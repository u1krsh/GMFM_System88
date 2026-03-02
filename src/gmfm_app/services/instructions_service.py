"""
Instructions Service - Load exercise instructions from static JSON (no python-docx dependency)
"""
import os
import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ExerciseInstruction:
    """Holds parsed instruction data for a single exercise."""
    number: int
    title: str
    scoring_criteria: Dict[str, str]  # {"0": "...", "1": "...", "2": "...", "3": "..."}
    starting_position: str
    instructions: str


def _find_data_path() -> Path:
    """Find the instructions_data.json file, handling both dev and Android bundled scenarios."""
    candidates = []
    
    # 1. Same directory as this file (normal case)
    try:
        candidates.append(Path(__file__).with_name("instructions_data.json"))
    except Exception:
        pass
    
    # 2. Current working directory (Android bundled case)
    try:
        candidates.append(Path.cwd() / "gmfm_app" / "services" / "instructions_data.json")
    except Exception:
        pass
    
    # 3. Relative to FLET_APP_STORAGE_DATA (Android app storage)
    storage = os.getenv("FLET_APP_STORAGE_DATA")
    if storage:
        candidates.append(Path(storage).parent / "gmfm_app" / "services" / "instructions_data.json")
        candidates.append(Path(storage) / "gmfm_app" / "services" / "instructions_data.json")
    
    # 4. Search sys.path (covers serious_python extraction directory)
    import sys
    for sp in sys.path:
        if sp:
            candidates.append(Path(sp) / "gmfm_app" / "services" / "instructions_data.json")
    
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    
    # Fallback to first candidate
    return candidates[0] if candidates else Path("instructions_data.json")


@lru_cache(maxsize=1)
def _load_instructions() -> Dict[int, ExerciseInstruction]:
    """Load instructions from JSON file."""
    data_path = _find_data_path()
    
    if not data_path.exists():
        return {}
    
    try:
        with data_path.open(encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception:
        return {}
    
    instructions: Dict[int, ExerciseInstruction] = {}
    for key, value in raw_data.items():
        try:
            num = int(key)
            instructions[num] = ExerciseInstruction(
                number=num,
                title=value.get("title", ""),
                scoring_criteria=value.get("scoring_criteria", {}),
                starting_position=value.get("starting_position", ""),
                instructions=value.get("instructions", ""),
            )
        except (ValueError, KeyError):
            continue
    
    return instructions


def get_instruction(item_number: int) -> Optional[ExerciseInstruction]:
    """Get instruction for a specific exercise number."""
    return _load_instructions().get(item_number)


def has_instructions() -> bool:
    """Check if instructions are available."""
    return bool(_load_instructions())
