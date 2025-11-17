from __future__ import annotations

from typing import Any

from kivymd.uix.screen import MDScreen

from gmfm_app.services.scoring_service import ScoringService, ScoreRequest
from gmfm_app.data.repositories import SessionRepository


class SessionFormScreen(MDScreen):
    def __init__(self, db_context, **kwargs: Any):  # type: ignore[override]
        super().__init__(**kwargs)
        self.scoring_service = ScoringService(SessionRepository(db_context))

    def parse_scores(self, text: str):
        raw_scores = {}
        parts = [p.strip() for p in text.split(",") if p.strip()]
        for part in parts:
            if ":" not in part:
                continue
            item, value = part.split(":", 1)
            raw_scores[int(item.strip())] = int(value.strip())
        return raw_scores

    def save_session(self) -> None:
        patient_id_field = self.ids.get("patient_id_field")
        scale_field = self.ids.get("scale_field")
        scores_field = self.ids.get("scores_field")
        try:
            payload = ScoreRequest(
                patient_id=int(patient_id_field.text),
                scale=scale_field.text.strip() or "66",
                raw_scores=self.parse_scores(scores_field.text),
            )
        except Exception:
            return
        self.scoring_service.score_session(payload)
        self.manager.current = "dashboard"
        dashboard = self.manager.get_screen("dashboard")
        dashboard.refresh()
