from __future__ import annotations

from datetime import datetime


def human_date(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")
