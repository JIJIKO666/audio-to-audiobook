from __future__ import annotations

import os
import re
from pathlib import Path

from utils import _natural_key, _extract_order_num

AUDIO_EXTS = frozenset({".m4a", ".mp3"})
VIDEO_EXTS = frozenset({".mp4", ".mkv", ".mov", ".m4v", ".avi", ".webm"})
MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS
IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".gif", ".avif", ".heic", ".heif"})


def get_direct_audio(folder: Path) -> list[Path]:
    """Audio/video files directly inside folder, ordered by leading track number then natural sort.
    Files without a leading number come last."""
    files = [f for f in folder.iterdir()
             if f.is_file() and f.suffix.lower() in MEDIA_EXTS]

    def _sort_key(f: Path):
        num, _ = _extract_order_num(f.stem)
        if num is not None:
            return (0, num, _natural_key(f.name))
        return (1, 0, _natural_key(f.name))

    return sorted(files, key=_sort_key)


def find_audiobook_dirs(root: Path) -> list[Path]:
    """All directories (at any depth) that directly contain at least one audio file."""
    result = []
    for dirpath, dirs, files in os.walk(root):
        dirs.sort(key=_natural_key)
        if any(Path(f).suffix.lower() in MEDIA_EXTS for f in files):
            result.append(Path(dirpath))
    return result


def find_cover(folder: Path, root: Path) -> Path | None:
    """Look for an image in folder, then walk up to root."""
    p = folder
    while True:
        imgs = sorted(
            [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS],
            key=lambda f: _natural_key(f.name)
        )
        for img in imgs:
            if "cover" in img.stem.lower():
                return img
        if imgs:
            return imgs[0]
        if p == root or p == p.parent:
            break
        p = p.parent
    return None


_BRACKET_RE = re.compile(r"^\[(.+?)\]\[(.+?)\]")


def parse_meta(folder: Path, root: Path | None = None) -> dict[str, str]:
    """
    Walk up from folder to root looking for a folder whose name matches
    '[album][artist]'. The first such match provides album and artist for
    all audiobooks inside it.

    Title is always folder.name, except blank when folder.name itself
    matches the bracket format.
    """
    album = ""
    artist = ""
    p = folder
    while True:
        m = _BRACKET_RE.match(p.name)
        if m:
            album, artist = m.group(1), m.group(2)
            break
        if root is None or p == root or p == p.parent:
            break
        p = p.parent

    if _BRACKET_RE.match(folder.name):
        # Folder name itself is bracket-formatted — it's the container, not a chapter
        title = ""
    elif folder == root and not album:
        # Imported root has no bracket format anywhere — it is the single audiobook, blank title
        title = ""
    else:
        title = folder.name
    return {"album": album, "title": title, "author": artist}
