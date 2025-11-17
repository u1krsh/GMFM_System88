from __future__ import annotations

from typing import Dict


def ensure_complete_scores(required_items, scores: Dict[int, int]) -> None:
    missing = [item for item in required_items if item not in scores]
    if missing:
        raise ValueError(f"Missing scores for items: {missing}")
