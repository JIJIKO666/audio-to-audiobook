from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from i18n import tr


class _ProgressDialog(QDialog):
    canceled = pyqtSignal()

    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setModal(True)
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 22)
        root.setSpacing(0)

        self._lbl_title = QLabel("")
        self._lbl_title.setWordWrap(True)
        root.addWidget(self._lbl_title)

        root.addSpacing(6)

        self._lbl_detail = QLabel("")
        self._lbl_detail.setObjectName("sub")
        self._lbl_detail.setWordWrap(True)
        root.addWidget(self._lbl_detail)

        root.addSpacing(16)

        self._bar = QProgressBar()
        self._bar.setRange(0, total)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        root.addWidget(self._bar)

        root.addSpacing(4)

        self._lbl_count = QLabel("")
        self._lbl_count.setObjectName("sub")
        self._lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(self._lbl_count)

        root.addSpacing(18)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton(tr("cancel"))
        self._btn_cancel.clicked.connect(self.canceled.emit)
        btn_row.addWidget(self._btn_cancel)
        root.addLayout(btn_row)

        self._total = total

    def setTitle(self, text: str):
        self._lbl_title.setText(text)

    def setDetail(self, text: str):
        self._lbl_detail.setText(text)

    def setValue(self, v: int):
        self._bar.setValue(v)
        self._lbl_count.setText(f"{v} / {self._total}")

    def maximum(self) -> int:
        return self._total
