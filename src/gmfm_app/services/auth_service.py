from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime
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
                            email: str = "", role: str = "teacher") -> AppUser:
        """Create a new user account. Auto-registers to Supabase."""
        normalized = _normalize_username(username)
        if len(normalized) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(password or "") < 6:
            raise ValueError("Password must be at least 6 characters")
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}")

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

        # Auto-register to Supabase FIRST to get cloud_uid
        cloud_uid = ""
        if email_clean and self.sync_service:
            cloud_uid = self._cloud_register(email_clean, password, full_name, role)

        user = AppUser(
            username=normalized,
            password_hash=hash_password(password),
            full_name=(full_name or "").strip() or "User",
            role=role,
            is_active=True,
            email=email_clean,
            cloud_uid=cloud_uid,
            created_at=datetime.utcnow(),
        )
        created = self.repo.create_user(user)
        _log(f"Created local user: {created.username} (id={created.id}, role={role}, cloud_uid={cloud_uid[:8] if cloud_uid else 'none'})")
        return created

    def login(self, page, username: str, password: str) -> Optional[AppUser]:
        """Login locally and auto-sign-in to Supabase."""
        normalized = _normalize_username(username)
        user = self.provider.authenticate(normalized, password)

        # Fallback for new devices: if local user is not found, but it looks like an email,
        # try logging in to Supabase directly to restore the account locally.
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
                            created_at=datetime.utcnow()
                        )
                        user = self.repo.create_user(user_obj)
                        _log(f"Restored account from cloud: {email_clean}")
            except Exception as e:
                _log(f"Failed to restore cloud user: {e}")

        if not user:
            return None

        page.client_storage.set(SESSION_USER_ID, int(user.id or 0))
        page.client_storage.set(SESSION_USERNAME, user.username)

        # Auto-login to Supabase cloud (non-blocking, silent)
        email = getattr(user, 'email', '')
        cloud_uid = getattr(user, 'cloud_uid', '')
        if email and self.sync_service:
            self._cloud_login(page, email, password, user)

        _log(f"Login OK: {user.username} (role={user.role})")
        return user

    def _cloud_register(self, email: str, password: str, full_name: str, role: str) -> str:
        """Register with Supabase Auth. Returns cloud_uid or empty string."""
        try:
            sync = self.sync_service
            if not sync:
                return ""

            # Pass metadata so the trigger creates the profile with role
            ok, msg, uid = sync.register_with_metadata(email, password, full_name, role)
            if ok:
                _log(f"Cloud register OK: {email} -> {uid[:8]}")
                return uid
            else:
                _log(f"Cloud register failed: {msg}")
                return ""
        except Exception as e:
            _log(f"Cloud register error: {e}")
            return ""

    def _cloud_login(self, page, email: str, password: str, user: AppUser):
        """Auto-login to Supabase. Updates cloud_uid if missing."""
        try:
            sync = self.sync_service
            if not sync:
                return

            ok, msg = sync.login(email, password,
                                 full_name=user.full_name, role=user.role)
            if ok:
                # Store cloud_uid if we don't have it yet
                if not getattr(user, 'cloud_uid', '') and sync._user_id:
                    self.repo.update_cloud_uid(user.id, sync._user_id)
                    user.cloud_uid = sync._user_id
                    _log(f"Stored cloud_uid for {user.username}: {sync._user_id[:8]}")

                from gmfm_app.services.sync_config import save_config
                sync.config.cloud_email = email
                save_config(page, sync.config)
            else:
                # If login fails, try register (first time on new device)
                ok2, msg2, uid = sync.register_with_metadata(
                    email, password,
                    user.full_name, user.role
                )
                if ok2:
                    self.repo.update_cloud_uid(user.id, uid)
                    user.cloud_uid = uid
                    from gmfm_app.services.sync_config import save_config
                    sync.config.cloud_email = email
                    save_config(page, sync.config)
                    _log(f"Auto-registered to cloud: {email}")
                else:
                    _log(f"Cloud login/register failed: {msg2}")
        except Exception as e:
            _log(f"Cloud auth error: {e}")

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
