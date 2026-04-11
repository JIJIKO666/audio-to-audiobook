from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
)

import theme
from i18n import tr
from utils import _natural_key, fmt_dur, fmt_size
from ui.widgets import _PlainHeaderView, _NoMenuDelegate


class TrackTable(QTableWidget):
    # Columns: # | Chapter Title | Format | Size | Duration
    tracks_changed = pyqtSignal()

    _COL_NUM   = 0
    _COL_TITLE = 1
    _COL_FMT   = 2
    _COL_SIZE  = 3
    _COL_DUR   = 4

    def __init__(self, parent=None):
        super().__init__(0, 5, parent)
        self.setHorizontalHeader(_PlainHeaderView(Qt.Orientation.Horizontal, self))
        self._update_headers()
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)

        hh = self.horizontalHeader()
        hh.setSectionResizeMode(self._COL_NUM,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self._COL_TITLE, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self._COL_FMT,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self._COL_SIZE,  QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self._COL_DUR,   QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)

        self._tracks: list[dict] = []
        self._busy = False
        self._undo_stack: list[list[dict]] = []
        self._redo_stack: list[list[dict]] = []
        self._sort_col: int | None = None
        self._sort_asc: bool = True
        self.itemChanged.connect(self._title_edited)
        self.setItemDelegateForColumn(TrackTable._COL_TITLE, _NoMenuDelegate(self))

        hh = self.horizontalHeader()
        hh.setSectionsClickable(True)
        hh.setSortIndicatorShown(True)
        hh.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        hh.sectionClicked.connect(self._header_clicked)

    def _update_headers(self):
        self.setHorizontalHeaderLabels([
            tr("col_num"), tr("col_title"), tr("col_fmt"), tr("col_size"), tr("col_dur")
        ])

    def retranslate_ui(self):
        self._update_headers()

    @property
    def tracks(self) -> list[dict]:
        return list(self._tracks)

    def load(self, tracks: list[dict]):
        self._tracks = list(tracks)
        self._rebuild()

    def update_duration(self, row: int, dur: float):
        if 0 <= row < len(self._tracks):
            self._tracks[row]["duration"] = dur
            item = self.item(row, self._COL_DUR)
            if item:
                self._busy = True
                item.setText(fmt_dur(dur))
                self._busy = False

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    _last_modified: "TrackTable | None" = None
    _last_push_time: float = 0.0

    def _snapshot(self) -> list[dict]:
        return [dict(t) for t in self._tracks]

    def _push_undo(self):
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        TrackTable._last_modified = self
        TrackTable._last_push_time = time.monotonic()

    def undo(self):
        if self._undo_stack:
            self._redo_stack.append(self._snapshot())
            self._tracks = self._undo_stack.pop()
            self._rebuild()

    def redo(self):
        if self._redo_stack:
            self._undo_stack.append(self._snapshot())
            self._tracks = self._redo_stack.pop()
            self._rebuild()

    @property
    def can_undo(self) -> bool: return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool: return bool(self._redo_stack)

    def take_last_undo_snapshot(self) -> "list[dict] | None":
        """Pop and return the last undo snapshot, resetting push time if stack empties."""
        if not self._undo_stack:
            return None
        snap = self._undo_stack.pop()
        self._redo_stack.clear()
        if not self._undo_stack:
            TrackTable._last_push_time = 0.0
        return snap

    def remove_selected(self):
        rows = sorted({i.row() for i in self.selectedIndexes()}, reverse=True)
        if not rows:
            return
        self._push_undo()
        for r in rows:
            self._tracks.pop(r)
        self._rebuild()

    def move_to_first(self):
        sel = sorted({i.row() for i in self.selectedIndexes()})
        if not sel or sel[0] == 0:
            return
        self._push_undo()
        moving = [self._tracks[r] for r in sel]
        staying = [t for i, t in enumerate(self._tracks) if i not in set(sel)]
        self._tracks = moving + staying
        self._rebuild()
        self.clearSelection()
        cols = self.columnCount() - 1
        for i in range(len(moving)):
            self.setRangeSelected(QTableWidgetSelectionRange(i, 0, i, cols), True)

    def move_to_last(self):
        sel = sorted({i.row() for i in self.selectedIndexes()})
        if not sel or sel[-1] == len(self._tracks) - 1:
            return
        self._push_undo()
        moving = [self._tracks[r] for r in sel]
        staying = [t for i, t in enumerate(self._tracks) if i not in set(sel)]
        self._tracks = staying + moving
        self._rebuild()
        self.clearSelection()
        base = len(staying)
        cols = self.columnCount() - 1
        for i in range(len(moving)):
            self.setRangeSelected(QTableWidgetSelectionRange(base + i, 0, base + i, cols), True)

    def _header_clicked(self, col: int):
        if col == self._COL_NUM:
            # Reset to natural filename order
            self._push_undo()
            self._tracks.sort(key=lambda t: _natural_key(Path(t["path"]).name))
            self._sort_col = None
            self._sort_asc = True
            self.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        else:
            if self._sort_col == col:
                self._sort_asc = not self._sort_asc
            else:
                self._sort_col = col
                self._sort_asc = True
            key_fn = {
                self._COL_TITLE: lambda t: _natural_key(t["title"]),
                self._COL_FMT:   lambda t: t.get("format", ""),
                self._COL_SIZE:  lambda t: t.get("size") or 0,
                self._COL_DUR:   lambda t: t.get("duration") or 0.0,
            }.get(col, lambda _: "")
            self._push_undo()
            self._tracks.sort(key=key_fn, reverse=not self._sort_asc)
            order = Qt.SortOrder.AscendingOrder if self._sort_asc else Qt.SortOrder.DescendingOrder
            self.horizontalHeader().setSortIndicator(col, order)
        self._rebuild()

    def _rebuild(self):
        _ro = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        self._busy = True
        self.setRowCount(0)
        for i, t in enumerate(self._tracks):
            self.insertRow(i)
            self.setRowHeight(i, 30)

            num = QTableWidgetItem(str(i + 1))
            num.setFlags(_ro)
            num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setForeground(QColor(theme.C_SECONDARY))
            self.setItem(i, self._COL_NUM, num)

            self.setItem(i, self._COL_TITLE, QTableWidgetItem(t["title"]))

            fmt_item = QTableWidgetItem(t.get("format", ""))
            fmt_item.setFlags(_ro)
            fmt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            fmt_item.setForeground(QColor(theme.C_SECONDARY))
            self.setItem(i, self._COL_FMT, fmt_item)

            sz = t.get("size")
            sz_item = QTableWidgetItem(fmt_size(sz) if sz else "—")
            sz_item.setFlags(_ro)
            sz_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sz_item.setForeground(QColor(theme.C_SECONDARY))
            self.setItem(i, self._COL_SIZE, sz_item)

            dur = QTableWidgetItem(fmt_dur(t.get("duration")))
            dur.setFlags(_ro)
            dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            dur.setForeground(QColor(theme.C_SECONDARY))
            self.setItem(i, self._COL_DUR, dur)
        self._busy = False
        self.tracks_changed.emit()

    def _title_edited(self, item: QTableWidgetItem):
        if self._busy or item.column() != self._COL_TITLE:
            return
        row = item.row()
        if 0 <= row < len(self._tracks):
            self._tracks[row]["title"] = item.text()

    def dropEvent(self, event: QDropEvent):
        if event.source() is not self:
            event.ignore()
            return
        target = self.indexAt(event.position().toPoint()).row()
        if target < 0:
            target = len(self._tracks)
        sel = sorted({i.row() for i in self.selectedIndexes()})
        if not sel:
            event.ignore()
            return
        self._push_undo()
        moving   = [self._tracks[r] for r in sel]
        staying  = [t for i, t in enumerate(self._tracks) if i not in set(sel)]
        above    = sum(1 for r in sel if r < target)
        insert_at = max(0, min(target - above, len(staying)))
        for i, t in enumerate(moving):
            staying.insert(insert_at + i, t)
        self._tracks = staying
        self._rebuild()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.remove_selected()
        else:
            super().keyPressEvent(event)

    def sizeHint(self):
        hint = super().sizeHint()
        rows = self.rowCount()
        h = self.horizontalHeader().height() + rows * 30 + 4
        hint.setHeight(min(h, 6*30))
        return hint
