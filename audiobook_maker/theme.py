from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication

# ── Palette ───────────────────────────────────────────────────────────────────

_THEME: str = "light"  # "light" | "dark" | "system"

_PALETTE_LIGHT = dict(
    C_BG="#FFFFFF", C_BG2="#F6F6F6", C_SEPARATOR="#ECECEC", C_PRESSED="#DBDBDB",
    C_LABEL="#000000", C_SECONDARY="#7C7C7C", C_ROW_ALT="#F4F5F5", 
    C_SEL_BG="#BAD6FB",
    C_ACCENT="#3478F6", C_ACCENT_HOVER="#2056D4", C_ACCENT_PRESSED="#1046A0",
    C_DANGER="#CE4745", C_DANGER_HOVER="#F8EDED", C_DANGER_PRESSED="#ECCBC9",
)
_PALETTE_DARK = dict(
    C_BG="#1B1B1B", C_BG2="#232323", C_SEPARATOR="#2C2C2C", C_PRESSED="#484848",
    C_LABEL="#FFFFFF", C_SECONDARY="#9B9B9B", C_ROW_ALT="#262626", 
    C_SEL_BG="#476288",
    C_ACCENT="#3478F6", C_ACCENT_HOVER="#2056D4", C_ACCENT_PRESSED="#1046A0",
    C_DANGER="#CE4745", C_DANGER_HOVER="#2C2020", C_DANGER_PRESSED="#4C2B29",
)

# Mutable colour globals — start with light
C_BG          = _PALETTE_LIGHT["C_BG"]
C_BG2         = _PALETTE_LIGHT["C_BG2"]
C_SEPARATOR   = _PALETTE_LIGHT["C_SEPARATOR"]
C_PRESSED     = _PALETTE_LIGHT["C_PRESSED"]
C_LABEL       = _PALETTE_LIGHT["C_LABEL"]
C_SECONDARY   = _PALETTE_LIGHT["C_SECONDARY"]
C_ROW_ALT     = _PALETTE_LIGHT["C_ROW_ALT"]
C_SEL_BG      = _PALETTE_LIGHT["C_SEL_BG"]
C_ACCENT      = _PALETTE_LIGHT["C_ACCENT"]
C_ACCENT_HOVER = _PALETTE_LIGHT["C_ACCENT_HOVER"]
C_ACCENT_PRESSED = _PALETTE_LIGHT["C_ACCENT_PRESSED"]
C_DANGER      = _PALETTE_LIGHT["C_DANGER"]
C_DANGER_HOVER   = _PALETTE_LIGHT["C_DANGER_HOVER"]
C_DANGER_PRESSED = _PALETTE_LIGHT["C_DANGER_PRESSED"]

# SVG arrows for QSpinBox (C_SECONDARY is the same in both themes)
_TMP = Path(tempfile.gettempdir())
_ARROW_UP = _TMP / "spinbox_up.svg"
_ARROW_DN = _TMP / "spinbox_dn.svg"
_ARROW_UP.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 5"><polygon points="4,0 0,5 8,5" fill="{C_SECONDARY}"/></svg>')
_ARROW_DN.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 5"><polygon points="0,0 8,0 4,5" fill="{C_SECONDARY}"/></svg>')


