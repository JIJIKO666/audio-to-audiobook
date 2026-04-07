from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHeaderView,
    QLineEdit,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
)

import theme


class _ComboItemDelegate(QStyledItemDelegate):
    """Custom delegate so macOS native style can't override item colours."""
    def __init__(self, view, combo):
        super().__init__(view)
        self._combo = combo
        self._hovered_row = -1
        view.entered.connect(lambda idx: self._set_hovered(idx.row()))

    def _set_hovered(self, row: int):
        self._hovered_row = row
        self.parent().viewport().update()

    def reset_hover(self):
        self._hovered_row = -1

    def paint(self, painter, option, index):
        option.state &= ~QStyle.StateFlag.State_HasFocus
        painter.save()
        is_hover = index.row() == self._hovered_row
        is_current = index.row() == self._combo.currentIndex()
        if is_hover:
            bg = QColor(theme.C_SEPARATOR)
        elif is_current:
            bg = QColor(theme.C_SEL_BG)
        else:
            bg = QColor(theme.C_BG)
        painter.fillRect(option.rect, bg)
        painter.setPen(QColor(theme.C_LABEL))
        text_rect = option.rect.adjusted(12, 0, -12, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, index.data())
        painter.restore()

    def sizeHint(self, option, index):
        sh = super().sizeHint(option, index)
        return sh.__class__(sh.width(), max(sh.height(), 32))


class _ComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = self.view()
        self._delegate = _ComboItemDelegate(v, self)
        v.setItemDelegate(self._delegate)
        v.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def showPopup(self):
        self._delegate.reset_hover()
        super().showPopup()
        container = next(
            (w for w in QApplication.topLevelWidgets()
             if w.inherits("QComboBoxPrivateContainer") and w.parent() is self),
            None,
        )
        if container is None:
            return
        container.hide()
        container.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        for child in container.findChildren(QFrame):
            child.setFrameShape(QFrame.Shape.NoFrame)
            child.setFrameShadow(QFrame.Shadow.Plain)
        container.show()

    def hidePopup(self):
        self._delegate.reset_hover()
        super().hidePopup()


class _PlainHeaderView(QHeaderView):
    """Header view that always renders section text with normal font weight."""
    def paintSection(self, painter, rect, logical_index):
        if not rect.isValid():
            return
        painter.save()
        # Fill entire section (including sort indicator area) with theme background
        painter.fillRect(rect, QColor(theme.C_BG))
        # Bottom border
        painter.setPen(QColor(theme.C_SEPARATOR))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # Sort indicator
        is_sort = self.isSortIndicatorShown() and self.sortIndicatorSection() == logical_index
        indicator_w = 0
        if is_sort:
            indicator_w = self.style().pixelMetric(QStyle.PixelMetric.PM_HeaderMarkSize) + 8
            arrow_size = 6
            cx = rect.right() - indicator_w // 2
            cy = rect.center().y()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.C_SECONDARY))
            from PyQt6.QtGui import QPolygon
            from PyQt6.QtCore import QPoint
            if self.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder:
                pts = [QPoint(cx, cy - arrow_size // 2),
                       QPoint(cx - arrow_size // 2, cy + arrow_size // 2),
                       QPoint(cx + arrow_size // 2, cy + arrow_size // 2)]
            else:
                pts = [QPoint(cx, cy + arrow_size // 2),
                       QPoint(cx - arrow_size // 2, cy - arrow_size // 2),
                       QPoint(cx + arrow_size // 2, cy - arrow_size // 2)]
            painter.drawPolygon(QPolygon(pts))

        # Text — always centered in the full section width
        text = self.model().headerData(logical_index, self.orientation())
        if text:
            f = self.font()
            f.setWeight(QFont.Weight.Normal)
            painter.setFont(f)
            painter.setPen(QColor(theme.C_SECONDARY))
            painter.drawText(rect.adjusted(12, 0, -12, 0),
                             Qt.AlignmentFlag.AlignCenter, str(text))
        painter.restore()


class _EditorSpinBox(QSpinBox):
    """SpinBox where arrow stepping stops at 50 minimum, but manual input can go lower."""
    _STEP_MIN = 50

    def stepBy(self, steps: int):
        if steps < 0 and self.value() - abs(steps) * self.singleStep() < self._STEP_MIN:
            self.setValue(max(self.value() - abs(steps) * self.singleStep(), self._STEP_MIN))
        else:
            super().stepBy(steps)


class _CoverSpinBox(QSpinBox):
    """SpinBox where clearing the field sets value to 0 (shown as '-')."""
    def validate(self, text, pos):
        from PyQt6.QtGui import QValidator
        clean = text.strip().replace(self.suffix().strip(), "").strip()
        if clean == "" or clean == "-":
            return (QValidator.State.Acceptable, text, pos)
        return super().validate(text, pos)

    def valueFromText(self, text):
        clean = text.strip().replace(self.suffix().strip(), "").strip()
        if clean == "" or clean == "-":
            return 0
        return super().valueFromText(text)


class _LineEdit(QLineEdit):
    def contextMenuEvent(self, event):
        event.ignore()


class _NoMenuDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):  # noqa: ARG002
        return _LineEdit(parent)


def _separator() -> QFrame:
    line = QFrame()
    line.setObjectName("separator")
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    return line
