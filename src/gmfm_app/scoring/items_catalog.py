from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


def _find_data_path() -> Path:
    """Find the items_data.json file, handling both dev and bundled scenarios."""
    # Try relative to this file first (normal case)
    local_path = Path(__file__).with_name("items_data.json")
    if local_path.exists():
        return local_path
    
    # Try current working directory (Android bundled case)
    cwd_path = Path.cwd() / "gmfm_app" / "scoring" / "items_data.json"
    if cwd_path.exists():
        return cwd_path
    
    # Try relative to FLET_APP_STORAGE_DATA
    storage = os.getenv("FLET_APP_STORAGE_DATA")
    if storage:
        storage_path = Path(storage).parent / "gmfm_app" / "scoring" / "items_data.json"
        if storage_path.exists():
            return storage_path
    
    # Fallback to local path (will raise error if missing)
    return local_path


DATA_PATH = _find_data_path()


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
    scale_key = "66" if scale == "66" else "88"
    data = _load_raw()
    domains: List[GMFMDomain] = []
    for letter in sorted(data.keys()):
        payload = data[letter]
        raw_items: Iterable[Dict[str, object]] = payload.get("items", [])  # type: ignore[assignment]
        filtered: List[GMFMItem] = []
        for item in raw_items:
            flag = bool(item.get("gmfm66"))
            if scale_key == "66" and not flag:
                continue
            filtered.append(
                GMFMItem(
                    number=int(item["number"]),
                    description=str(item["description"]),
                    gmfm66=flag,
                )
            )
        if not filtered:
            continue
        domains.append(
            GMFMDomain(
                dimension=str(payload.get("dimension", letter)),
                title=str(payload.get("title", "")),
                items=tuple(filtered),
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
