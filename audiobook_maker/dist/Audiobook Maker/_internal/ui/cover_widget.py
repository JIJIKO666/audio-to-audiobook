from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from PyQt6.QtCore import QBuffer, QByteArray, QPoint, QRect, QRectF, QSettings, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDropEvent, QPainter, QPainterPath, QPen, QPixmap, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)

import theme
from i18n import tr
from ui.widgets import _LineEdit, _EditorSpinBox, _separator


class _CropWidget(QLabel):
    """Image display with drag-to-select crop region.

    Supports three interaction modes after a selection exists:
      - Draw   : drag outside selection to create a new one
      - Move   : drag inside selection to reposition it
      - Resize : drag a corner handle to resize
    """

    _IDLE   = 0
    _DRAW   = 1
    _MOVE   = 2
    _RESIZE = 3
    _HIT    = 10   # px radius for corner hit test

    def __init__(self, pixmap: QPixmap, max_side: int, parent=None):
        super().__init__(parent)
        self._src: QPixmap = pixmap
        self._max_side: int = max_side
        self._scale: float = 1.0
        self._sel: QRect | None = None
        self._mode = self._IDLE
        self._drag_origin = QPoint()
        self._sel_at_drag = QRect()
        self._corner: str | None = None   # 'tl' 'tr' 'bl' 'br'
        self._ratio: "tuple[int,int] | None" = None  # None=free, (num,den) e.g. (1,1) (3,4) (5,7)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._refresh_display()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_pixmap(self, pixmap: QPixmap):
        self._src = pixmap
        self._sel = None
        self._mode = self._IDLE
        self._refresh_display()

    @staticmethod
    def _fit_ratio(w: int, h: int, num: int, den: int) -> QRect:
        """Largest exact (num:den) rect centered in w×h using integer arithmetic."""
        k = min(w // num, h // den)
        rw, rh = k * num, k * den
        return QRect((w - rw) // 2, (h - rh) // 2, rw, rh)

    def set_ratio(self, ratio: "tuple[int,int] | None"):
        """Set aspect-ratio constraint: None=free, or (num,den) e.g. (3,4)."""
        self._ratio = ratio
        if ratio is not None:
            # Derive display selection from source crop rect so they match exactly
            src = self._fit_ratio(self._src.width(), self._src.height(), *ratio)
            s = self._scale
            ox, oy = self._img_rect.x(), self._img_rect.y()
            self._sel = QRect(
                round(src.x() * s) + ox, round(src.y() * s) + oy,
                round(src.width() * s), round(src.height() * s),
            )
        else:
            self._sel = None
        self._mode = self._IDLE
        self.update()

    def crop_rect_in_source(self) -> QRect | None:
        if not self._sel or self._sel.width() < 2:
            return None
        s = self._scale
        sel = self._sel
        img = self._img_rect
        sel_x = sel.x() - img.x()
        sel_y = sel.y() - img.y()
        x = 0 if sel_x <= 0 else round(sel_x / s)
        y = 0 if sel_y <= 0 else round(sel_y / s)
        w = (self._src.width() - x) if (sel_x + sel.width() >= img.width()) else round(sel.width() / s)
        h = (self._src.height() - y) if (sel_y + sel.height() >= img.height()) else round(sel.height() / s)
        # Snap to exact ratio to correct any floating-point drift
        if self._ratio is not None:
            num, den = self._ratio
            k = min(w // num, h // den)
            w, h = k * num, k * den
        return QRect(x, y, w, h)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def sizeHint(self):
        return QSize(self._max_side, self._max_side)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        old_scale = self._scale
        old_offset = getattr(self, '_img_rect', QRect()).topLeft()
        old_sel = QRect(self._sel) if self._sel else None
        self._refresh_display()
        if old_sel and old_sel.width() > 1 and old_scale > 0:
            if self._ratio is not None:
                src = self._fit_ratio(self._src.width(), self._src.height(), *self._ratio)
                s = self._scale
                ox, oy = self._img_rect.x(), self._img_rect.y()
                self._sel = QRect(
                    round(src.x() * s) + ox, round(src.y() * s) + oy,
                    round(src.width() * s), round(src.height() * s),
                )
            else:
                ox_old, oy_old = old_offset.x(), old_offset.y()
                ox_new, oy_new = self._img_rect.x(), self._img_rect.y()
                src_x = (old_sel.x() - ox_old) / old_scale
                src_y = (old_sel.y() - oy_old) / old_scale
                src_w = old_sel.width() / old_scale
                src_h = old_sel.height() / old_scale
                self._sel = self._clamp(QRect(
                    round(src_x * self._scale) + ox_new,
                    round(src_y * self._scale) + oy_new,
                    round(src_w * self._scale),
                    round(src_h * self._scale),
                ))

    def _refresh_display(self):
        dpr = QApplication.primaryScreen().devicePixelRatio()
        w = self.width() if self.width() > 0 else self._max_side
        h = self.height() if self.height() > 0 else self._max_side
        disp = self._src.scaled(
            int(w * dpr), int(h * dpr),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        disp.setDevicePixelRatio(dpr)
        img_w = int(disp.width() / dpr)
        img_h = int(disp.height() / dpr)
        self._scale = img_w / self._src.width()
        self._disp = disp
        ox = (w - img_w) // 2
        oy = (h - img_h) // 2
        self._img_rect = QRect(ox, oy, img_w, img_h)
        self.update()

    def _corner_at(self, pos: QPoint) -> str | None:
        if not self._sel:
            return None
        r = self._HIT
        pts = {
            'tl': QPoint(self._sel.left(),  self._sel.top()),
            'tr': QPoint(self._sel.right(), self._sel.top()),
            'bl': QPoint(self._sel.left(),  self._sel.bottom()),
            'br': QPoint(self._sel.right(), self._sel.bottom()),
        }
        for name, pt in pts.items():
            if (pos.x()-pt.x())**2 + (pos.y()-pt.y())**2 <= r*r:
                return name
        return None

    @staticmethod
    def _cursor_for(corner: str | None, inside: bool):
        if corner in ('tl', 'br'):
            return Qt.CursorShape.SizeFDiagCursor
        if corner in ('tr', 'bl'):
            return Qt.CursorShape.SizeBDiagCursor
        if inside:
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.CrossCursor

    def _clamp(self, r: QRect) -> QRect:
        """Keep rect inside image bounds."""
        img = self._img_rect
        x = max(img.left(), min(r.x(), img.right() - r.width() + 1))
        y = max(img.top(), min(r.y(), img.bottom() - r.height() + 1))
        return QRect(x, y, r.width(), r.height())

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        corner = self._corner_at(pos)
        if corner:
            self._mode = self._RESIZE
            self._corner = corner
        elif self._sel and self._sel.contains(pos):
            self._mode = self._MOVE
        else:
            self._mode = self._DRAW
            self._sel = None
            img = self._img_rect
            pos = QPoint(
                max(img.left(), min(pos.x(), img.right())),
                max(img.top(), min(pos.y(), img.bottom())),
            )
        self._drag_origin = pos
        self._sel_at_drag = QRect(self._sel) if self._sel else QRect()
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        if self._mode == self._IDLE:
            corner = self._corner_at(pos)
            inside = bool(self._sel and self._sel.contains(pos))
            self.setCursor(self._cursor_for(corner, inside))
            return

        dx = pos.x() - self._drag_origin.x()
        dy = pos.y() - self._drag_origin.y()

        if self._mode == self._DRAW:
            img = self._img_rect
            ex = max(img.left(), min(pos.x(), img.right()))
            ey = max(img.top(), min(pos.y(), img.bottom()))
            end = QPoint(ex, ey)
            if self._ratio is not None:
                num, den = self._ratio
                k = min(abs(dx) // num, abs(dy) // den)
                rw, rh = k * num, k * den
                end = QPoint(
                    self._drag_origin.x() + (rw if dx >= 0 else -rw),
                    self._drag_origin.y() + (rh if dy >= 0 else -rh),
                )
            self._sel = QRect(self._drag_origin, end).normalized()

        elif self._mode == self._MOVE:
            r = QRect(self._sel_at_drag)
            r.translate(dx, dy)
            self._sel = self._clamp(r)

        elif self._mode == self._RESIZE:
            r = QRect(self._sel_at_drag)
            c = self._corner
            img = self._img_rect
            if 't' in c:
                r.setTop(max(img.top(), min(r.top() + dy, r.bottom() - 1)))
            if 'b' in c:
                r.setBottom(max(r.top() + 1, min(r.bottom() + dy, img.bottom())))
            if 'l' in c:
                r.setLeft(max(img.left(), min(r.left() + dx, r.right() - 1)))
            if 'r' in c:
                r.setRight(max(r.left() + 1, min(r.right() + dx, img.right())))
            if self._ratio is not None:
                # Constrain to exact ratio, keeping the fixed corner anchored
                num, den = self._ratio
                k = min(r.width() // num, r.height() // den)
                w, h = k * num, k * den
                if 'l' in c:
                    r.setLeft(r.right() - w)
                else:
                    r.setRight(r.left() + w)
                if 't' in c:
                    r.setTop(r.bottom() - h)
                else:
                    r.setBottom(r.top() + h)
            self._sel = r

        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mode = self._IDLE
            pos = event.position().toPoint()
            corner = self._corner_at(pos)
            inside = bool(self._sel and self._sel.contains(pos))
            self.setCursor(self._cursor_for(corner, inside))

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.C_BG))
        if hasattr(self, '_disp'):
            p.drawPixmap(self._img_rect.topLeft(), self._disp)
        if not (self._sel and self._sel.width() > 1):
            p.end()
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim only the image area outside selection
        outer = QPainterPath()
        outer.addRect(QRectF(self._img_rect))
        inner = QPainterPath()
        inner.addRect(float(self._sel.x()), float(self._sel.y()),
                      float(self._sel.width()), float(self._sel.height()))
        p.fillPath(outer.subtracted(inner), QColor(0, 0, 0, 80))

        # Border — inset 0.5 px so the 1px stroke stays fully inside widget bounds
        p.setPen(QPen(QColor(theme.C_ACCENT), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(
            self._sel.x() + 0.5, self._sel.y() + 0.5,
            self._sel.width() - 1, self._sel.height() - 1,
        ))

        # Corner handles — L-shapes drawn inside the selection, always fully visible
        L = 8
        pen = QPen(QColor(theme.C_ACCENT), 4)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        x1 = self._sel.left()  + 2
        y1 = self._sel.top()   + 2
        x2 = self._sel.right() - 1
        y2 = self._sel.bottom()- 1
        for cx, cy, hx, vy in (
            (x1, y1,  L,  L),   # top-left     → right, down
            (x2, y1, -L,  L),   # top-right    → left,  down
            (x1, y2,  L, -L),   # bottom-left  → right, up
            (x2, y2, -L, -L),   # bottom-right → left,  up
        ):
            p.drawLine(cx, cy, cx + hx, cy)
            p.drawLine(cx, cy, cx, cy + vy)
        p.end()


class CoverEditorDialog(QDialog):
    """Edit Cover window: In-memory cover editor: crop, resize, quality compression."""

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self._path = path
        self._pixmap = QPixmap(str(path))
        self._history: list[tuple[QPixmap, "QByteArray | None"]] = []
        self._future:  list[tuple[QPixmap, "QByteArray | None"]] = []
        self._compressed: "QByteArray | None" = None
        self._setWindowStyle()
        self._build_ui()
        self._refresh_info()
        screen = QApplication.primaryScreen().availableGeometry()
        init_h = min(self._CANVAS + 220, screen.height() - 80)
        self.resize(self._CANVAS + 32, init_h)
        self.setMinimumWidth(self._CANVAS)

    def _setWindowStyle(self):
        self.setWindowTitle(tr("edit_cover"))

    _CANVAS = 500  # preferred side length of the crop area in logical pixels

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(16, 14, 16, 14)

        # Pic Info bar — fixed height, name left (elides at start), stats right
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        info_row.setContentsMargins(0, 0, 0, 0)

        self._lbl_name = _LineEdit("")
        self._lbl_name.setObjectName("sub")
        self._lbl_name.setReadOnly(True)

        self._lbl_stats = _LineEdit("")
        self._lbl_stats.setObjectName("sub")
        self._lbl_stats.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_stats.setReadOnly(True)
        self._lbl_stats.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        info_row.addWidget(self._lbl_name, stretch=1)
        info_row.addWidget(self._lbl_stats)
        lay.addLayout(info_row)

        self._crop_w = _CropWidget(self._pixmap, self._CANVAS, self)
        self._crop_w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._crop_w.setMinimumSize(200, 200)
        lay.addWidget(self._crop_w, stretch=1)

        lay.addWidget(_separator())

        _s = QSettings("audiobook-maker", "AudiobookMaker")

        # ── Crop row ──────────────────────────────────────────────────────────
        crop_row = QHBoxLayout()
        crop_row.setSpacing(10)
        lbl_c = QLabel(tr("crop"))
        lbl_c.setFixedWidth(50)
        lbl_c.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._btn_free   = QPushButton(tr("crop_free"))
        self._btn_square = QPushButton("1:1")
        self._btn_ratio34  = QPushButton("3:4")
        self._btn_ratio34.setToolTip("0.75")
        # Mutable so swap can flip; index 0=free,1=1:1,2=3:4or4:3,3=custom
        _swapped = bool(int(_s.value("cover_editor/crop_swapped", 0)))
        _custom_raw = _s.value("cover_editor/crop_custom", "")
        _custom_ratio = None
        if _custom_raw:
            try:
                a, b = (int(x) for x in _custom_raw.split(":"))
                if a > 0 and b > 0:
                    _custom_ratio = (a, b)
            except (ValueError, AttributeError):
                pass
        self._ratios = [None, (1, 1),
                        (4, 3) if _swapped else (3, 4),
                        _custom_ratio]
        self._crop_grp = QButtonGroup(self)
        for i, btn in enumerate((self._btn_free, self._btn_square, self._btn_ratio34)):
            btn.setCheckable(True)
            btn.setObjectName("cropMode")
            self._crop_grp.addButton(btn, i)
        self._btn_free.setChecked(True)
        self._crop_grp.setExclusive(True)
        self._crop_grp.idClicked.connect(lambda i: self._crop_w.set_ratio(self._ratios[i]))

        # Custom ratio button (index 3) — hidden until set
        self._btn_custom = QPushButton("")
        self._btn_custom.setCheckable(True)
        self._btn_custom.setObjectName("cropModeCustom")
        self._crop_grp.addButton(self._btn_custom, 3)
        if _custom_ratio:
            self._btn_custom.setText(f"{_custom_ratio[0]}:{_custom_ratio[1]}")
            self._btn_custom.setVisible(True)
        else:
            self._btn_custom.setVisible(False)

        btn_add_ratio = QPushButton("+")
        btn_add_ratio.setObjectName("icon")
        btn_add_ratio.setToolTip("Add custom ratio")
        btn_add_ratio.clicked.connect(self._set_custom_crop)

        btn_swap_crop = QPushButton("⇄")
        btn_swap_crop.setObjectName("icon")
        btn_swap_crop.setToolTip("Swap W:H")
        btn_swap_crop.clicked.connect(self._swap_crop)

        btn_apply_crop = QPushButton(tr("apply_crop"))
        btn_apply_crop.setObjectName("revise")
        btn_apply_crop.clicked.connect(self._apply_crop)

        crop_row.addWidget(lbl_c)
        crop_row.addWidget(self._btn_free)
        crop_row.addWidget(self._btn_square)
        crop_row.addWidget(self._btn_ratio34)
        crop_row.addWidget(self._btn_custom)
        crop_row.addStretch()
        crop_row.addWidget(btn_add_ratio)
        crop_row.addWidget(btn_swap_crop)
        crop_row.addWidget(btn_apply_crop)
        lay.addLayout(crop_row)
        # Apply saved swap state to button label
        self._btn_ratio34.setText(f"{self._ratios[2][0]}:{self._ratios[2][1]}")

        # ── Resize row ────────────────────────────────────────────────────────
        resize_row = QHBoxLayout()
        resize_row.setSpacing(10)
        lbl_r = QLabel(tr("resize"))
        lbl_r.setFixedWidth(50)
        lbl_r.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._spin_w = _EditorSpinBox()
        self._spin_w.setFixedWidth(100)
        self._spin_w.setRange(1, 9999)
        self._spin_w.setValue(int(_s.value("cover_editor/resize_w", 600)))
        self._spin_w.setSuffix(" px")
        self._spin_w.setSingleStep(50)
        self._spin_h = _EditorSpinBox()
        self._spin_h.setFixedWidth(100)
        self._spin_h.setRange(1, 9999)
        self._spin_h.setValue(int(_s.value("cover_editor/resize_h", 600)))
        self._spin_h.setSuffix(" px")
        self._spin_h.setSingleStep(50)
        lbl_x = QLabel("×")
        lbl_x.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_apply_resize = QPushButton(tr("apply"))
        btn_apply_resize.setObjectName("revise")
        btn_apply_resize.clicked.connect(self._apply_resize)

        resize_row.addWidget(lbl_r)
        resize_row.addWidget(self._spin_w)
        resize_row.addWidget(lbl_x)
        resize_row.addWidget(self._spin_h)
        resize_row.addStretch()
        resize_row.addWidget(btn_apply_resize)
        lay.addLayout(resize_row)

        # ── Quality row ───────────────────────────────────────────────────────
        qual_row = QHBoxLayout()
        qual_row.setSpacing(10)
        lbl_q = QLabel(tr("qual_label"))
        lbl_q.setFixedWidth(50)
        lbl_q.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._spin_kb = _EditorSpinBox()
        self._spin_kb.setFixedWidth(100)
        self._spin_kb.setRange(1, 99999)
        self._spin_kb.setValue(int(_s.value("cover_editor/quality_kb", 200)))
        self._spin_kb.setSuffix(" KB")
        self._spin_kb.setSingleStep(50)

        btn_apply_qual = QPushButton(tr("apply"))
        btn_apply_qual.setObjectName("revise")
        btn_apply_qual.clicked.connect(self._apply_quality)

        qual_row.addWidget(lbl_q)
        qual_row.addWidget(self._spin_kb)
        qual_row.addStretch()
        qual_row.addWidget(btn_apply_qual)
        lay.addLayout(qual_row)

        lay.addWidget(_separator())

        # ── Bottom buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(tr("cancel"))
        btn_cancel.clicked.connect(self.reject)
        btn_save_to = QPushButton(tr("save_to"))
        btn_save_to.setAutoDefault(False)
        btn_save_to.clicked.connect(self._save_to)
        btn_save = QPushButton(tr("save"))
        btn_save.setObjectName("primary")
        btn_save.setAutoDefault(False)
        btn_cancel.setAutoDefault(False)
        btn_save.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save_to)
        btn_row.addWidget(btn_save)
        lay.addLayout(btn_row)

    # ── History ───────────────────────────────────────────────────────────────

    def _push_history(self):
        self._history.append((QPixmap(self._pixmap), self._compressed))
        self._future.clear()
        self._compressed = None

    def _undo_edit(self):
        if self._history:
            self._future.append((QPixmap(self._pixmap), self._compressed))
            self._pixmap, self._compressed = self._history.pop()
            self._crop_w.set_pixmap(self._pixmap)
            self._refresh_info()

    def _redo_edit(self):
        if self._future:
            self._history.append((QPixmap(self._pixmap), self._compressed))
            self._pixmap, self._compressed = self._future.pop()
            self._crop_w.set_pixmap(self._pixmap)
            self._refresh_info()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Undo):
            self._undo_edit()
        elif event.matches(QKeySequence.StandardKey.Redo):
            self._redo_edit()
        else:
            super().keyPressEvent(event)

    # ── Tools ─────────────────────────────────────────────────────────────────

    def _display_name(self) -> str:
        """Filename to show: original name if unmodified, else stem + output extension."""
        if not self._history:
            return self._path.name
        ext = ".png" if self._cover_fmt() == "png" else ".jpg"
        return self._path.stem + ext

    def _refresh_info(self):
        w, h = self._pixmap.width(), self._pixmap.height()
        if self._compressed is not None:
            size_bytes = self._compressed.size()
        else:
            size_bytes = self._encode_pixmap().size()
        if size_bytes >= 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size_bytes / 1024:.0f} KB"
        self._lbl_name.setText(self._display_name())
        self._lbl_stats.setText(f"{w} × {h} px · {size_str}")
        self._lbl_stats.setFixedWidth(self._lbl_stats.fontMetrics().horizontalAdvance(self._lbl_stats.text()) + 4)

    def _set_custom_crop(self):
        a0, b0 = self._ratios[3] if self._ratios[3] else (1, 1)
        dlg = QDialog(self)
        dlg.setWindowTitle("Custom Ratio")
        dlg.setStyleSheet(theme.APP_STYLE)
        dl = QHBoxLayout(dlg)
        dl.setSpacing(8)
        dl.setContentsMargins(16, 14, 16, 14)
        spin_a = QSpinBox(); spin_a.setRange(1, 9999); spin_a.setValue(a0)
        spin_b = QSpinBox(); spin_b.setRange(1, 9999); spin_b.setValue(b0)
        btn_ok = QPushButton("OK"); btn_ok.setObjectName("primary")
        dl.addWidget(spin_a)
        dl.addWidget(QLabel(":"))
        dl.addWidget(spin_b)
        dl.addSpacing(8)
        dl.addWidget(btn_ok)
        btn_ok.clicked.connect(dlg.accept)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        a, b = spin_a.value(), spin_b.value()
        self._ratios[3] = (a, b)
        self._btn_custom.setText(f"{a}:{b}")
        self._btn_custom.setVisible(True)
        QSettings("audiobook-maker", "AudiobookMaker").setValue("cover_editor/crop_custom", f"{a}:{b}")
        self._btn_custom.setChecked(True)
        self._crop_w.set_ratio((a, b))

    def _swap_crop(self):
        s = QSettings("audiobook-maker", "AudiobookMaker")
        # Flip 3:4↔4:3
        self._ratios[2] = (self._ratios[2][1], self._ratios[2][0])
        swapped = self._ratios[2] == (4, 3)
        s.setValue("cover_editor/crop_swapped", int(swapped))
        self._btn_ratio34.setText(f"{self._ratios[2][0]}:{self._ratios[2][1]}")
        # Flip custom ratio too
        if self._ratios[3]:
            self._ratios[3] = (self._ratios[3][1], self._ratios[3][0])
            self._btn_custom.setText(f"{self._ratios[3][0]}:{self._ratios[3][1]}")
            s.setValue("cover_editor/crop_custom", f"{self._ratios[3][0]}:{self._ratios[3][1]}")
        checked = self._crop_grp.checkedId()
        if checked in (2, 3) and self._ratios[checked]:
            self._crop_w.set_ratio(self._ratios[checked])

    def _apply_crop(self):
        rect = self._crop_w.crop_rect_in_source()
        if rect and rect.width() > 1 and rect.height() > 1:
            current_ratio = self._crop_w._ratio
            self._push_history()
            self._pixmap = self._pixmap.copy(rect)
            self._crop_w.set_pixmap(self._pixmap)
            self._refresh_info()
            # Re-apply same ratio to new image (keeps button checked, resets selection area)
            if current_ratio is not None:
                self._crop_w.set_ratio(current_ratio)

    def _apply_resize(self):
        self._push_history()
        self._pixmap = self._pixmap.scaled(
            self._spin_w.value(), self._spin_h.value(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._crop_w.set_pixmap(self._pixmap)
        self._refresh_info()
        s = QSettings("audiobook-maker", "AudiobookMaker")
        s.setValue("cover_editor/resize_w", self._spin_w.value())
        s.setValue("cover_editor/resize_h", self._spin_h.value())

    def _apply_quality(self):
        target = self._spin_kb.value() * 1024

        # Measure current size
        if self._compressed is not None:
            current_size = self._compressed.size()
        else:
            current_size = self._encode_pixmap().size()

        if current_size <= target:
            QMessageBox.warning(
                self, tr("apply"),
                f"Image is already {current_size / 1024:.0f} KB, "
                f"which is within the {self._spin_kb.value()} KB target.\n"
                f"No compression needed.",
            )
            return

        img = self._pixmap.toImage()
        result = QByteArray()
        best: QByteArray | None = None
        for quality in range(100, 0, -1):
            buf = QBuffer(result)
            result.clear()
            buf.open(QBuffer.OpenModeFlag.WriteOnly)
            img.save(buf, "JPEG", quality)
            if result.size() <= target:
                best = QByteArray(result)
                break
        if best is None:
            # Even quality=1 exceeds the target
            min_kb = result.size() / 1024
            QMessageBox.warning(
                self, tr("apply"),
                f"Cannot compress below {min_kb:.0f} KB at this resolution.\n"
                f"Try resizing the image first.",
            )
            return
        new_px = QPixmap()
        new_px.loadFromData(best)
        if not new_px.isNull():
            self._push_quality(best)
            self._pixmap = new_px
            self._crop_w.set_pixmap(self._pixmap)
            self._refresh_info()
            QSettings("audiobook-maker", "AudiobookMaker").setValue(
                "cover_editor/quality_kb", self._spin_kb.value()
            )

    def _push_quality(self, data: "QByteArray"):
        """Store compressed JPEG bytes so _save can write them as-is."""
        self._push_history()
        self._compressed: "QByteArray | None" = data

    @staticmethod
    def _cover_fmt() -> str:
        return QSettings("audiobook-maker", "AudiobookMaker").value("cover_edit_fmt", "jpg")

    def _encode_pixmap(self) -> QByteArray:
        """Encode current pixmap to the output format. Size = actual output size."""
        fmt = self._cover_fmt()
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        if fmt == "png":
            self._pixmap.toImage().save(buf, "PNG")
        else:
            self._pixmap.toImage().save(buf, "JPEG", 92)
        return data

    def _save_to(self):
        fmt = self._cover_fmt()
        ext = ".png" if fmt == "png" else ".jpg"
        qt_fmt = "PNG" if fmt == "png" else "JPEG"
        filter_str = "PNG (*.png)" if fmt == "png" else "JPEG (*.jpg *.jpeg)"
        dest, _ = QFileDialog.getSaveFileName(
            self, tr("save_to"),
            str(self._path.parent / (self._path.stem + "_edited" + ext)),
            filter_str,
        )
        if not dest:
            return
        dest = Path(dest)
        compressed = getattr(self, "_compressed", None)
        # compressed bytes are always JPEG; if format is PNG we must re-save from pixmap
        if compressed is not None and qt_fmt == "JPEG":
            ok = dest.write_bytes(compressed.data()) > 0
        else:
            quality = -1 if qt_fmt == "PNG" else 92
            ok = self._pixmap.save(str(dest), qt_fmt, quality)
        if not ok:
            QMessageBox.critical(self, "Error", "Failed to save cover image.")

    def _save(self):
        fmt = self._cover_fmt()
        ext = ".png" if fmt == "png" else ".jpg"
        qt_fmt = "PNG" if fmt == "png" else "JPEG"
        fd, tmp = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        compressed = getattr(self, "_compressed", None)
        if compressed is not None and qt_fmt == "JPEG":
            with open(tmp, "wb") as f:
                f.write(compressed.data())
            ok = True
        else:
            quality = -1 if qt_fmt == "PNG" else 92
            ok = self._pixmap.save(tmp, qt_fmt, quality)
        if ok:
            self.result_path = Path(tmp)
            self.accept()
        else:
            os.unlink(tmp)
            QMessageBox.critical(self, "Error", "Failed to save cover image.")


class CoverWidget(QLabel):
    cover_path_changed = pyqtSignal(object)

    _last_modified: "CoverWidget | None" = None
    _last_push_time: float = -1.0

    def __init__(self, size: int = 120):
        super().__init__()
        self._SIZE = size
        self._path: Path | None = None
        self._undo_stack: list[Path | None] = []
        self._redo_stack: list[Path | None] = []
        self.setObjectName("coverWidget")
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self._show_placeholder()

    @property
    def cover_path(self) -> Path | None:
        return self._path

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def _push_undo(self):
        self._undo_stack.append(self._path)
        self._redo_stack.clear()
        CoverWidget._last_modified = self
        CoverWidget._last_push_time = time.monotonic()

    def undo(self):
        if self._undo_stack:
            self._redo_stack.append(self._path)
            self._apply_path(self._undo_stack.pop())

    def redo(self):
        if self._redo_stack:
            self._undo_stack.append(self._path)
            self._apply_path(self._redo_stack.pop())

    def set_cover(self, path: Path | None):
        self._push_undo()
        self._apply_path(path)

    @staticmethod
    def _convert_to_output_fmt(path: Path) -> Path:
        """If path is not already in the target format, convert and return a temp file."""
        fmt = QSettings("audiobook-maker", "AudiobookMaker").value("cover_edit_fmt", "jpg")
        target_exts = (".png",) if fmt == "png" else (".jpg", ".jpeg")
        if path.suffix.lower() in target_exts:
            return path
        qt_fmt = "PNG" if fmt == "png" else "JPEG"
        quality = -1 if qt_fmt == "PNG" else 92
        ext = ".png" if qt_fmt == "PNG" else ".jpg"
        subdir = Path(tempfile.gettempdir()) / str(abs(hash(str(path))))
        subdir.mkdir(exist_ok=True)
        tmp = subdir / f"{path.stem}{ext}"
        QPixmap(str(path)).toImage().save(str(tmp), qt_fmt, quality)
        return tmp if tmp.exists() else path

    def _apply_path(self, path: Path | None):
        self._path = self._convert_to_output_fmt(path) if path and path.exists() else path
        if self._path and self._path.exists():
            dpr = QApplication.primaryScreen().devicePixelRatio()
            phys = int(self._SIZE * dpr)
            src = QPixmap(str(self._path)).scaled(
                phys, phys,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            src.setDevicePixelRatio(dpr)
            self.setFixedSize(int(src.width() / dpr), int(src.height() / dpr))
            self.setPixmap(src)
            self.setText("")
            self._set_cv_state("image")
        else:
            self._show_placeholder()
        self.cover_path_changed.emit(self._path)

    def _set_cv_state(self, state: str):
        self.setProperty("cvState", state)
        self.style().unpolish(self)
        self.style().polish(self)

    def _show_placeholder(self):
        self.setFixedSize(self._SIZE, self._SIZE)
        self.clear()
        self.setText(tr("cover"))
        self._set_cv_state("placeholder")

    def retranslate_ui(self):
        if not (self._path and self._path.exists()):
            self._show_placeholder()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._path and self._path.exists():
                self._open_editor()
            else:
                self._upload()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(theme.APP_STYLE)
        act_edit   = menu.addAction(tr("edit_cover"))
        act_edit.setEnabled(bool(self._path and self._path.exists()))
        menu.addSeparator()
        act_upload = menu.addAction(tr("upload"))
        act_delete = menu.addAction(tr("delete"))
        act_delete.setEnabled(self._path is not None)

        chosen = menu.exec(event.globalPos())
        if chosen == act_edit:
            self._open_editor()
        elif chosen == act_upload:
            self._upload()
        elif chosen == act_delete:
            self.set_cover(None)

    def _upload(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("upload").rstrip("…"), "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif *.gif *.avif *.heic *.heif)"
        )
        if path:
            self.set_cover(Path(path))

    def _open_editor(self):
        if not (self._path and self._path.exists()):
            return
        dlg = CoverEditorDialog(self._path, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.set_cover(dlg.result_path)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        from scanner import IMAGE_EXTS
        if urls and Path(urls[0].toLocalFile()).suffix.lower() in IMAGE_EXTS:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        self.set_cover(Path(event.mimeData().urls()[0].toLocalFile()))
        event.acceptProposedAction()
