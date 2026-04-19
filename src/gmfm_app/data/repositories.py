from __future__ import annotations

import json
from typing import List, Optional
from datetime import datetime, date

from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.models import Student, Session, AppUser


def _log_sync(conn, table_name: str, record_id: int, operation: str, payload: dict):
    """Log a change to sync_queue for later cloud push."""
    try:
        conn.cursor().execute(
            "INSERT INTO sync_queue (table_name, record_id, operation, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (table_name, record_id, operation, json.dumps(payload), datetime.utcnow().isoformat()),
        )
    except Exception:
        pass  # Don't break writes if sync logging fails


class BaseRepository:
    def __init__(self, db_context: Optional[DatabaseContext] = None, user_id: Optional[int] = None):
        self.db_context = db_context or DatabaseContext()
        self.user_id = user_id  # Current logged-in user's ID for data isolation

    @property
    def db(self) -> DatabaseContext:
        return self.db_context

    def _encrypt(self, value: Optional[str]) -> Optional[str]:
        return self.db.encrypt(value)

    def _decrypt(self, value: Optional[str]) -> Optional[str]:
        return self.db.decrypt(value)


class StudentRepository(BaseRepository):
    def list_students(self, limit: int = 50) -> List[Student]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute("SELECT * FROM students WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (self.user_id, limit))
            else:
                cur.execute("SELECT * FROM students ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            students: List[Student] = []
            for row in rows:
                data = dict(row)
                data.pop("user_id", None)  # Don't pass to model
                data["given_name"] = self._decrypt(data.get("given_name"))
                data["family_name"] = self._decrypt(data.get("family_name"))
                data["identifier"] = self._decrypt(data.get("identifier"))
                students.append(Student(**data))
            return students

    def get_student(self, student_id: int) -> Optional[Student]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute("SELECT * FROM students WHERE id = ? AND user_id = ?", (student_id, self.user_id))
            else:
                cur.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data.pop("user_id", None)
            data["given_name"] = self._decrypt(data.get("given_name"))
            data["family_name"] = self._decrypt(data.get("family_name"))
            data["identifier"] = self._decrypt(data.get("identifier"))
            return Student(**data)

    def create_student(self, student: Student) -> Student:
        uid = self.user_id or 1
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO students (given_name, family_name, dob, identifier, created_at, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    self._encrypt(student.given_name),
                    self._encrypt(student.family_name),
                    student.dob.isoformat() if student.dob else None,
                    self._encrypt(student.identifier),
                    student.created_at.isoformat(),
                    uid,
                ),
            )
            student.id = cur.lastrowid
            _log_sync(conn, "students", student.id, "INSERT", {
                "given_name": student.given_name, "family_name": student.family_name,
                "dob": student.dob.isoformat() if student.dob else None,
                "identifier": student.identifier, "created_at": student.created_at.isoformat(),
            })
            return student

    def update_student(self, student: Student) -> Student:
        if student.id is None:
            raise ValueError("Student must have id for update")
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "UPDATE students SET given_name=?, family_name=?, dob=?, identifier=? WHERE id=?",
                (
                    self._encrypt(student.given_name),
                    self._encrypt(student.family_name),
                    student.dob.isoformat() if student.dob else None,
                    self._encrypt(student.identifier),
                    student.id,
                ),
            )
            _log_sync(conn, "students", student.id, "UPDATE", {
                "given_name": student.given_name, "family_name": student.family_name,
                "dob": student.dob.isoformat() if student.dob else None,
                "identifier": student.identifier, "created_at": student.created_at.isoformat(),
            })
            return student

    def delete_student(self, student_id: int) -> None:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("DELETE FROM students WHERE id = ?", (student_id,))
            _log_sync(conn, "students", student_id, "DELETE", {})


