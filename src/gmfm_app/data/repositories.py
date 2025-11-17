from __future__ import annotations

import json
from typing import List, Optional

from gmfm_app.data.database import DatabaseContext
from gmfm_app.data.models import Patient, Session


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


class PatientRepository(BaseRepository):
    def list_patients(self, limit: int = 50) -> List[Patient]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM patients ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            patients: List[Patient] = []
            for row in rows:
                data = dict(row)
                data["given_name"] = self._decrypt(data.get("given_name"))
                data["family_name"] = self._decrypt(data.get("family_name"))
                data["identifier"] = self._decrypt(data.get("identifier"))
                patients.append(Patient(**data))
            return patients

    def get_patient(self, patient_id: int) -> Optional[Patient]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
            row = cur.fetchone()
            if row is None:
                return None
            data = dict(row)
            data["given_name"] = self._decrypt(data.get("given_name"))
            data["family_name"] = self._decrypt(data.get("family_name"))
            data["identifier"] = self._decrypt(data.get("identifier"))
            return Patient(**data)

    def create_patient(self, patient: Patient) -> Patient:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO patients (given_name, family_name, dob, identifier, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    self._encrypt(patient.given_name),
                    self._encrypt(patient.family_name),
                    patient.dob.isoformat() if patient.dob else None,
                    self._encrypt(patient.identifier),
                    patient.created_at.isoformat(),
                ),
            )
            patient.id = cur.lastrowid
            return patient

    def update_patient(self, patient: Patient) -> Patient:
        if patient.id is None:
            raise ValueError("Patient must have id for update")
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "UPDATE patients SET given_name=?, family_name=?, dob=?, identifier=? WHERE id=?",
                (
                    self._encrypt(patient.given_name),
                    self._encrypt(patient.family_name),
                    patient.dob.isoformat() if patient.dob else None,
                    self._encrypt(patient.identifier),
                    patient.id,
                ),
            )
            return patient

    def delete_patient(self, patient_id: int) -> None:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("DELETE FROM patients WHERE id = ?", (patient_id,))


class SessionRepository(BaseRepository):
    def create_session(self, session: Session) -> Session:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sessions (patient_id, scale, raw_scores, total_score, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    session.patient_id,
                    session.scale,
                    json.dumps(session.raw_scores),
                    session.total_score if session.total_score is not None else 0.0,
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

    def list_sessions_for_patient(self, patient_id: int) -> List[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,))
            rows = cur.fetchall()
            sessions: List[Session] = []
            for r in rows:
                data = dict(r)
                data["raw_scores"] = json.loads(data["raw_scores"]) if data.get("raw_scores") else {}
                sessions.append(Session(**data))
            return sessions

    def get_latest_session_for_patient(self, patient_id: int) -> Optional[Session]:
        with self.db() as conn:  # type: ignore[misc]
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM sessions WHERE patient_id = ? ORDER BY created_at DESC LIMIT 1",
                (patient_id,),
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
