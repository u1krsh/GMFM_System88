from __future__ import annotations

from typing import Dict, Literal, Tuple

from pydantic import BaseModel, validator

from gmfm_app.data.models import Session
from gmfm_app.data.repositories import SessionRepository
from gmfm_app.scoring.engine import calculate_gmfm66, calculate_gmfm88


class ScoreRequest(BaseModel):
    patient_id: int
    scale: Literal["66", "88"]
    raw_scores: Dict[int, int]

    @validator("raw_scores")
    def ensure_scores_in_range(cls, value: Dict[int, int]):
        for k, v in value.items():
            if not 0 <= int(v) <= 3:
                raise ValueError(f"Item {k} must be between 0 and 3")
        return value


class ScoringService:
    def __init__(self, session_repo: SessionRepository | None = None):
        self.session_repo = session_repo or SessionRepository()

    def score_session(self, payload: ScoreRequest) -> Tuple[Session, Dict[str, object]]:
        if payload.scale == "66":
            result = calculate_gmfm66(payload.raw_scores)
        else:
            result = calculate_gmfm88(payload.raw_scores)

        session = Session(
            patient_id=payload.patient_id,
            scale=payload.scale,
            raw_scores=payload.raw_scores,
            total_score=result["total_percent"],
        )
        session = self.session_repo.create_session(session)
        return session, result
