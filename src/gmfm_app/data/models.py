from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field, constr, conint


class Patient(BaseModel):
    id: Optional[int] = None
    given_name: constr(min_length=1)
    family_name: constr(min_length=1)
    dob: Optional[date] = None
    identifier: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    id: Optional[int] = None
    patient_id: int
    scale: Literal["66", "88"]
    raw_scores: Dict[int, conint(ge=0, le=3)]
    total_score: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
