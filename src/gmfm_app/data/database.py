from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from gmfm_app.services.security import SecurityProvider

APP_DB_NAME = "gmfm_app.db"


def resolve_db_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    
    # On Android, Path.home() may fail or be inaccessible
    # Use CWD as fallback which is app's private storage
    try:
        home = Path.home()
        app_dir = home / ".gmfm_app"
        app_dir.mkdir(parents=True, exist_ok=True)
        # Test if writable
        test_file = app_dir / ".test"
        test_file.write_text("test")
        test_file.unlink()
        return app_dir / APP_DB_NAME
    except Exception:
        # Fallback to CWD (works on Android)
        app_dir = Path(".") / ".gmfm_data"
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / APP_DB_NAME


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY,
                given_name TEXT NOT NULL,
                family_name TEXT NOT NULL,
                dob TEXT,
                identifier TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                patient_id INTEGER NOT NULL,
                scale TEXT NOT NULL,
                raw_scores TEXT NOT NULL,
                total_score REAL NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        # Add notes column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN notes TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        conn.commit()


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    resolved = resolve_db_path(str(path) if path else None)
    init_db(resolved)
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_context(path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class DatabaseContext:
    """Helper class to hand out SQLite connections with shared config/security."""

    def __init__(self, db_path: str | None = None, security: "SecurityProvider" | None = None):
        self.db_path = Path(db_path).expanduser() if db_path else None
        self.security = security

    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        return db_context(self.db_path)

    def __call__(self) -> Generator[sqlite3.Connection, None, None]:
        return self.connect()

    # security helpers
    def encrypt(self, value: Optional[str]) -> Optional[str]:
        if self.security:
            return self.security.encrypt(value)
        return value

    def decrypt(self, value: Optional[str]) -> Optional[str]:
        if self.security:
            return self.security.decrypt(value)
        return value
