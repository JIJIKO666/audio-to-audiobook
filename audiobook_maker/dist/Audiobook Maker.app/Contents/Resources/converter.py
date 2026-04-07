"""
FFmpeg-based audiobook converter.
Ported from m4a_to_audiobook.ipynb.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def _which(cmd: str) -> str:
    path = shutil.which(cmd)
    if path is None:
        # Try common Homebrew install paths (needed inside .app bundles)
        for prefix in ("/usr/local/bin", "/opt/homebrew/bin"):
            p = Path(prefix) / cmd
            if p.exists():
                return str(p)
    if not path:
        raise FileNotFoundError(
            f"'{cmd}' not found. Install via: brew install ffmpeg"
        )
    return path


def _escape(s: str) -> str:
    """Escape a string for FFMETADATA format."""
    for ch in ("\\", "=", ";", "#"):
        s = s.replace(ch, "\\" + ch)
    return s.replace("\n", "\\\n")


def get_duration(path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    ffprobe = _which("ffprobe")

    r = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a:0",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        pass

    # Fallback: duration_ts / sample_rate
    r2 = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=duration_ts,sample_rate", "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    try:
        s = json.loads(r2.stdout)["streams"][0]
        return float(s["duration_ts"]) / float(s["sample_rate"])
    except (KeyError, ValueError, IndexError, json.JSONDecodeError):
        pass

    raise ValueError(f"Cannot determine duration: {path}")


def _process_cover(src: Path, dst: Path, max_w: int = 0, max_h: int = 0, max_kb: int = 0) -> None:
    """Resize then compress a cover image. 0 means no change for that dimension."""
    try:
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import Qt as _Qt
    except ImportError:
        shutil.copy2(src, dst)
        return

    img = QImage(str(src))
    if img.isNull():
        shutil.copy2(src, dst)
        return

    # Step 1: resize to exact target dimensions (only axes that are specified)
    target_w = max_w if max_w > 0 else img.width()
    target_h = max_h if max_h > 0 else img.height()
    if target_w != img.width() or target_h != img.height():
        img = img.scaled(
            target_w, target_h,
            _Qt.AspectRatioMode.IgnoreAspectRatio,
            _Qt.TransformationMode.SmoothTransformation,
        )

    # Step 2: compress to KB limit
    if max_kb > 0:
        for quality in range(92, 0, -1):
            img.save(str(dst), "JPEG", quality)
            if dst.exists() and dst.stat().st_size <= max_kb * 1024:
                break
    else:
        img.save(str(dst), "JPEG", 92)


def build_audiobook(
    files: list[Path],
    titles: list[str],
    output: Path,
    title: str,
    author: str,
    album: str,
    cover: Path | None = None,
    audio_codec: str = "aac",
    audio_quality: str | None = None,
    cover_max_w: int = 0,
    cover_max_h: int = 0,
    cover_max_kb: int = 0,
    progress_cb: callable = None,
) -> None:
    """
    Merge audio files into a single .m4b with embedded chapters, cover, metadata.
    Output format is always m4b. audio_codec controls the encoded codec (e.g. 'aac', 'libmp3lame').
    audio_quality: None = copy original codec; '128k' etc = re-encode with audio_codec.
    """
    ffmpeg = _which("ffmpeg")

    def _prog(msg: str):
        if progress_cb:
            progress_cb(msg)

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)

        # 1. Write ffmpeg concat list
        concat_file = tmp / "concat.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for fp in files:
                quoted = "'" + str(fp).replace("'", r"'\''") + "'"
                f.write(f"file {quoted}\n")

        # 2. Merge all files into one stream (no re-encode)
        _prog("Merging audio files…")
        merged = tmp / "merged.m4a"
        r = subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_file), "-map", "0:a", "-c", "copy", str(merged)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise RuntimeError(f"Merge failed:\n{r.stderr[-3000:]}")

        # 3. Get per-file durations for chapter timestamps
        _prog("Reading chapter durations…")
        durations: list[float] = []
        for i, fp in enumerate(files):
            _prog(f"Duration {i + 1}/{len(files)}: {fp.name}")
            durations.append(get_duration(fp))

        # 4. Build FFMETADATA file
        _prog("Writing chapter metadata…")
        meta_file = tmp / "chapters.ffmeta"
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(";FFMETADATA1\n")
            f.write(f"title={_escape(title)}\n")
            f.write(f"artist={_escape(author)}\n")
            f.write(f"album={_escape(album)}\n\n")
            cursor = 0.0
            for fp, dur, ch_title in zip(files, durations, titles):
                start_ms = int(cursor * 1000)
                end_ms = int((cursor + dur) * 1000)
                f.write("[CHAPTER]\nTIMEBASE=1/1000\n")
                f.write(f"START={start_ms}\nEND={end_ms}\n")
                f.write(f"title={_escape(ch_title)}\n\n")
                cursor += dur

        # 5. Process cover: resize then compress
        active_cover: Path | None = cover
        if cover and cover.exists() and (cover_max_w > 0 or cover_max_h > 0 or cover_max_kb > 0):
            _prog("Processing cover image…")
            tmp_cover = tmp / "cover.jpg"
            _process_cover(cover, tmp_cover, max_w=cover_max_w, max_h=cover_max_h, max_kb=cover_max_kb)
            if tmp_cover.exists():
                active_cover = tmp_cover

        # 6. Build final output with cover + chapters
        _prog("Building final audiobook…")
        output.parent.mkdir(parents=True, exist_ok=True)

        has_cover = active_cover and active_cover.exists()
        cmd = [ffmpeg, "-y", "-i", str(merged)]
        if has_cover:
            cmd += ["-i", str(active_cover)]
        cmd += ["-f", "ffmetadata", "-i", str(meta_file)]

        meta_idx = 2 if has_cover else 1
        cmd += ["-map", "0:a:0"]
        if has_cover:
            cmd += ["-map", "1:v:0"]
        cmd += [
            "-map_metadata", str(meta_idx),
            "-map_chapters", str(meta_idx),
        ]

        # Audio codec: copy or re-encode
        if audio_quality:
            cmd += ["-c:a", audio_codec, "-b:a", audio_quality]
        else:
            cmd += ["-c:a", "copy"]

        if has_cover:
            cmd += ["-c:v", "mjpeg", "-disposition:v:0", "attached_pic"]
        cmd.append(str(output))

        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Final build failed:\n{r.stderr[-3000:]}")

        _prog("Done!")
