from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import QSettings


def _natural_key(s: str) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


_ORDER_PREFIX_RE = re.compile(r"^[\(\[]?(\d+)[\)\]]?[.\s_\-]+")


def _extract_order_num(stem: str) -> tuple[int | None, str]:
    """Return (order_number, remaining_title) or (None, stem) if no prefix found."""
    m = _ORDER_PREFIX_RE.match(stem)
    if m:
        return int(m.group(1)), stem[m.end():].strip("_- ") or stem
    return None, stem


def clean_title(p: Path) -> str:
    remove = QSettings("audiobook-maker", "AudiobookMaker").value(
        "remove_order_num", True, type=bool
    )
    num, stripped = _extract_order_num(p.stem)
    if remove and num is not None:
        return stripped
    return p.stem


def fmt_dur(secs: float | None) -> str:
    if secs is None:
        return "—"
    s = int(secs)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def fmt_size(b: int) -> str:
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB"
    return f"{b / 1024:.0f} KB"
