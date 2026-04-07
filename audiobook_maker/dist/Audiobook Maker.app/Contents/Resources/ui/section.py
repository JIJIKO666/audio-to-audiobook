from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from i18n import tr
from utils import clean_title
from scanner import get_direct_audio, find_cover, parse_meta
from workers import DurationWorker
from ui.widgets import _LineEdit, _separator
from ui.track_table import TrackTable
from ui.cover_widget import CoverWidget


class AudiobookSection(QWidget):
    """One collapsible section per audiobook folder."""
    delete_requested = pyqtSignal(object)

    def __init__(self, folder: Path, root: Path):
        super().__init__()
        self._folder = folder
        self._root   = root
        self._dur_worker: DurationWorker | None = None
        self._build_ui()
        self._load()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 20)
        lay.setSpacing(10)

        try:
            display = str(self._folder.relative_to(self._root.parent))
        except ValueError:
            display = str(self._folder)

        self._path_field = _LineEdit(display)
        self._path_field.setObjectName("pathField")
        self._path_field.setReadOnly(True)
        self._path_field.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._path_field.setToolTip(display)

        self._btn_del = QPushButton(tr("delete_book"))
        self._btn_del.setObjectName("danger")
        self._btn_del.clicked.connect(lambda: self.delete_requested.emit(self))

        # Metadata + cover row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(15)
        meta_row.setContentsMargins(0, 5, 0, 0)

        self.cover = CoverWidget(size=150)
        self.cover.setToolTip(tr("tt_cover_thumb"))
        meta_row.addWidget(self.cover, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.edit_album  = _LineEdit(); self.edit_album.setPlaceholderText(tr("album"))
        self.edit_album.setToolTip(tr("tt_album"))
        self.edit_title  = _LineEdit(); self.edit_title.setPlaceholderText(tr("title_ph"))
        self.edit_title.setToolTip(tr("tt_title"))
        self.edit_author = _LineEdit(); self.edit_author.setPlaceholderText(tr("artist"))
        self.edit_author.setToolTip(tr("tt_artist"))

        self._lbl_album  = QLabel(tr("album"))
        self._lbl_title  = QLabel(tr("title_field"))
        self._lbl_artist = QLabel(tr("artist"))

        fields_col = QVBoxLayout()
        fields_col.setSpacing(7)

        # Path field + delete button above the metadata fields
        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_row.addWidget(self._path_field, stretch=1)
        path_row.addWidget(self._btn_del)
        fields_col.addLayout(path_row)

        for lbl_w, widget in (
            (self._lbl_album,  self.edit_album),
            (self._lbl_title,  self.edit_title),
            (self._lbl_artist, self.edit_author),
        ):
            lbl_w.setFixedWidth(50)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row = QHBoxLayout()
            row.setSpacing(10)
            row.addWidget(lbl_w)
            row.addWidget(widget)
            fields_col.addLayout(row)

        meta_row.addLayout(fields_col, stretch=1)
        lay.addLayout(meta_row)

        # Track table — no internal scrollbar; height is managed by expand/collapse
        self.table = TrackTable()
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._COLLAPSED_ROWS = 5
        lay.addWidget(self.table)

        # Order / remove buttons row
        rm_row = QHBoxLayout()
        rm_row.setContentsMargins(0, 0, 0, 0)
        rm_row.setSpacing(6)
        self._expanded = False
        self._btn_expand = QPushButton(tr("expand"))
        self._btn_expand.clicked.connect(self._toggle_expand)
        self._btn_first = QPushButton(tr("move_first"))
        self._btn_first.setObjectName("revise")
        self._btn_first.clicked.connect(self._move_first)
        self._btn_last = QPushButton(tr("move_last"))
        self._btn_last.setObjectName("revise")
        self._btn_last.clicked.connect(self._move_last)
        rm_row.addWidget(self._btn_expand)
        rm_row.addWidget(self._btn_first)
        rm_row.addWidget(self._btn_last)
        rm_row.addStretch()
        self._btn_rm = QPushButton(tr("remove_aud"))
        self._btn_rm.setObjectName("danger")
        self._btn_rm.clicked.connect(self._remove_selected)
        rm_row.addWidget(self._btn_rm)
        lay.addLayout(rm_row)

        # Connect signals
        self.table.tracks_changed.connect(self._after_table_change)
        self.table.selectionModel().selectionChanged.connect(self._update_move_buttons)
        self._btn_first.setEnabled(False)
        self._btn_last.setEnabled(False)

    def _remove_selected(self):
        if not self.table.selectedIndexes():
            QMessageBox.information(self, tr("no_sel_title"), tr("no_sel_msg"))
            return
        self.table.remove_selected()

    def _move_first(self):
        self.table.move_to_first()
        self._update_move_buttons()

    def _move_last(self):
        self.table.move_to_last()
        self._update_move_buttons()

    def _update_move_buttons(self):
        sel = sorted({i.row() for i in self.table.selectedIndexes()})
        n = self.table.rowCount()
        if not sel:
            self._btn_first.setEnabled(False)
            self._btn_last.setEnabled(False)
            return
        k = len(sel)
        already_first = sel == list(range(k))
        already_last  = sel == list(range(n - k, n))
        self._btn_first.setEnabled(not already_first)
        self._btn_last.setEnabled(not already_last)

    def _after_table_change(self):
        n = self.table.rowCount()
        if n == 0:
            self.delete_requested.emit(self)
            return
        needs_expand = n > self._COLLAPSED_ROWS
        if not needs_expand and self._expanded:
            self._expanded = False
        self._btn_expand.setVisible(needs_expand)
        self._btn_expand.setText(tr("collapse") if self._expanded else tr("expand"))
        self._apply_table_height()
        self._update_move_buttons()

    def _row_height(self) -> int:
        if self.table.rowCount() > 0:
            return self.table.rowHeight(0)
        return self.table.verticalHeader().defaultSectionSize()

    def _header_height(self) -> int:
        return self.table.horizontalHeader().height()

    def _collapsed_height(self) -> int:
        rows = min(self.table.rowCount(), self._COLLAPSED_ROWS)
        return self._header_height() + self._row_height() * rows + 2

    def _full_height(self) -> int:
        rows_h = sum(self.table.rowHeight(i) for i in range(self.table.rowCount()))
        return self._header_height() + rows_h + 2

    def _apply_table_height(self):
        h = self._full_height() if self._expanded else self._collapsed_height()
        self.table.setFixedHeight(h)
        self.updateGeometry()
        win = self.window()
        if hasattr(win, "_fit_window"):
            win._fit_window()

    def _toggle_expand(self):
        self._expanded = not self._expanded
        self._apply_table_height()
        self._btn_expand.setText(tr("collapse") if self._expanded else tr("expand"))
        self._update_move_buttons()

    def retranslate_ui(self):
        self._btn_del.setText(tr("delete_book"))
        self._btn_rm.setText(tr("remove_aud"))
        self._btn_expand.setText(tr("collapse") if self._expanded else tr("expand"))
        self._btn_first.setText(tr("move_first"))
        self._btn_last.setText(tr("move_last"))
        self._lbl_album.setText(tr("album"))
        self._lbl_title.setText(tr("title_field"))
        self._lbl_artist.setText(tr("artist"))
        self.edit_album.setPlaceholderText(tr("album"))
        self.edit_title.setPlaceholderText(tr("title_ph"))
        self.edit_author.setPlaceholderText(tr("artist"))
        self.edit_album.setToolTip(tr("tt_album"))
        self.edit_title.setToolTip(tr("tt_title"))
        self.edit_author.setToolTip(tr("tt_artist"))
        self.cover.setToolTip(tr("tt_cover_thumb"))
        self.cover.retranslate_ui()
        self.table.retranslate_ui()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load(self):
        files = get_direct_audio(self._folder)
        if not files:
            return

        tracks = [
            {
                "path":     fp,
                "title":    clean_title(fp),
                "duration": None,
                "format":   fp.suffix.upper().lstrip("."),
                "size":     fp.stat().st_size,
            }
            for fp in files
        ]
        self._expanded = False
        self.table.load(tracks)  # emits tracks_changed → _after_table_change

        self.cover.set_cover(find_cover(self._folder, self._root))

        meta = parse_meta(self._folder, self._root)
        self.edit_album.setText(meta["album"] or self._path_field.text())
        self.edit_title.setText(meta["title"])
        self.edit_author.setText(meta["author"])

        self._dur_worker = DurationWorker(files)
        self._dur_worker.result.connect(self.table.update_duration)
        self._dur_worker.start()

    def stop_worker(self):
        if self._dur_worker and self._dur_worker.isRunning():
            self._dur_worker.stop()
            self._dur_worker.wait()

    # ── Job export ────────────────────────────────────────────────────────────

    def job(self, out_dir: Path, *,
            audio_codec: str = "aac",
            audio_quality: str | None = None,
            cover_max_w: int = 0,
            cover_max_h: int = 0,
            cover_max_kb: int = 0) -> dict | None:
        tracks = self.table.tracks
        if not tracks:
            return None
        album  = self.edit_album.text().strip()
        title  = self.edit_title.text().strip() or album or "Audiobook"
        author = self.edit_author.text().strip()

        # Filename: "album_title" when they differ, "album" when they're the same
        if album and title and album != title:
            stem = f"{album}_{title}"
        else:
            stem = album or title or "Audiobook"

        return {
            "files":         [t["path"]  for t in tracks],
            "titles":        [t["title"] for t in tracks],
            "output":        out_dir / f"{stem}.m4b",
            "title":         title,
            "author":        author,
            "album":         album or title,
            "cover":         self.cover.cover_path,
            "audio_codec":   audio_codec,
            "audio_quality": audio_quality,
            "cover_max_w":   cover_max_w,
            "cover_max_h":   cover_max_h,
            "cover_max_kb":  cover_max_kb,
        }

    @property
    def track_count(self) -> int:
        return len(self.table.tracks)


class _SectionScroll(QScrollArea):
    def sizeHint(self) -> QSize:
        w = self.widget()
        if not w:
            return QSize(0, 0)
        w.adjustSize()
        content_h = w.sizeHint().height()
        screen_h  = QApplication.primaryScreen().availableGeometry().height()
        return QSize(super().sizeHint().width(), min(content_h, int(screen_h * 0.7)))
