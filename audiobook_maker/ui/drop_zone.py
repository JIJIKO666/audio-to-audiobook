from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from i18n import tr, _tr_loaded


class DropZone(QFrame):
    folders_dropped = pyqtSignal(list)  # list[Path]

    def __init__(self):
        super().__init__()
        self._loaded_name: str | None = None
        self._loaded_n_books: int = 0
        self._loaded_n_tracks: int = 0
        self._dir_hint: "callable | None" = None
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(70)
        self._set_state("idle")

        row = QHBoxLayout(self)
        row.setContentsMargins(20, 10, 30, 10)
        row.setSpacing(16)

        self._icon = QLabel("📁")
        self._icon.setObjectName("icon")
        row.addWidget(self._icon)

        col = QVBoxLayout()
        col.setSpacing(0)
        self._line1 = QLabel(tr("drag_hint"))
        self._line1.setObjectName("dom")
        self._line2 = QLabel(tr("drop_sub"))
        self._line2.setObjectName("sub")
        col.addWidget(self._line1)
        col.addWidget(self._line2)
        row.addLayout(col)
        row.addStretch()

    def _set_state(self, state: str):
        self.setProperty("dzState", state)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_loaded(self, first_name: str, n_books: int, n_tracks: int, extra: int = 0):
        self._loaded_name = first_name
        self._loaded_n_books = n_books
        self._loaded_n_tracks = n_tracks
        self._icon.setText("📂")
        title = f"{first_name}  etc." if extra > 0 else first_name
        self._line1.setText(title)
        self._line2.setText(_tr_loaded(n_books, n_tracks))
        self._set_state("loaded")

    def update_counts(self, n_books: int, n_tracks: int):
        self._loaded_n_books = n_books
        self._loaded_n_tracks = n_tracks
        self._line2.setText(_tr_loaded(n_books, n_tracks))

    def reset(self):
        self._loaded_name = None
        self._loaded_n_books = 0
        self._loaded_n_tracks = 0
        self._icon.setText("📁")
        self._line1.setText(tr("drag_hint"))
        self._line2.setText(tr("drop_sub"))
        self._set_state("idle")

    def retheme(self):
        self._set_state("loaded" if self._loaded_name is not None else "idle")

    def retranslate_ui(self):
        if self._loaded_name is not None:
            self._line2.setText(_tr_loaded(self._loaded_n_books, self._loaded_n_tracks))
        else:
            self._line1.setText(tr("drag_hint"))
            self._line2.setText(tr("drop_sub"))

    def mousePressEvent(self, _event):
        import subprocess
        script = (
            'set folderList to choose folder with multiple selections allowed\n'
            'set out to ""\n'
            'repeat with f in folderList\n'
            '    set out to out & POSIX path of f & "\\n"\n'
            'end repeat\n'
            'out'
        )
        result = subprocess.run(['osascript', '-e', script],
                                capture_output=True, text=True)
        if result.returncode == 0:
            folders = [Path(p) for p in result.stdout.strip().splitlines()
                       if p.strip() and Path(p.strip()).is_dir()]
            if folders:
                self.folders_dropped.emit(folders)

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls()
        if any(Path(u.toLocalFile()).is_dir() for u in urls):
            event.acceptProposedAction()
            self._set_state("hover")

    def dragLeaveEvent(self, _event):
        self.retheme()

    def dropEvent(self, event: QDropEvent):
        self.retheme()
        urls = event.mimeData().urls()
        folders = [Path(u.toLocalFile()) for u in urls if Path(u.toLocalFile()).is_dir()]
        if folders:
            event.acceptProposedAction()
            self.folders_dropped.emit(folders)