class SessionRepository(BaseRepository):
    def create_session(self, session: Session) -> Session:
        uid = self.user_id or 1
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sessions (student_id, scale, raw_scores, total_score, notes, created_at, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session.student_id,
                    session.scale,
                    json.dumps(session.raw_scores),
                    session.total_score if session.total_score is not None else 0.0,
                    session.notes,
                    session.created_at.isoformat(),
                    uid,
                ),
            )
            session.id = cur.lastrowid
            _log_sync(conn, "sessions", session.id, "INSERT", {
                "student_id": session.student_id, "scale": session.scale,
                "raw_scores": session.raw_scores, "total_score": session.total_score,
                "notes": session.notes, "created_at": session.created_at.isoformat(),
            })
            return session

    def get_session(self, session_id: int) -> Optional[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute("SELECT * FROM sessions WHERE id = ? AND user_id = ?", (session_id, self.user_id))
            else:
                cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data.pop("user_id", None)
            data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
            return Session(**data)

    def list_sessions_for_student(self, student_id: int) -> List[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute("SELECT * FROM sessions WHERE student_id = ? AND user_id = ? ORDER BY created_at DESC", (student_id, self.user_id))
            else:
                cur.execute("SELECT * FROM sessions WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
            rows = cur.fetchall()
            sessions: List[Session] = []
            for r in rows:
                data = dict(r)
                data.pop("user_id", None)
                data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
                sessions.append(Session(**data))
            return sessions

    def get_latest_session_for_student(self, student_id: int) -> Optional[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute(
                    "SELECT * FROM sessions WHERE student_id = ? AND user_id = ? ORDER BY created_at DESC LIMIT 1",
                    (student_id, self.user_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM sessions WHERE student_id = ? ORDER BY created_at DESC LIMIT 1",
                    (student_id,),
                )
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data.pop("user_id", None)
            data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
            return Session(**data)

    def delete_session(self, session_id: int) -> None:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            _log_sync(conn, "sessions", session_id, "DELETE", {})

    def get_recent_sessions(self, limit: int = 3) -> List[dict]:
        """Get recent sessions across all students with student info in one query."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute(
                    """
                    SELECT s.id, s.student_id, s.scale, s.raw_scores, s.total_score,
                           s.notes, s.created_at, st.given_name, st.family_name
                    FROM sessions s
                    JOIN students st ON s.student_id = st.id
                    WHERE s.user_id = ?
                    ORDER BY s.created_at DESC
                    LIMIT ?
                    """,
                    (self.user_id, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT s.id, s.student_id, s.scale, s.raw_scores, s.total_score,
                           s.notes, s.created_at, st.given_name, st.family_name
                    FROM sessions s
                    JOIN students st ON s.student_id = st.id
                    ORDER BY s.created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
            results = []
            for r in rows:
                data = dict(r)
                given = data.pop("given_name", "")
                family = data.pop("family_name", "")
                data.pop("user_id", None)
                data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
                sess = Session(**data)
                results.append({"session": sess, "given_name": given, "family_name": family})
            return results

    def get_dashboard_stats(self) -> dict:
        """Get aggregate stats in a single query: total sessions, average score."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute("SELECT COUNT(*) as cnt, AVG(total_score) as avg_score FROM sessions WHERE user_id = ?", (self.user_id,))
            else:
                cur.execute("SELECT COUNT(*) as cnt, AVG(total_score) as avg_score FROM sessions")
            row = cur.fetchone()
            return {"total_sessions": row["cnt"] or 0, "avg_score": row["avg_score"] or 0}

    def get_latest_session_per_student(self) -> dict:
        """Get latest session for every student in one query. Returns {student_id: Session}."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            if self.user_id is not None:
                cur.execute(
                    """
                    SELECT s.* FROM sessions s
                    INNER JOIN (
                        SELECT student_id, MAX(created_at) as max_date
                        FROM sessions WHERE user_id = ? GROUP BY student_id
                    ) latest ON s.student_id = latest.student_id AND s.created_at = latest.max_date
                    WHERE s.user_id = ?
                    """,
                    (self.user_id, self.user_id),
                )
            else:
                cur.execute(
                    """
                    SELECT s.* FROM sessions s
                    INNER JOIN (
                        SELECT student_id, MAX(created_at) as max_date
                        FROM sessions GROUP BY student_id
                    ) latest ON s.student_id = latest.student_id AND s.created_at = latest.max_date
                    """
                )
            rows = cur.fetchall()
            result = {}
            for r in rows:
                data = dict(r)
                data.pop("user_id", None)
                data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
                sess = Session(**data)
                result[sess.student_id] = sess
            return result

    def update_session(self, session: Session) -> Session:
        """Update an existing session's scores and notes."""
        if session.id is None:
            raise ValueError("Session must have id for update")
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "UPDATE sessions SET raw_scores=?, total_score=?, notes=? WHERE id=?",
                (
                    json.dumps(session.raw_scores),
                    session.total_score if session.total_score is not None else 0.0,
                    session.notes,
                    session.id,
                ),
            )
            _log_sync(conn, "sessions", session.id, "UPDATE", {
                "student_id": session.student_id, "scale": session.scale,
                "raw_scores": session.raw_scores, "total_score": session.total_score,
                "notes": session.notes, "created_at": session.created_at.isoformat(),
            })
            return session


class UserRepository(BaseRepository):
    def count_users(self) -> int:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS cnt FROM app_users")
            row = cur.fetchone()
            return int(row["cnt"] or 0)

    def get_by_username(self, username: str) -> Optional[AppUser]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM app_users WHERE username = ?", (username.strip().lower(),))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["is_active"] = bool(data.get("is_active", 1))
            data.setdefault("cloud_uid", "")
            return AppUser(**data)

    def get_by_id(self, user_id: int) -> Optional[AppUser]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM app_users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["is_active"] = bool(data.get("is_active", 1))
            data.setdefault("cloud_uid", "")
            return AppUser(**data)

    def get_by_email(self, email: str) -> Optional[AppUser]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM app_users WHERE email = ?", (email.strip().lower(),))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["is_active"] = bool(data.get("is_active", 1))
            data.setdefault("cloud_uid", "")
            return AppUser(**data)

    def create_user(self, user: AppUser) -> AppUser:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO app_users (username, password_hash, full_name, role, is_active, email, cloud_uid, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user.username.strip().lower(),
                    user.password_hash,
                    user.full_name,
                    user.role,
                    1 if user.is_active else 0,
                    getattr(user, 'email', ''),
                    getattr(user, 'cloud_uid', ''),
                    user.created_at.isoformat(),
                ),
            )
            user.id = cur.lastrowid
            return user

    def update_cloud_uid(self, user_id: int, cloud_uid: str) -> None:
        """Store the Supabase UUID for a local user."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("UPDATE app_users SET cloud_uid = ? WHERE id = ?", (cloud_uid, user_id))

    def list_users(self) -> List[AppUser]:
        """List all users (admin only)."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM app_users ORDER BY created_at DESC")
            rows = cur.fetchall()
            users = []
            for row in rows:
                data = dict(row)
                data["is_active"] = bool(data.get("is_active", 1))
                data.setdefault("cloud_uid", "")
                users.append(AppUser(**data))
            return users

