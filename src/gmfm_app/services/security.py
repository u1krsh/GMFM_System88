from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
try:
    import keyring  # type: ignore
except ImportError:  # pragma: no cover
    keyring = None

ENV_KEY_VAR = "GMFM_APP_SECRET"
KEYRING_SERVICE = "gmfm_app"
KEYRING_ENTRY = "encryption_key"
DEV_KEY_PATH = Path(".env.local")


class SecurityProvider:
    """Loads/stores encryption keys and exposes helper methods."""

    def __init__(self) -> None:
        self._key = self._load_key()
        self._fernet = Fernet(self._key)

    # key resolution order: env -> keyring -> local file -> generate new dev key
    def _load_key(self) -> bytes:
        env_key = os.getenv(ENV_KEY_VAR)
        if env_key:
            return env_key.encode()
        keyring_key = self._fetch_keyring_key()
        if keyring_key:
            return keyring_key
        file_key = self._read_local_key()
        if file_key:
            return file_key
        new_key = Fernet.generate_key()
        self._persist_dev_key(new_key)
        return new_key

    def _fetch_keyring_key(self) -> Optional[bytes]:
        if keyring is None:
            return None
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_ENTRY)
        if stored:
            return stored.encode()
        return None

    def _read_local_key(self) -> Optional[bytes]:
        if DEV_KEY_PATH.exists():
            value = DEV_KEY_PATH.read_text().strip()
            try:
                base64.urlsafe_b64decode(value)
                return value.encode()
            except Exception:
                return None
        return None

    def _persist_dev_key(self, key: bytes) -> None:
        DEV_KEY_PATH.write_text(key.decode())

    def encrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        token = self._fernet.encrypt(value.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            plain = self._fernet.decrypt(value.encode("utf-8"))
            return plain.decode("utf-8")
        except Exception:
            return None
