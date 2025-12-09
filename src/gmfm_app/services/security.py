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
KEY_FILE_NAME = ".gmfm_key"

def get_data_dir():
    # Attempt to find a writable data directory
    # On Android, we might need a specific path or just rely on CWD if writable.
    # For Flet on Android, CWD is usually writable private storage.
    return Path(".")


class SecurityProvider:
    """Loads/stores encryption keys and exposes helper methods."""

    def __init__(self) -> None:
        self._key = self._load_key()
        self._fernet = Fernet(self._key)

    # key resolution order: env -> local file -> generate new key
    def _load_key(self) -> bytes:
        env_key = os.getenv(ENV_KEY_VAR)
        if env_key:
            return env_key.encode()
        
        # Try local file in data dir
        file_key = self._read_local_key()
        if file_key:
            return file_key
            
        # Generate new
        new_key = Fernet.generate_key()
        self._persist_key(new_key)
        return new_key

    def _get_key_path(self) -> Path:
        return get_data_dir() / KEY_FILE_NAME

    def _read_local_key(self) -> Optional[bytes]:
        key_path = self._get_key_path()
        if key_path.exists():
            try:
                content = key_path.read_text().strip()
                # Basic validation
                if len(content) > 0:
                    return content.encode()
            except Exception:
                pass
        return None

    def _persist_key(self, key: bytes) -> None:
        try:
            self._get_key_path().write_text(key.decode())
        except Exception:
            # If we can't write, we might be on a read-only filesystem or strict permissions
            print("WARNING: Could not persist encryption key.")

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
