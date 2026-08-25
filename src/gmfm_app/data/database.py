from __future__ import annotations

import os
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
    
    # On Android/iOS, use FLET_APP_STORAGE_DATA which points to app's private storage
    flet_storage = os.getenv("FLET_APP_STORAGE_DATA")
    if flet_storage:
        app_dir = Path(flet_storage) / ".gmfm_data"
        try:
            app_dir.mkdir(parents=True, exist_ok=True)
            return app_dir / APP_DB_NAME
        except Exception:
            pass
    
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
        
        # Migration: Rename patients table to students if exists
        try:
            cursor.execute("ALTER TABLE patients RENAME TO students")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Table already renamed or doesn't exist
            
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
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
                student_id INTEGER NOT NULL,
                scale TEXT NOT NULL,
                raw_scores TEXT NOT NULL,
                total_score REAL NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'clinician',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                synced INTEGER DEFAULT 0
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        
        # Migration: Add notes column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN notes TEXT")
        except sqlite3.OperationalError:
            pass

        # Migration: Add user metadata columns if missing
        try:
            cursor.execute("ALTER TABLE app_users ADD COLUMN role TEXT NOT NULL DEFAULT 'clinician'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE app_users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass
            
        # Migration: Rename patient_id to student_id if needed
        # SQLite doesn't support renaming columns easily in older versions, 
        # but modern versions do.
        try:
            cursor.execute("ALTER TABLE sessions RENAME COLUMN patient_id TO student_id")
        except sqlite3.OperationalError:
            pass

        # Migration: Add email column to app_users if missing
        try:
            cursor.execute("ALTER TABLE app_users ADD COLUMN email TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # Migration: Add cloud_uid column to app_users if missing
        try:
            cursor.execute("ALTER TABLE app_users ADD COLUMN cloud_uid TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # Migration: Add user_id column to students if missing
        try:
            cursor.execute("ALTER TABLE students ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass

        # Migration: Add user_id column to sessions if missing
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass

        # Migration: Rename old 'clinician' role to 'teacher'
        try:
            cursor.execute("UPDATE app_users SET role = 'teacher' WHERE role = 'clinician'")
        except sqlite3.OperationalError:
            pass

        # Student access table — the unified relationship model connecting
        # every account type (teacher/parent/…) to student records.
        # access_level: 'owner' | 'edit' | 'view'.
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS student_access (
                id INTEGER PRIMARY KEY,
                student_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                access_level TEXT NOT NULL DEFAULT 'view',
                granted_by INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id),
                UNIQUE(student_id, user_id)
            );
            """
        )

        # Backfill: every existing student's owning teacher gets an explicit
        # 'owner' access row, so the relationship table is authoritative going
        # forward. Idempotent via the UNIQUE(student_id, user_id) constraint.
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO student_access
                    (student_id, user_id, access_level, granted_by, created_at)
                SELECT id, user_id, 'owner', NULL, created_at FROM students;
                """
            )
        except sqlite3.OperationalError:
            pass

        # One-time admin bootstrap: on an existing single-user install there is
        # no admin yet, so promote the earliest account. Fresh installs get
        # their admin via the "first user" signup path instead.
        try:
            cursor.execute(
                """
                UPDATE app_users SET role = 'admin'
                WHERE id = (SELECT id FROM app_users ORDER BY created_at ASC, id ASC LIMIT 1)
                  AND NOT EXISTS (SELECT 1 FROM app_users WHERE role = 'admin');
                """
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()


_db_initialized: set = set()  # Track which DB paths have been initialized


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    resolved = resolve_db_path(str(path) if path else None)
    resolved_str = str(resolved)
    if resolved_str not in _db_initialized:
        init_db(resolved)
        _db_initialized.add(resolved_str)
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
