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

    @dataclass
    class Student:
        given_name: str = ""
        family_name: str = ""
        id: Optional[int] = None
        dob: Optional[date] = None
        identifier: Optional[str] = None
        created_at: datetime = field(default_factory=datetime.utcnow)

    @dataclass
    class Session:
        student_id: int = 0
        scale: str = "88"
        raw_scores: Dict = field(default_factory=dict)
        id: Optional[int] = None
        total_score: Optional[float] = None
        notes: Optional[str] = None
        created_at: datetime = field(default_factory=datetime.utcnow)
