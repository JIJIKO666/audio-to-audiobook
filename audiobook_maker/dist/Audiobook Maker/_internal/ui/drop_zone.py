from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from i18n import tr, _tr_loaded


class DropZone(QFrame):
    folder_dropped = pyqtSignal(Path)

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
        # Right margin 38 = 18 (visual padding) + 20 (compensates for main layout's 0 right margin)
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

    def set_loaded(self, name: str, n_books: int, n_tracks: int):
        self._loaded_name = name
        self._loaded_n_books = n_books
        self._loaded_n_tracks = n_tracks
        self._icon.setText("📂")
        self._line1.setText(name)
        self._line2.setText(_tr_loaded(n_books, n_tracks))
        self._set_state("loaded")

    def retheme(self):
        self._set_state("loaded" if self._loaded_name is not None else "idle")

    def retranslate_ui(self):
        if self._loaded_name is not None:
            self._line2.setText(_tr_loaded(self._loaded_n_books, self._loaded_n_tracks))
        else:
            self._line1.setText(tr("drag_hint"))
            self._line2.setText(tr("drop_sub"))

    def mousePressEvent(self, _event):
        start = self._dir_hint() if self._dir_hint else ""
        folder = QFileDialog.getExistingDirectory(self, "Select audiobook folder", start)
        if folder:
            self.folder_dropped.emit(Path(folder))

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).is_dir():
            event.acceptProposedAction()
            self._set_state("hover")

    def dragLeaveEvent(self, _event):
        self.retheme()

    def dropEvent(self, event: QDropEvent):
        self.retheme()
        urls = event.mimeData().urls()
        if urls:
            folder = Path(urls[0].toLocalFile())
            if folder.is_dir():
                event.acceptProposedAction()
                self.folder_dropped.emit(folder)
