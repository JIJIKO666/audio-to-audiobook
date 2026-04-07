#!/usr/bin/env python3
"""
Audiobook Maker — entry point.
Run: python main.py
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

import theme
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Audiobook Maker")
    app.setStyle("Fusion")

    # Load saved theme before creating window so colours are correct from the start
    saved_theme = QSettings("audiobook-maker", "AudiobookMaker").value("theme", "light")
    theme._apply_theme(saved_theme)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