def _build_app_style() -> str:
    return f"""
QMainWindow, QWidget {{ background: {C_BG}; color: {C_LABEL}; font-size: 13px; }}

QFrame#separator {{ background: {C_SEPARATOR}; border: none; }}

QFrame#dropZone[dzState="idle"]   {{ border: 1.5px solid {C_SEPARATOR}; border-radius: 12px; background: {C_BG}; }}
QFrame#dropZone[dzState="loaded"] {{ border: 1.5px solid {C_SEPARATOR}; border-radius: 12px; background: {C_BG2}; }}
QFrame#dropZone[dzState="hover"]  {{ border: 1.5px solid {C_ACCENT};    border-radius: 12px; background: {C_BG2}; }}

QLabel#coverWidget[cvState="placeholder"] {{ border: 1.5px solid {C_SEPARATOR}; color: {C_SECONDARY}; font-size: 13px; background: {C_BG2}; }}
QLabel#coverWidget[cvState="image"]       {{ border: none; background: transparent; }}

QTableWidget {{ border: none; outline: none; gridline-color: transparent; }}
QTableWidget::item {{ padding: 0 12px; color: {C_LABEL}; }}
QTableWidget::item:selected {{ background: {C_SEL_BG}; }}
QTableWidget::item:alternate {{ background: {C_ROW_ALT}; }}
QTableWidget::item:alternate:selected {{ background: {C_SEL_BG}; }}

QHeaderView {{ border: none; }}
QHeaderView::section {{ color: {C_SECONDARY}; padding: 5px 12px; border: none; border-bottom: 1px solid {C_SEPARATOR}; }}
QHeaderView::section:selected {{ font-weight: normal; }}

QLabel {{ color: {C_SECONDARY};  border: none; background: transparent; }}
QLabel#dom {{ color: {C_LABEL}; }}
QLabel#sub {{ font-size: 12px; }}
QLabel#icon {{ font-size: 30px; }}

QLineEdit {{
    background: {C_BG2}; border: 1px solid transparent; border-radius: 6px; padding: 5px 12px;
    selection-background-color: {C_SEL_BG}; selection-color: {C_LABEL};
}}
QLineEdit:focus {{ border: 1px solid {C_ACCENT}; }}
QLineEdit::placeholder {{ color: {C_SECONDARY}; }}
QAbstractItemView QLineEdit {{ border-radius: 0; padding: 0px; }}

QLineEdit#pathField {{ color: {C_SECONDARY}; background: transparent; border: none; padding: 0px; }}
QLineEdit#sub {{ background: transparent;border: none; padding: 0px; color: {C_SECONDARY}; font-size: 12px;  }}

QComboBox {{ background: {C_BG2}; border: 1px solid transparent; border-radius: 6px; padding: 5px 12px; }}
QComboBox:hover {{ background: {C_SEPARATOR}; }}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{ background: transparent; border: none; padding: 2px; outline: 0; }}

QMenu {{ border: 1px solid {C_SEPARATOR}; padding: 2px; }}
QMenu::item {{ padding: 5px 12px; }}
QMenu::item:selected {{ background: {C_SEL_BG}; }}
QMenu::item:disabled {{ color: {C_SECONDARY}; }}
QMenu::separator {{ height: 1px; background: {C_SEPARATOR}; margin: 2px 8px; }}

QPushButton {{ background: {C_BG2}; border: 1px solid {C_BG2}; padding: 5px 14px; border-radius: 13px; min-width: 40px; }}
QPushButton:hover   {{ background: {C_SEPARATOR}; border-color: {C_SEPARATOR}; }}
QPushButton:pressed {{ background: {C_PRESSED}; border-color: {C_PRESSED}; }}

QPushButton#cropMode {{ background: transparent; color: {C_SECONDARY}; border: 1px solid {C_SEPARATOR}; padding: 5px; border-radius: 6px; }}
QPushButton#cropMode:checked {{ background: {C_ACCENT}; color: white; border-color: {C_ACCENT}; }}
QPushButton#cropMode:hover:!checked {{ background: {C_SEPARATOR}; color: {C_LABEL}; }}

QPushButton#cropModeCustom {{ background: transparent; color: {C_ACCENT}; border: 1px solid {C_ACCENT}; padding: 5px; border-radius: 6px; }}
QPushButton#cropModeCustom:checked {{ background: {C_ACCENT}; color: white; }}
QPushButton#cropModeCustom:hover:!checked {{ background: {C_SEL_BG}; }}

QPushButton#primary {{ background: {C_ACCENT}; color: white; border: 1px solid {C_ACCENT}; }}
QPushButton#primary:hover    {{ background: {C_ACCENT_HOVER}; border-color: {C_ACCENT_HOVER}; }}
QPushButton#primary:pressed  {{ background: {C_ACCENT_PRESSED}; border-color: {C_ACCENT_PRESSED}; }}
QPushButton#primary:disabled {{ background: {C_SEL_BG}; color: white; border-color: {C_SEL_BG}; }}

QPushButton#danger {{ background: transparent; color: {C_DANGER}; border: 1px solid transparent; }}
QPushButton#danger:hover   {{ background: {C_DANGER_HOVER}; border-color: {C_DANGER_HOVER}; }}
QPushButton#danger:pressed {{ background: {C_DANGER_PRESSED}; border-color: {C_DANGER_PRESSED}; }}

QPushButton#revise {{ background: transparent; border: 1px solid {C_SEPARATOR}; }}
QPushButton#revise:hover   {{ background: {C_SEPARATOR}; border-color: {C_SEPARATOR}; }}
QPushButton#revise:pressed {{ background: {C_PRESSED}; border-color: {C_PRESSED}; }}
QPushButton#revise:disabled {{ color: {C_SECONDARY}; }}

QPushButton#icon {{ padding: 5px; min-width: 20px; }}

QSpinBox {{ background: {C_BG2}; border: none; border-radius: 6px; padding: 3px 6px; selection-background-color: {C_SEL_BG}; selection-color: {C_LABEL}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 20px; background: transparent; border-left: 1px solid {C_SEPARATOR}; }}
QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; border-bottom: 1px solid {C_SEPARATOR}; border-top-right-radius: 6px; }}
QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; border-top: 1px solid {C_SEPARATOR}; border-bottom-right-radius: 6px; }}
QSpinBox::up-arrow   {{ image: url({_ARROW_UP}); height: 3px; }}
QSpinBox::down-arrow {{ image: url({_ARROW_DN}); height: 3px; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover   {{ background: {C_SEPARATOR}; }}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{ background: {C_PRESSED}; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ width: 6px; background: transparent; margin: 0; }}
QScrollBar::handle:vertical {{ background: {C_SECONDARY}; border-radius: 3px; min-height: 20px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QMessageBox {{ }}
QMessageBox QLabel {{ background: transparent; }}
QMessageBox QPushButton {{ background: {C_BG2}; border: none; padding: 6px 14px; border-radius: 13px; min-width: 50px; }}
QMessageBox QPushButton:hover   {{ background: {C_SEPARATOR}; }}
QMessageBox QPushButton:pressed {{ background: {C_PRESSED}; }}
QMessageBox QPushButton:default {{ background: {C_ACCENT}; color: white; }}
QMessageBox QPushButton:default:hover   {{ background: {C_ACCENT_HOVER}; }}
QMessageBox QPushButton:default:pressed {{ background: {C_ACCENT_PRESSED}; }}

QProgressBar {{ background: {C_SEPARATOR}; height: 8px; border-radius: 8px; }}
QProgressBar::chunk {{ background: {C_ACCENT}; border-radius: 8px; }}

QToolTip {{ color: {C_LABEL}; background-color: {C_BG2}; border: 1px solid {C_SEPARATOR}; padding: 1px 2px; font-size: 12px; }}
"""


