"""
Sync Service — offline-first cloud sync engine.

Uses created_by (Supabase UUID) for cloud operations.
Follows a git-like model: commit locally, push when online.
"""
from __future__ import annotations

import json
import socket
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from gmfm_app.data.database import DatabaseContext
from gmfm_app.services.sync_config import SyncConfig


def _log(msg):
    try:
        print(f"[SYNC] {msg}", flush=True)
    except Exception:
        pass


@dataclass
class SyncResult:
    pushed: int = 0
    pulled: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True

    @property
    def summary(self) -> str:
        parts = []
        if self.pushed:
            parts.append(f"pushed {self.pushed}")
        if self.pulled:
            parts.append(f"pulled {self.pulled}")
        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        return ", ".join(parts) if parts else "Up to date"


class SyncService:
    """Offline-first sync engine using Supabase as cloud backend."""

    def __init__(self, db_context: DatabaseContext, config: SyncConfig):
        self.db_context = db_context
        self.config = config
        self._client = None
        self._user_id: Optional[str] = None  # Supabase UUID

    def _get_client(self):
        """Lazy-init Supabase client. Reuses existing client."""
        if self._client is None and self.config.is_configured():
            try:
                from supabase import create_client
                self._client = create_client(self.config.supabase_url, self.config.supabase_key)
                _log(f"Supabase client ready")
            except ImportError:
                _log("supabase package not installed")
            except Exception as e:
                _log(f"Supabase client error: {e}")
        return self._client

    def is_online(self) -> bool:
        # Try Supabase host first (the server we actually need)
        try:
            host = self.config.supabase_url.replace("https://", "").replace("http://", "").split("/")[0]
            socket.create_connection((host, 443), timeout=5).close()
            return True
        except Exception:
            pass
        # Fallback to Google DNS
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3).close()
            return True
        except (OSError, socket.timeout):
            return False

    def get_pending_count(self) -> int:
        try:
            with self.db_context.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM sync_queue WHERE synced = 0")
                row = cur.fetchone()
                return int(row[0]) if row else 0
        except Exception:
            return 0

    # ── Authentication ─────────────────────────────────────────────

    def register_with_metadata(self, email: str, password: str,
                                full_name: str, role: str) -> tuple:
        """Register with Supabase Auth. Profile is created on first login.
        Returns (ok, msg, cloud_uid).
        """
        client = self._get_client()
        if not client:
            return False, "Supabase not configured", ""
        try:
            # Store metadata for profile creation after login
            self._pending_profile = {
                "full_name": full_name,
                "role": role,
                "email": email,
            }
            result = client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "role": role,
                    }
                }
            })
            user = getattr(result, 'user', None)
            if user:
                self._user_id = user.id
                self.config.cloud_email = email
                _log(f"Registered: {email} (uid={user.id[:8]}). Profile will be created on login.")
                return True, "Account created!", user.id
            return False, "Registration failed", ""
        except Exception as e:
            msg = str(e)
            if "already registered" in msg.lower() or "already been registered" in msg.lower():
                _log(f"Already registered, trying login: {email}")
                ok, login_msg = self.login(email, password)
                uid = self._user_id or ""
                return ok, login_msg, uid
            _log(f"Register error: {msg[:100]}")
            return False, f"Registration error: {msg[:100]}", ""

    def login(self, email: str, password: str,
              full_name: str = "", role: str = "") -> tuple:
        """Sign in to Supabase. Creates/updates profile with given role."""
        client = self._get_client()
        if not client:
            return False, "Supabase not configured"
        try:
            result = client.auth.sign_in_with_password({"email": email, "password": password})
            user = getattr(result, 'user', None)
            session = getattr(result, 'session', None)
            if user:
                self._user_id = user.id
                self.config.cloud_email = email
                _log(f"Cloud login OK: {email} (uid={user.id[:8]})")

                # Store refresh token for session persistence across restarts
                if session:
                    self._save_refresh_token(getattr(session, 'refresh_token', ''))

                # Create/update profile (session is now active with valid JWT)
                self._ensure_profile(user.id, email, full_name, role)

                return True, "Signed in!"
            return False, "Login failed"
        except Exception as e:
            msg = str(e)
            _log(f"Cloud login error: {msg[:100]}")
            if "invalid" in msg.lower() or "credentials" in msg.lower():
                return False, "Invalid email or password"
            if "not confirmed" in msg.lower():
                return False, "Email not confirmed yet"
            return False, f"Login error: {msg[:80]}"

    def _ensure_profile(self, user_id: str, email: str,
                        full_name: str = "", role: str = ""):
        """Create or update the profiles row. Called after login when session is active."""
        client = self._get_client()
        if not client:
            return
        try:
            # Use explicit params first, then pending profile data, then defaults
            profile_data = getattr(self, '_pending_profile', None) or {}
            final_name = full_name or profile_data.get('full_name', '')
            final_role = role or profile_data.get('role', 'teacher')

            client.table("profiles").upsert({
                "id": user_id,
                "full_name": final_name,
                "role": final_role,
                "email": email,
            }, on_conflict="id").execute()
            _log(f"Profile upserted for {email} (role={final_role})")
            self._pending_profile = None
        except Exception as e:
            _log(f"Profile upsert error: {e}")

    def _save_refresh_token(self, token: str):
        """Persist refresh token to local file for session restoration."""
        if not token:
            return
        try:
            from pathlib import Path
            token_path = Path.home() / ".gmfm_app" / ".cloud_token"
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(token)
            _log("Refresh token saved")
        except Exception as e:
            _log(f"Token save error: {e}")

    def _load_refresh_token(self) -> str:
        """Load stored refresh token."""
        try:
            from pathlib import Path
            token_path = Path.home() / ".gmfm_app" / ".cloud_token"
            if token_path.exists():
                return token_path.read_text().strip()
        except Exception:
            pass
        return ""

    def _clear_refresh_token(self):
        """Remove stored refresh token."""
        try:
            from pathlib import Path
            token_path = Path.home() / ".gmfm_app" / ".cloud_token"
            if token_path.exists():
                token_path.unlink()
        except Exception:
            pass

    def ensure_auth(self) -> bool:
        """Check/restore Supabase session. Uses stored refresh token if needed."""
        if self._user_id:
            return True
        client = self._get_client()
        if not client:
            return False

        # Try existing session first
        try:
            session = client.auth.get_session()
            if session:
                user = getattr(session, 'user', None)
                if user:
                    self._user_id = user.id
                    _log(f"Session restored from existing: {user.id[:8]}")
                    return True
        except Exception:
            pass

        # Try refresh token
        refresh_token = self._load_refresh_token()
        if refresh_token:
            try:
                result = client.auth.refresh_session(refresh_token)
                session = getattr(result, 'session', None)
                user = getattr(result, 'user', None) or (getattr(session, 'user', None) if session else None)
                if user:
                    self._user_id = user.id
                    # Save new refresh token
                    if session:
                        new_token = getattr(session, 'refresh_token', '')
                        if new_token:
                            self._save_refresh_token(new_token)
                    _log(f"Session restored from refresh token: {user.id[:8]}")
                    return True
            except Exception as e:
                _log(f"Refresh token expired: {e}")
                self._clear_refresh_token()

        return False

    def cloud_logout(self) -> None:
        client = self._get_client()
        if client:
            try:
                client.auth.sign_out()
            except Exception:
                pass
        self._user_id = None
        self._client = None
        self._clear_refresh_token()

    # ── Push (local -> cloud) ──────────────────────────────────────

    def push(self) -> SyncResult:
        result = SyncResult()
        client = self._get_client()

        if not self._user_id:
            if not self.ensure_auth():
                result.errors.append("Not authenticated")
                result.success = False
                return result

        if not client:
            result.errors.append("No Supabase client")
            result.success = False
            return result

        try:
            with self.db_context.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, table_name, record_id, operation, payload, created_at "
                    "FROM sync_queue WHERE synced = 0 ORDER BY id ASC LIMIT 100"
                )
                rows = cur.fetchall()

                if not rows:
                    return result

                _log(f"Pushing {len(rows)} items...")

                for row in rows:
                    q_id, table, record_id, operation = row[0], row[1], row[2], row[3]
                    payload = json.loads(row[4]) if row[4] else {}

                    try:
                        if operation == "DELETE":
                            client.table(table).upsert({
                                "local_id": record_id,
                                "created_by": self._user_id,
                                "deleted": True,
                                "updated_at": datetime.utcnow().isoformat(),
                                **self._cloud_payload(table, payload),
                            }, on_conflict="created_by,local_id").execute()
                        else:
                            cloud_data = {
                                "local_id": record_id,
                                "created_by": self._user_id,
                                "deleted": False,
                                "updated_at": datetime.utcnow().isoformat(),
                                **self._cloud_payload(table, payload),
                            }
                            client.table(table).upsert(
                                cloud_data, on_conflict="created_by,local_id"
                            ).execute()

                        cur.execute("UPDATE sync_queue SET synced = 1 WHERE id = ?", (q_id,))
                        result.pushed += 1

                    except Exception as e:
                        err = str(e)[:120]
                        _log(f"  Push error {table}#{record_id}: {err}")
                        result.errors.append(f"{table}#{record_id}: {err}")

                conn.commit()

        except Exception as e:
            _log(f"Push failed: {e}")
            result.errors.append(str(e)[:100])
            result.success = False

        return result

    def _cloud_payload(self, table: str, payload: dict) -> dict:
        data = dict(payload)
        if table == "students":
            return {
                "given_name": data.get("given_name", ""),
                "family_name": data.get("family_name", ""),
                "dob": data.get("dob"),
                "identifier": data.get("identifier"),
                "created_at": data.get("created_at", datetime.utcnow().isoformat()),
            }
        elif table == "sessions":
            raw = data.get("raw_scores", {})
            return {
                "student_local_id": data.get("student_id", 0),
                "scale": data.get("scale", "88"),
                "raw_scores": raw if isinstance(raw, str) else json.dumps(raw),
                "total_score": data.get("total_score", 0),
                "notes": data.get("notes"),
                "created_at": data.get("created_at", datetime.utcnow().isoformat()),
            }
        return data

    # ── Pull (cloud -> local) ──────────────────────────────────────

    def pull(self) -> SyncResult:
        result = SyncResult()
        client = self._get_client()

        if not self._user_id:
            if not self.ensure_auth():
                result.errors.append("Not authenticated for pull")
                result.success = False
                return result

        if not client:
            result.errors.append("No Supabase client")
            result.success = False
            return result

        try:
            last_pull = self._get_last_pull()

            for table in ("students", "sessions"):
                try:
                    query = client.table(table).select("*").eq("created_by", self._user_id)
                    if last_pull:
                        query = query.gt("updated_at", last_pull)
                    response = query.execute()

                    if response.data:
                        for record in response.data:
                            self._upsert_local(table, record)
                            result.pulled += 1
                        _log(f"Pulled {len(response.data)} from {table}")

                except Exception as e:
                    err = str(e)[:120]
                    _log(f"Pull error {table}: {err}")
                    result.errors.append(f"Pull {table}: {err}")

            self._set_last_pull(datetime.utcnow().isoformat())

        except Exception as e:
            _log(f"Pull failed: {e}")
            result.errors.append(str(e)[:100])
            result.success = False

        return result

    def _upsert_local(self, table: str, cloud_record: dict):
        local_id = cloud_record.get("local_id")
        if local_id is None:
            return

        with self.db_context.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM sync_queue WHERE table_name = ? AND record_id = ? AND synced = 0",
                (table, local_id),
            )
            if cur.fetchone()[0] > 0:
                return  # Local change pending — skip

            is_deleted = cloud_record.get("deleted", False)

            if table == "students":
                if is_deleted:
                    cur.execute("DELETE FROM students WHERE id = ?", (local_id,))
                else:
                    cur.execute("SELECT id FROM students WHERE id = ?", (local_id,))
                    if cur.fetchone():
                        cur.execute(
                            "UPDATE students SET given_name=?, family_name=?, dob=?, identifier=? WHERE id=?",
                            (cloud_record.get("given_name"), cloud_record.get("family_name"),
                             cloud_record.get("dob"), cloud_record.get("identifier"), local_id),
                        )
                    else:
                        cur.execute(
                            "INSERT OR REPLACE INTO students (id, given_name, family_name, dob, identifier, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (local_id, cloud_record.get("given_name"), cloud_record.get("family_name"),
                             cloud_record.get("dob"), cloud_record.get("identifier"),
                             cloud_record.get("created_at", datetime.utcnow().isoformat())),
                        )

            elif table == "sessions":
                if is_deleted:
                    cur.execute("DELETE FROM sessions WHERE id = ?", (local_id,))
                else:
                    raw_scores = cloud_record.get("raw_scores", "{}")
                    if isinstance(raw_scores, dict):
                        raw_scores = json.dumps(raw_scores)
                    cur.execute("SELECT id FROM sessions WHERE id = ?", (local_id,))
                    if cur.fetchone():
                        cur.execute(
                            "UPDATE sessions SET student_id=?, scale=?, raw_scores=?, total_score=?, notes=? WHERE id=?",
                            (cloud_record.get("student_local_id"), cloud_record.get("scale"),
                             raw_scores, cloud_record.get("total_score", 0),
                             cloud_record.get("notes"), local_id),
                        )
                    else:
                        cur.execute(
                            "INSERT OR REPLACE INTO sessions (id, student_id, scale, raw_scores, total_score, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (local_id, cloud_record.get("student_local_id"), cloud_record.get("scale"),
                             raw_scores, cloud_record.get("total_score", 0),
                             cloud_record.get("notes"),
                             cloud_record.get("created_at", datetime.utcnow().isoformat())),
                        )

            conn.commit()

    def _get_last_pull(self) -> Optional[str]:
        try:
            with self.db_context.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM sync_metadata WHERE key = 'last_pull'")
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def _set_last_pull(self, timestamp: str):
        try:
            with self.db_context.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT OR REPLACE INTO sync_metadata (key, value) VALUES ('last_pull', ?)",
                    (timestamp,),
                )
                conn.commit()
        except Exception:
            pass

    # ── Full Sync ──────────────────────────────────────────────────

    def sync(self) -> SyncResult:
        combined = SyncResult()

        if not self.is_online():
            combined.errors.append("No internet")
            combined.success = False
            return combined

        # Ensure our profile exists before pushing (FK constraint)
        if self._user_id and self.config.cloud_email:
            self._ensure_profile(self._user_id, self.config.cloud_email)

        push_result = self.push()
        combined.pushed = push_result.pushed
        combined.errors.extend(push_result.errors)

        pull_result = self.pull()
        combined.pulled = pull_result.pulled
        combined.errors.extend(pull_result.errors)

        combined.success = push_result.success and pull_result.success
        if combined.errors:
            for err in combined.errors:
                _log(f"  Sync error: {err}")
        _log(f"Sync done: {combined.summary}")
        return combined

    def restore_from_cloud(self) -> SyncResult:
        self._set_last_pull("")
        return self.pull()
