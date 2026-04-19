"""
Sync Configuration — manages Supabase connection settings.
Stored in Flet's client_storage so credentials persist across sessions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

STORAGE_PREFIX = "cloud_sync_"

# Default Supabase project credentials (anon key is public — RLS protects data)
DEFAULT_SUPABASE_URL = "https://rymumoqzrxxnnlfwmqyp.supabase.co"
DEFAULT_SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5bXVtb3F6cnh4bm5sZndtcXlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4MjI2MTEsImV4cCI6MjA4OTM5ODYxMX0.ueqUeb4gnT7TbCnoH9EHnEERnFzsaAgxXJMavcgZcOU"


@dataclass
class SyncConfig:
    supabase_url: str = DEFAULT_SUPABASE_URL
    supabase_key: str = DEFAULT_SUPABASE_KEY
    cloud_email: str = ""
    cloud_password: str = ""  # Only kept in-memory for login; never persisted

    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    def is_logged_in(self) -> bool:
        return bool(self.supabase_url and self.supabase_key and self.cloud_email)


def save_config(page, config: SyncConfig) -> None:
    """Persist config to Flet client_storage (except password)."""
    try:
        page.client_storage.set(f"{STORAGE_PREFIX}url", config.supabase_url)
        page.client_storage.set(f"{STORAGE_PREFIX}key", config.supabase_key)
        page.client_storage.set(f"{STORAGE_PREFIX}email", config.cloud_email)
    except Exception:
        pass


def load_config(page) -> SyncConfig:
    """Load config from Flet client_storage, falling back to hardcoded defaults."""
    try:
        return SyncConfig(
            supabase_url=page.client_storage.get(f"{STORAGE_PREFIX}url") or DEFAULT_SUPABASE_URL,
            supabase_key=page.client_storage.get(f"{STORAGE_PREFIX}key") or DEFAULT_SUPABASE_KEY,
            cloud_email=page.client_storage.get(f"{STORAGE_PREFIX}email") or "",
        )
    except Exception:
        return SyncConfig()


def clear_config(page) -> None:
    """Remove cloud config from client_storage."""
    for key in ("url", "key", "email"):
        try:
            page.client_storage.remove(f"{STORAGE_PREFIX}{key}")
        except Exception:
            pass
