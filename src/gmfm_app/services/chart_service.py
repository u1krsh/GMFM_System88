from __future__ import annotations

import io
from datetime import datetime
import math
from typing import Iterable, Sequence, Dict, List

import matplotlib

matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt

from gmfm_app.data.models import Session
from gmfm_app.scoring.engine import calculate_gmfm66, calculate_gmfm88


def render_total_score_trend(sessions: Sequence[Session]) -> bytes:
    """Return PNG bytes representing total score trend for provided sessions."""
    if not sessions:
        return b""

    sessions_sorted = sorted(sessions, key=lambda s: s.created_at)
    dates: Iterable[datetime] = [s.created_at for s in sessions_sorted]
    scores = [s.total_score or 0.0 for s in sessions_sorted]

    fig, ax = plt.subplots(figsize=(4, 2))
    ax.plot(dates, scores, marker="o", color="#1976D2")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Total %")
    ax.set_xlabel("Session")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return buffer.getvalue()


def render_score_dashboard(sessions: Sequence[Session]) -> bytes:
    """Render combined chart showing total score and per-domain trends."""
    if not sessions:
        return b""

    sessions_sorted = sorted(sessions, key=lambda s: s.created_at)
    dates: List[datetime] = [s.created_at for s in sessions_sorted]
    totals = [s.total_score or 0.0 for s in sessions_sorted]

    all_domains = set()
    session_results = []
    for session in sessions_sorted:
        result = (
            calculate_gmfm66(session.raw_scores)
            if session.scale == "66"
            else calculate_gmfm88(session.raw_scores)
        )
        session_results.append(result)
        all_domains.update(result["domains"].keys())

    domain_series: Dict[str, List[float]] = {domain: [] for domain in sorted(all_domains)}
    for result in session_results:
        for domain, series in domain_series.items():
            if domain in result["domains"]:
                series.append(result["domains"][domain]["percent"])
            else:
                series.append(math.nan)

    fig, (ax_total, ax_domains) = plt.subplots(2, 1, figsize=(5, 4), sharex=True)

    ax_total.plot(dates, totals, marker="o", color="#1976D2")
    ax_total.set_ylabel("Total %")
    ax_total.set_ylim(0, 100)
    ax_total.grid(True, linestyle="--", alpha=0.3)

    for domain, values in domain_series.items():
        ax_domains.plot(dates, values, marker="o", label=domain)
    ax_domains.set_ylabel("Domain %")
    ax_domains.set_ylim(0, 100)
    ax_domains.grid(True, linestyle="--", alpha=0.3)
    ax_domains.legend(fontsize="x-small", ncol=2)
    ax_domains.set_xlabel("Session")

    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return buffer.getvalue()
