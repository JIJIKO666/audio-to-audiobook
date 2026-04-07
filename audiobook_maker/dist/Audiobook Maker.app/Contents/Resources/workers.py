from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from converter import build_audiobook, get_duration


class DurationWorker(QThread):
    result = pyqtSignal(int, float)
    done   = pyqtSignal()

    def __init__(self, files: list[Path]):
        super().__init__()
        self.files = files
        self._stop = False

    def stop(self): self._stop = True

    def run(self):
        for i, fp in enumerate(self.files):
            if self._stop:
                break
            try:
                self.result.emit(i, get_duration(fp))
            except Exception:
                pass
        self.done.emit()


class ConvertWorker(QThread):
    """Processes a list of audiobook jobs sequentially."""
    progress    = pyqtSignal(str)
    book_start  = pyqtSignal(int, str)
    book_done   = pyqtSignal(int)
    book_error  = pyqtSignal(int, str)
    all_done    = pyqtSignal(list)

    def __init__(self, jobs: list[dict]):
        super().__init__()
        self.jobs = jobs

    def run(self):
        outputs = []
        for i, job in enumerate(self.jobs):
            album = job.get("album", "")
            title = job.get("title", "")
            label = f"{album} - {title}" if album and title and album != title else album or title
            self.book_start.emit(i, label)
            try:
                build_audiobook(
                    job["files"], job["titles"], job["output"],
                    job["title"], job["author"], job["album"], job["cover"],
                    audio_codec=job.get("audio_codec", "aac"),
                    audio_quality=job.get("audio_quality"),
                    cover_max_w=job.get("cover_max_w", 0),
                    cover_max_h=job.get("cover_max_h", 0),
                    cover_max_kb=job.get("cover_max_kb", 0),
                    progress_cb=self.progress.emit,
                )
                outputs.append(str(job["output"]))
                self.book_done.emit(i)
            except Exception as exc:
                self.book_error.emit(i, str(exc))
        self.all_done.emit(outputs)
