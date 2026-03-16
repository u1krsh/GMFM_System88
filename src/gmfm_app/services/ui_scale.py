from __future__ import annotations

from typing import Any

import flet as ft


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _scale_num(value: Any, scale: float) -> Any:
    if not _is_number(value):
        return value
    scaled = float(value) * scale
    if isinstance(value, int):
        return max(1, int(round(scaled)))
    return scaled


def _scale_spacing(value: Any, scale: float) -> Any:
    if value is None:
        return value
    if _is_number(value):
        return _scale_num(value, scale)

    # Flet spacing objects expose left/top/right/bottom attributes.
    attrs = ("left", "top", "right", "bottom")
    if all(hasattr(value, attr) for attr in attrs):
        try:
            return ft.padding.only(
                left=_scale_num(getattr(value, "left"), scale),
                top=_scale_num(getattr(value, "top"), scale),
                right=_scale_num(getattr(value, "right"), scale),
                bottom=_scale_num(getattr(value, "bottom"), scale),
            )
        except Exception:
            return value
    return value


def get_android_scale(page: ft.Page) -> float:
    """Read Android text scale factor and clamp to a practical UI range."""
    platform = str(getattr(page, "platform", "")).lower()
    if "android" not in platform:
        return 1.0

    media = getattr(page, "media", None)
    factor = getattr(media, "text_scale_factor", None) if media else None
    if not _is_number(factor):
        return 1.0

    # Material-style accessibility range guard.
    factor = float(factor)
    return max(0.85, min(1.60, factor))


def _scale_control(control: ft.Control, scale: float, visited: set[int]) -> None:
    if not isinstance(control, ft.Control):
        return

    control_id = id(control)
    if control_id in visited:
        return
    visited.add(control_id)

    numeric_props = (
        "size",
        "text_size",
        "icon_size",
        "width",
        "height",
        "stroke_width",
        "tooltip_size",
    )
    for prop in numeric_props:
        if hasattr(control, prop):
            try:
                current = getattr(control, prop)
                setattr(control, prop, _scale_num(current, scale))
            except Exception:
                pass

    if hasattr(control, "border_radius"):
        try:
            current = getattr(control, "border_radius")
            setattr(control, "border_radius", _scale_spacing(current, scale))
        except Exception:
            pass

    if hasattr(control, "padding"):
        try:
            current = getattr(control, "padding")
            setattr(control, "padding", _scale_spacing(current, scale))
        except Exception:
            pass

    if hasattr(control, "margin"):
        try:
            current = getattr(control, "margin")
            setattr(control, "margin", _scale_spacing(current, scale))
        except Exception:
            pass

    # Traverse all nested controls generically so every view gets scaled.
    for value in vars(control).values():
        if isinstance(value, ft.Control):
            _scale_control(value, scale, visited)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                if isinstance(item, ft.Control):
                    _scale_control(item, scale, visited)
        elif isinstance(value, dict):
            for item in value.values():
                if isinstance(item, ft.Control):
                    _scale_control(item, scale, visited)


def apply_android_scale(page: ft.Page, root: ft.Control) -> None:
    """Scale a view/control tree to follow Android system accessibility scaling."""
    scale = get_android_scale(page)
    if abs(scale - 1.0) < 0.01:
        return
    _scale_control(root, scale, set())
