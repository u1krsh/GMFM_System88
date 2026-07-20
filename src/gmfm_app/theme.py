"""
Shared theme colours, domain constants, and colour helpers for GMFM app views.

All views must import from here instead of declaring their own constants.
"""

# ── Brand palette ──────────────────────────────────────────────────────────
PRIMARY = "#0D9488"
SECONDARY = "#7C3AED"
SUCCESS = "#10B981"
WARNING = "#F59E0B"
ERROR = "#EF4444"
INFO = "#3B82F6"

# ── Light / Dark colour maps ───────────────────────────────────────────────
DARK_BG = "#0F172A"
LIGHT_BG = "#F8FAFC"


def get_colors(is_dark: bool) -> dict:
    """Return a colour-map dict for the given theme mode."""
    if is_dark:
        return {
            "BG": DARK_BG,
            "CARD": "#1E293B",
            "BORDER": "#334155",
            "TEXT1": "#F8FAFC",
            "TEXT2": "#94A3B8",
            "TEXT3": "#64748B",
        }
    return {
        "BG": LIGHT_BG,
        "CARD": "#FFFFFF",
        "BORDER": "#E2E8F0",
        "TEXT1": "#1E293B",
        "TEXT2": "#64748B",
        "TEXT3": "#94A3B8",
    }


# ── GMFM domain metadata ───────────────────────────────────────────────────
DOMAIN_COLORS = {
    "A": "#EF4444",
    "B": "#F59E0B",
    "C": "#10B981",
    "D": "#3B82F6",
    "E": "#8B5CF6",
}

DOMAIN_ICONS = {
    "A": "hotel",
    "B": "weekend",
    "C": "child_care",
    "D": "accessibility_new",
    "E": "directions_run",
}

DOMAIN_NAMES = {
    "A": "Lying & Rolling",
    "B": "Sitting",
    "C": "Crawling & Kneeling",
    "D": "Standing",
    "E": "Walking & Running",
}
