from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Optional

from gmfm_app.data.models import AppUser
from gmfm_app.data.repositories import UserRepository


SESSION_USER_ID = "auth_user_id"
SESSION_USERNAME = "auth_username"

VALID_ROLES = ("admin", "teacher", "parent", "sponsor")


class AuthProvider:
    """Base auth provider."""

    def authenticate(self, username: str, password: str) -> Optional[AppUser]:
        raise NotImplementedError


class LocalAuthProvider(AuthProvider):
    """Local provider using SQLite + PBKDF2 password hashes."""

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def authenticate(self, username: str, password: str) -> Optional[AppUser]:
        user = self.repo.get_by_username(username)
        if not user or not user.is_active:
            return None
        if verify_password(password, user.password_hash):
            return user
        return None


def _normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def hash_password(password: str, iterations: int = 200_000) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    digest_b64 = base64.b64encode(digest).decode("utf-8")
    return f"pbkdf2_sha256${iterations}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_b64, digest_b64 = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False


def _log(msg):
    try:
        print(f"[AUTH] {msg}", flush=True)
    except Exception:
        pass


class AuthService:
    """Auth facade with automatic Supabase cloud registration/login."""

    def __init__(self, db_context, sync_service=None):
        self.repo = UserRepository(db_context)
        self.provider: AuthProvider = LocalAuthProvider(self.repo)
        self.sync_service = sync_service  # Set by main.py after sync init

    def has_users(self) -> bool:
        return self.repo.count_users() > 0

    def create_user_account(self, full_name: str, username: str, password: str,
                            email: str = "", role: str = "teacher",
                            allow_privileged: bool = False,
                            skip_cloud: bool = False) -> AppUser:
        """Create a new user account. Auto-registers to Supabase.

        ``allow_privileged`` lets an existing administrator create an account with
        any valid role from the admin console, including otherwise non-selectable
        ones such as ``sponsor``.

        ``skip_cloud`` suppresses the immediate Supabase sign-up. Required when an
        admin creates an account *on behalf of someone else*: ``sign_up`` swaps the
        client's session to the new user, which would silently sign the admin out
        of the cloud mid-session.
        """
        normalized = _normalize_username(username)
        if len(normalized) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(password or "") < 6:
            raise ValueError("Password must be at least 6 characters")

        # Role policy: the very first account always bootstraps an administrator.
        # Afterwards the signup form offers Teacher / Parent / Admin, so 'admin'
        # is accepted here too; the cloud trigger mirrors this. 'sponsor' remains
        # non-selectable (legacy role) unless an admin creates the account.
        if not self.has_users():
            role = "admin"
        elif allow_privileged:
            if role not in VALID_ROLES:
                role = "teacher"
        elif role not in ("teacher", "parent", "admin"):
            role = "teacher"

        # Check if username already exists
        existing = self.repo.get_by_username(normalized)
        if existing:
            raise ValueError("Username already taken")

        # Check if email already used
        email_clean = (email or "").strip().lower()
        if email_clean:
            existing_email = self.repo.get_by_email(email_clean)
            if existing_email:
                raise ValueError("Email already registered")

        # Try to register with Supabase to get cloud_uid, but NEVER block
        # local account creation on cloud failures (network, DNS, etc.).
        # The _cloud_provision() mechanism will auto-register on next login.
        cloud_uid = ""
        if email_clean and self.sync_service and not skip_cloud:
            if self.sync_service.is_online():
                uid, err_msg = self._cloud_register(email_clean, password, full_name, role)
                if uid:
                    cloud_uid = uid
                else:
                    _log(f"Cloud registration deferred (will auto-provision on next login): {err_msg}")
            else:
                _log("Offline — skipping immediate cloud registration (will auto-provision later)")
        elif skip_cloud:
            _log(f"Cloud sign-up skipped for {email_clean or normalized} "
                 "(created by an admin — preserving the admin's own cloud session)")

        user = AppUser(
            username=normalized,
            password_hash=hash_password(password),
            full_name=(full_name or "").strip() or "User",
            role=role,
            is_active=True,
            email=email_clean,
            cloud_uid=cloud_uid,
            created_at=datetime.now(timezone.utc),
        )
        created = self.repo.create_user(user)
        _log(f"Created local user: {created.username} (id={created.id}, role={role}, cloud_uid={cloud_uid[:8] if cloud_uid else 'none'})")
        return created

    def login(self, page, username: str, password: str) -> Optional[AppUser]:
        """Login locally and auto-provision a Supabase cloud account."""
        normalized = _normalize_username(username)
        user = self.provider.authenticate(normalized, password)

        # Fallback for new devices: if local user is not found but input looks like an
        # email, try restoring the account from Supabase (cloud → local sync).
        if not user and "@" in normalized and getattr(self, 'sync_service', None):
            try:
                client = self.sync_service._get_client()
                if client:
                    result = client.auth.sign_in_with_password({"email": normalized, "password": password})
                    cloud_user = getattr(result, 'user', None)
                    if cloud_user:
                        self.sync_service._user_id = cloud_user.id
                        # Fetch profile from Supabase
                        prof_res = client.table("profiles").select("*").eq("id", cloud_user.id).execute()
                        prof_data = prof_res.data[0] if prof_res.data else {}
                        full_name = prof_data.get("full_name") or "User"
                        role = prof_data.get("role") or "teacher"
                        if role not in VALID_ROLES:
                            role = "teacher"
                        email_clean = prof_data.get("email") or normalized

                        # Create local AppUser
                        user_obj = AppUser(
                            username=email_clean.split('@')[0],
                            password_hash=hash_password(password),
                            full_name=full_name,
                            role=role,
                            is_active=True,
                            email=email_clean,
                            cloud_uid=cloud_user.id,
                            created_at=datetime.now(timezone.utc)
                        )
                        user = self.repo.create_user(user_obj)
                        _log(f"Restored account from cloud: {email_clean}")
            except Exception as e:
                _log(f"Failed to restore cloud user: {e}")

        if not user:
            return None

        page.client_storage.set(SESSION_USER_ID, int(user.id or 0))
        page.client_storage.set(SESSION_USERNAME, user.username)

        # Always attempt cloud provisioning after a successful local login.
        # If the user has no email on record, derive a synthetic one so they
        # still get a cloud account and their data syncs automatically.
        if self.sync_service:
            email = (getattr(user, 'email', '') or '').strip()
            if not email:
                # Generate a deterministic synthetic email for accounts that
                # were created before email was required.
                email = f"{user.username}@motormeasure.app"
                _log(f"No email on file for {user.username} — using synthetic: {email}")
                # Persist the synthetic email so future logins use it.
                try:
                    self.repo.update_email(user.id, email)
                    user.email = email
                except Exception as e:
                    _log(f"Could not persist synthetic email: {e}")
            self._cloud_provision(page, email, password, user)

        _log(f"Login OK: {user.username} (role={user.role})")
        return user

    def _cloud_register(self, email: str, password: str, full_name: str, role: str) -> tuple[str, str]:
        """Register with Supabase Auth. Returns (cloud_uid, error_msg)."""
        try:
            sync = self.sync_service
            if not sync:
                return "", "Supabase not configured"

            # Pass metadata so the trigger creates the profile with role
            ok, msg, uid = sync.register_with_metadata(email, password, full_name, role)
            if ok:
                _log(f"Cloud register OK: {email} -> {uid[:8]}")
                return uid, ""
            else:
                _log(f"Cloud register failed: {msg}")
                return "", msg
        except Exception as e:
            _log(f"Cloud register error: {e}")
            return "", str(e)

    def _cloud_provision(self, page, email: str, password: str, user: AppUser):
        """Ensure the user has a live Supabase session.

        Strategy (runs silently in the background after local login):
        1. Try signing in with the stored email + password.
        2. If login fails (wrong creds / account doesn't exist), auto-register.
        3. If offline, skip silently — sync_worker will retry when online.
        """
        import threading

        def _do_provision():
            try:
                sync = self.sync_service
                if not sync:
                    return

                # A session may already be live (restored from the refresh token by
                # the sync worker, or a previous login in this run). Skip the
                # sign-in, but still reconcile: cloud is authoritative for roles, and
                # returning early here used to leave a device's local role stale
                # forever — an admin's promotion/demotion never reached them.
                if sync._user_id:
                    _log(f"Cloud session already active for {user.username} — reconciling only")
                    self._finalize_cloud_uid(page, user, sync)
                    self._reconcile_role(page, user, sync)
                    return

                if not sync.is_online():
                    _log(f"Offline — skipping cloud provision for {user.username}")
                    return

                # Attempt 1: sign in
                ok, msg = sync.login(email, password,
                                     full_name=user.full_name, role=user.role)
                if ok:
                    _log(f"Cloud sign-in OK for {user.username} ({email})")
                    self._finalize_cloud_uid(page, user, sync)
                    self._reconcile_role(page, user, sync)
                    return

                # Attempt 2: auto-register (account doesn't exist on the server yet)
                _log(f"Cloud sign-in failed ({msg}) — auto-registering {email}...")
                ok2, msg2, uid = sync.register_with_metadata(
                    email, password, user.full_name, user.role
                )
                if ok2:
                    _log(f"Auto-registered cloud account for {user.username}: {uid[:8]}")
                    self._finalize_cloud_uid(page, user, sync)
                    self._reconcile_role(page, user, sync)
                    # Notify on the Flet page (safe: Flet is thread-safe for updates)
                    try:
                        page.snack_bar = __import__('flet').SnackBar(
                            __import__('flet').Text("☁️ Cloud account created automatically!"),
                            bgcolor="#0D9488",
                        )
                        page.snack_bar.open = True
                        page.update()
                    except Exception:
                        pass
                else:
                    _log(f"Cloud provision failed for {user.username}: {msg2}")
            except Exception as e:
                _log(f"Cloud provision error for {user.username}: {e}")

        # Run in a daemon thread so login is never blocked by network calls
        threading.Thread(target=_do_provision, daemon=True).start()

    def _finalize_cloud_uid(self, page, user: AppUser, sync):
        """Persist cloud_uid and save config after a successful cloud auth."""
        try:
            if not getattr(user, 'cloud_uid', '') and sync._user_id:
                self.repo.update_cloud_uid(user.id, sync._user_id)
                user.cloud_uid = sync._user_id
                _log(f"Stored cloud_uid for {user.username}: {sync._user_id[:8]}")
            from gmfm_app.services.sync_config import save_config
            sync.config.cloud_email = user.email
            save_config(page, sync.config)
        except Exception as e:
            _log(f"Could not finalise cloud_uid: {e}")

    def _reconcile_role(self, page, user: AppUser, sync):
        """Cloud (`profiles.role`) is authoritative for roles. After a successful
        cloud sign-in, pull the server role and update the local mirror if it
        drifted (e.g. an admin promoted/demoted this user from the console).

        Runs in the provisioning daemon thread; the new role is picked up the
        next time `current_user()` re-reads the local row (next navigation/login).
        """
        try:
            client = sync._get_client()
            if not client or not getattr(sync, "_user_id", None):
                return
            res = client.table("profiles").select("role").eq("id", sync._user_id).execute()
            rows = getattr(res, "data", None) or []
            cloud_role = rows[0].get("role") if rows else None
            if cloud_role in VALID_ROLES and cloud_role != user.role:
                old_role = user.role
                self.repo.update_role(user.id, cloud_role)
                user.role = cloud_role
                _log(f"Reconciled role for {user.username} from cloud -> {cloud_role}")
                # Tell the user. A silent demotion is confusing — menu entries
                # (e.g. the Admin console) simply vanish with no explanation.
                try:
                    import flet as ft
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(
                            f"Your account role changed on the server: "
                            f"{old_role} → {cloud_role}. Restart to apply everywhere.",
                            color="white"),
                        bgcolor="#F59E0B",
                    )
                    page.snack_bar.open = True
                    page.update()
                except Exception:
                    pass
        except Exception as e:
            _log(f"Role reconcile skipped for {user.username}: {e}")

    # ── Password recovery ──────────────────────────────────────────

    def request_password_reset(self, email: str) -> tuple:
        """Send a password-recovery code to the given email (cloud-only)."""
        if not self.sync_service:
            return False, "Cloud sync isn't available on this device."
        return self.sync_service.send_password_reset(email)

    def complete_password_reset(self, page, email: str, token: str,
                                new_password: str) -> tuple:
        """Verify the recovery code, set the new cloud password, and mirror it to
        the local account so both app login and the silent cloud re-auth work with
        the new password. Returns (ok, msg)."""
        if len(new_password or "") < 6:
            return False, "Password must be at least 6 characters."
        if not self.sync_service:
            return False, "Cloud sync isn't available on this device."

        ok, msg = self.sync_service.reset_password_with_otp(email, token, new_password)
        if not ok:
            return False, msg

        # Mirror the new password into the local account so app login uses it too.
        # If no local row exists yet (new device), login()'s new-device restore
        # path recreates it on next sign-in with the new password.
        email_clean = (email or "").strip().lower()
        try:
            user = self.repo.get_by_email(email_clean)
            if user:
                self.repo.update_password(user.id, hash_password(new_password))
                if not getattr(user, "cloud_uid", "") and self.sync_service._user_id:
                    self.repo.update_cloud_uid(user.id, self.sync_service._user_id)
                _log(f"Local password mirrored for {user.username}")
            else:
                _log(f"No local account for {email_clean}; will restore on next sign-in.")
        except Exception as e:
            _log(f"Could not mirror local password: {e}")

        return True, "Password reset. Sign in with your new password."

    def current_user(self, page) -> Optional[AppUser]:
        try:
            user_id = page.client_storage.get(SESSION_USER_ID)
            username = page.client_storage.get(SESSION_USERNAME)
        except Exception:
            return None
        if not user_id or not username:
            return None
        user = self.repo.get_by_id(int(user_id))
        if not user:
            self.logout(page)
            return None
        if user.username != _normalize_username(username):
            self.logout(page)
            return None
        return user

    def is_authenticated(self, page) -> bool:
        return self.current_user(page) is not None

    def logout(self, page) -> None:
        try:
            page.client_storage.remove(SESSION_USER_ID)
            page.client_storage.remove(SESSION_USERNAME)
        except Exception:
            pass
        # Also logout from Supabase
        if self.sync_service:
            try:
                self.sync_service.cloud_logout()
            except Exception:
                pass