APP_STYLE = _build_app_style()


def _effective_is_dark() -> bool:
    if _THEME == "dark":   return True
    if _THEME == "light":  return False
    try:
        from PyQt6.QtGui import QPalette as _QPal
        _app = QApplication.instance()
        if _app:
            return _app.palette().color(_QPal.ColorRole.Window).lightness() < 128
    except Exception:
        pass
    return False


def _apply_theme(theme: str) -> None:
    global _THEME, APP_STYLE, C_BG, C_BG2, C_SEPARATOR, C_PRESSED, C_LABEL, C_SECONDARY, C_ROW_ALT
    global C_SEL_BG, C_ACCENT, C_ACCENT_HOVER, C_ACCENT_PRESSED, C_DANGER, C_DANGER_HOVER, C_DANGER_PRESSED
    _THEME = theme
    pal = _PALETTE_DARK if _effective_is_dark() else _PALETTE_LIGHT
    C_BG = pal["C_BG"]; C_BG2 = pal["C_BG2"]; C_SEPARATOR = pal["C_SEPARATOR"]; C_PRESSED = pal["C_PRESSED"]
    C_LABEL = pal["C_LABEL"]; C_SECONDARY = pal["C_SECONDARY"]; C_ROW_ALT = pal["C_ROW_ALT"]
    C_SEL_BG = pal["C_SEL_BG"]
    C_ACCENT = pal["C_ACCENT"]; C_ACCENT_HOVER = pal["C_ACCENT_HOVER"]; C_ACCENT_PRESSED = pal["C_ACCENT_PRESSED"]
    C_DANGER = pal["C_DANGER"]; C_DANGER_HOVER = pal["C_DANGER_HOVER"]; C_DANGER_PRESSED = pal["C_DANGER_PRESSED"]
    APP_STYLE = _build_app_style()
    _app = QApplication.instance()
    if _app:
        _app.setStyleSheet(APP_STYLE)
