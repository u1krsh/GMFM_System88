from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


def _find_data_path() -> Path:
    """Find the items_data.json file, handling both dev and bundled scenarios."""
    candidates = []
    
    # 1. Relative to this file (normal case)
    try:
        local_path = Path(__file__).with_name("items_data.json")
        candidates.append(local_path)
    except Exception:
        pass
    
    # 2. Current working directory (Android bundled case)
    try:
        candidates.append(Path.cwd() / "gmfm_app" / "scoring" / "items_data.json")
    except Exception:
        pass
    
    # 3. Relative to FLET_APP_STORAGE_DATA
    storage = os.getenv("FLET_APP_STORAGE_DATA")
    if storage:
        candidates.append(Path(storage).parent / "gmfm_app" / "scoring" / "items_data.json")
        candidates.append(Path(storage) / "gmfm_app" / "scoring" / "items_data.json")
    
    # 4. Search sys.path (covers serious_python extraction directory)
    import sys
    for sp in sys.path:
        if sp:
            candidates.append(Path(sp) / "gmfm_app" / "scoring" / "items_data.json")
    
    # 5. Walk up from __file__ to find it
    try:
        p = Path(__file__).resolve().parent
        for _ in range(5):
            candidate = p / "gmfm_app" / "scoring" / "items_data.json"
            candidates.append(candidate)
            p = p.parent
    except Exception:
        pass
    
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    
    # Fallback to first candidate (will raise error if missing)
    return candidates[0] if candidates else Path("items_data.json")


def _safe_find_data_path() -> Path:
    """Safe wrapper that never raises during module load."""
    try:
        return _find_data_path()
    except Exception:
        return Path("items_data.json")


DATA_PATH = _safe_find_data_path()


@dataclass(frozen=True)
class GMFMItem:
    number: int
    description: str
    gmfm66: bool


@dataclass(frozen=True)
class GMFMDomain:
    dimension: str
    title: str
    items: Sequence[GMFMItem]

    @property
    def label(self) -> str:
        return f"{self.dimension}: {self.title}"

    @property
    def friendly_name(self) -> str:
        return self.title.title()


@lru_cache(maxsize=1)
def _load_raw() -> Dict[str, Dict[str, object]]:
    if not DATA_PATH.exists():  # pragma: no cover - sanity guard
        raise FileNotFoundError(f"Missing GMFM item catalog at {DATA_PATH}")
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_domains(scale: str = "88") -> List[GMFMDomain]:
    """Return all GMFM-88 domains and items."""
    data = _load_raw()
    domains: List[GMFMDomain] = []
    for letter in sorted(data.keys()):
        payload = data[letter]
        raw_items: Iterable[Dict[str, object]] = payload.get("items", [])  # type: ignore[assignment]
        items: List[GMFMItem] = []
        for item in raw_items:
            items.append(
                GMFMItem(
                    number=int(item["number"]),
                    description=str(item["description"]),
                    gmfm66=bool(item.get("gmfm66")),
                )
            )
        if not items:
            continue
        domains.append(
            GMFMDomain(
                dimension=str(payload.get("dimension", letter)),
                title=str(payload.get("title", "")),
                items=tuple(items),
            )
        )
    return domains


def build_item_number_map(scale: str = "88") -> Dict[str, List[int]]:
    mapping: Dict[str, List[int]] = {}
    for domain in get_domains(scale):
        mapping[domain.friendly_name] = [item.number for item in domain.items]
    return mapping


def all_item_numbers(scale: str = "88") -> List[int]:
    numbers: List[int] = []
    for domain in get_domains(scale):
        numbers.extend(item.number for item in domain.items)
    return numbers
