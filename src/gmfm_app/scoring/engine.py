"""GMFM scoring engine (MVP).
Provides functions to calculate domain percentages and total percentage for both GMFM-66 and GMFM-88.
Input: raw_scores -> dict[int, int] mapping item_id to score (0..3)
Output: dict with per-domain percent (0-100) and total_percent
"""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

from gmfm_app.scoring.constants import GMFM66_ITEMS, GMFM88_ITEMS, MAX_ITEM_SCORE


def _score_domain(item_ids: Iterable[int], raw_scores: Dict[int, int]) -> Tuple[float, int]:
    """Return (percent, n_items) for given domain."""
    if not item_ids:
        return 0.0, 0
    total = 0
    count = 0
    for iid in item_ids:
        if iid in raw_scores:
            val = raw_scores[iid]
            # clamp 0..MAX_ITEM_SCORE
            val = max(0, min(MAX_ITEM_SCORE, int(val)))
            total += val
            count += 1
    if count == 0:
        return 0.0, len(list(item_ids))
    max_possible = count * MAX_ITEM_SCORE
    percent = (total / max_possible) * 100.0
    return percent, count


def calculate_gmfm_scores(raw_scores: Dict[int, int], scale: str = "66") -> Dict[str, object]:
    """Calculate domain percentages and total for GMFM-66 or GMFM-88.

    Returns:
      {
        "scale": "66",
        "domains": {domain_name: {"percent": float, "n_items": int}},
        "total_percent": float,
        "items_scored": int,
        "items_total": int,
      }
    """
    items_map = GMFM66_ITEMS if scale == "66" else GMFM88_ITEMS

    domains: Dict[str, Dict[str, object]] = {}
    total_score = 0.0
    total_items_scored = 0
    total_items = 0

    for domain, item_ids in items_map.items():
        percent, n_items_scored = _score_domain(item_ids, raw_scores)
        domains[domain] = {"percent": round(percent, 2), "n_items_scored": n_items_scored, "n_items_total": len(item_ids)}
        # accumulate raw totals for overall calculation: convert percent back to raw sum
        total_items_scored += n_items_scored
        total_items += len(item_ids)
        # compute raw contribution
        total_score += (percent / 100.0) * (len(item_ids) * MAX_ITEM_SCORE)

    # total percent computed as (sum of raw scores) / (max_possible_all_items) *100
    max_possible_all = total_items * MAX_ITEM_SCORE if total_items > 0 else 1
    total_percent = (total_score / max_possible_all) * 100.0

    return {
        "scale": scale,
        "domains": domains,
        "total_percent": round(total_percent, 2),
        "items_scored": total_items_scored,
        "items_total": total_items,
    }


# convenience wrappers
def calculate_gmfm66(raw_scores: Dict[int, int]) -> Dict[str, object]:
    return calculate_gmfm_scores(raw_scores, scale="66")


def calculate_gmfm88(raw_scores: Dict[int, int]) -> Dict[str, object]:
    return calculate_gmfm_scores(raw_scores, scale="88")
