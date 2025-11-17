from __future__ import annotations

from typing import Any, Dict, List

from gmfm_app.data.models import Patient, Session


class SyncService:
    """Placeholder for future offline/online sync."""

    def export_payload(self, patients: List[Patient], sessions: List[Session]) -> Dict[str, Any]:
        return {
            "patients": [patient.dict() for patient in patients],
            "sessions": [session.dict() for session in sessions],
        }

    def apply_remote_changes(self, payload: Dict[str, Any]) -> None:
        # TODO: integrate with real backend
        return None
