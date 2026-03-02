from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional, Literal

try:
    from pydantic import BaseModel, Field, constr, conint

    class Student(BaseModel):
        id: Optional[int] = None
        given_name: constr(min_length=1)
        family_name: constr(min_length=1)
        dob: Optional[date] = None
        identifier: Optional[str] = None
        created_at: datetime = Field(default_factory=datetime.utcnow)

    class Session(BaseModel):
        id: Optional[int] = None
        student_id: int
        scale: Literal["66", "88"]
        raw_scores: Dict[int, conint(ge=0, le=3)]
        total_score: Optional[float] = None
        notes: Optional[str] = None
        created_at: datetime = Field(default_factory=datetime.utcnow)

except Exception:
    from dataclasses import dataclass, field

    def _parse_datetime(val):
        """Coerce ISO‑string → datetime (SQLite returns strings)."""
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except (ValueError, TypeError):
                return datetime.utcnow()
        return val if val is not None else datetime.utcnow()

    def _parse_date(val):
        """Coerce ISO‑string → date."""
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, str):
            try:
                return date.fromisoformat(val)
            except (ValueError, TypeError):
                return None
        return None

    @dataclass
    class Student:
        given_name: str = ""
        family_name: str = ""
        id: Optional[int] = None
        dob: Optional[date] = None
        identifier: Optional[str] = None
        created_at: datetime = field(default_factory=datetime.utcnow)

        def __post_init__(self):
            self.created_at = _parse_datetime(self.created_at)
            if self.dob is not None:
                self.dob = _parse_date(self.dob)

    @dataclass
    class Session:
        student_id: int = 0
        scale: str = "88"
        raw_scores: Dict = field(default_factory=dict)
        id: Optional[int] = None
        total_score: Optional[float] = None
        notes: Optional[str] = None
        created_at: datetime = field(default_factory=datetime.utcnow)

        def __post_init__(self):
            self.created_at = _parse_datetime(self.created_at)
            # Ensure raw_scores keys are ints (json.loads returns string keys)
            if self.raw_scores and isinstance(self.raw_scores, dict):
                self.raw_scores = {int(k): int(v) for k, v in self.raw_scores.items()}
