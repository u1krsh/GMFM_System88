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


class AuthProvider:
    """Base auth provider. Replace this with an API-backed provider later."""

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


class AuthService:
    """Auth facade that can be switched from local DB to online services later."""

    def __init__(self, db_context):
        self.repo = UserRepository(db_context)
        self.provider: AuthProvider = LocalAuthProvider(self.repo)

    def has_users(self) -> bool:
        return self.repo.count_users() > 0

    def create_first_admin(self, full_name: str, username: str, password: str) -> AppUser:
        if self.has_users():
            raise ValueError("An account already exists")
        normalized = _normalize_username(username)
        if len(normalized) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(password or "") < 8:
            raise ValueError("Password must be at least 8 characters")
        user = AppUser(
            username=normalized,
            password_hash=hash_password(password),
            full_name=(full_name or "").strip() or "Admin",
            role="admin",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        return self.repo.create_user(user)

    def login(self, page, username: str, password: str) -> Optional[AppUser]:
        normalized = _normalize_username(username)
        user = self.provider.authenticate(normalized, password)
        if not user:
            return None
        page.client_storage.set(SESSION_USER_ID, int(user.id or 0))
        page.client_storage.set(SESSION_USERNAME, user.username)
        return user

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
