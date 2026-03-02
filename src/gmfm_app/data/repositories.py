from __future__ import annotations

import json
from typing import List, Optional
from datetime import datetime, date

from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.models import Student, Session


class BaseRepository:
    def __init__(self, db_context: Optional[DatabaseContext] = None):
        self.db_context = db_context or DatabaseContext()

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
            cur.execute("SELECT * FROM students ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            students: List[Student] = []
            for row in rows:
                data = dict(row)
                data["given_name"] = self._decrypt(data.get("given_name"))
                data["family_name"] = self._decrypt(data.get("family_name"))
                data["identifier"] = self._decrypt(data.get("identifier"))
                students.append(Student(**data))
            return students

    def get_student(self, student_id: int) -> Optional[Student]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["given_name"] = self._decrypt(data.get("given_name"))
            data["family_name"] = self._decrypt(data.get("family_name"))
            data["identifier"] = self._decrypt(data.get("identifier"))
            return Student(**data)

    def create_student(self, student: Student) -> Student:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO students (given_name, family_name, dob, identifier, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    self._encrypt(student.given_name),
                    self._encrypt(student.family_name),
                    student.dob.isoformat() if student.dob else None,
                    self._encrypt(student.identifier),
                    student.created_at.isoformat(),
                ),
            )
            student.id = cur.lastrowid
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
            return student

    def delete_student(self, student_id: int) -> None:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("DELETE FROM students WHERE id = ?", (student_id,))


class SessionRepository(BaseRepository):
    def create_session(self, session: Session) -> Session:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sessions (student_id, scale, raw_scores, total_score, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session.student_id,
                    session.scale,
                    json.dumps(session.raw_scores),
                    session.total_score if session.total_score is not None else 0.0,
                    session.notes,
                    session.created_at.isoformat(),
                ),
            )
            session.id = cur.lastrowid
            return session

    def get_session(self, session_id: int) -> Optional[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
            return Session(**data)

    def list_sessions_for_student(self, student_id: int) -> List[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
            rows = cur.fetchall()
            sessions: List[Session] = []
            for r in rows:
                data = dict(r)
                data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
                sessions.append(Session(**data))
            return sessions

    def get_latest_session_for_student(self, student_id: int) -> Optional[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM sessions WHERE student_id = ? ORDER BY created_at DESC LIMIT 1",
                (student_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
            return Session(**data)

    def delete_session(self, session_id: int) -> None:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def get_recent_sessions(self, limit: int = 3) -> List[dict]:
        """Get recent sessions across all students with student info in one query."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
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
                data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
                sess = Session(**data)
                results.append({"session": sess, "given_name": given, "family_name": family})
            return results

    def get_dashboard_stats(self) -> dict:
        """Get aggregate stats in a single query: total sessions, average score."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt, AVG(total_score) as avg_score FROM sessions")
            row = cur.fetchone()
            return {"total_sessions": row["cnt"] or 0, "avg_score": row["avg_score"] or 0}

    def get_latest_session_per_student(self) -> dict:
        """Get latest session for every student in one query. Returns {student_id: Session}."""
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
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
            return session
