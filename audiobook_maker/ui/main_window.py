from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import i18n
import theme
from i18n import tr, _tr_create, _tr_no_audio, _tr_files_exist, _tr_done, _tr_error_book
from scanner import get_direct_audio, find_audiobook_dirs
from workers import ConvertWorker
from ui.widgets import _LineEdit, _ComboBox, _CoverSpinBox, _separator
from ui.dialogs import _ProgressDialog
from ui.drop_zone import DropZone
from ui.track_table import TrackTable
from ui.cover_widget import CoverWidget
from ui.section import AudiobookSection, _SectionScroll


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        s = QSettings("audiobook-maker", "AudiobookMaker")
        i18n._LANG = s.value("lang", "en")
        theme._apply_theme(s.value("theme", "light"))

        self.setWindowTitle("Audiobook Maker")
        self.setMinimumSize(700, 100)
        self._sections: list[AudiobookSection] = []
        # Each entry: (timestamp, [(section, original_idx, restore_tracks)], in_ui)
        # in_ui=True  → sections are currently in the UI; undo removes them
        # in_ui=False → sections are currently hidden;   undo restores them
        self._sec_undo: list[tuple[float, list, bool]] = []
        self._sec_redo: list[tuple[float, list, bool]] = []
        self._conv_worker: ConvertWorker | None = None
        self._progress: _ProgressDialog | None = None
        self._build_ui()
        self._fit_window()
        if s.contains("pos"):
            self.move(s.value("pos"))

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menubar()

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setSpacing(0)
        # Right margin 0 so the scrollbar sits flush at the window edge.
        # Drop zone and bottom bar compensate with their own internal right padding.
        main.setContentsMargins(8, 10, 8, 10)

        # Drop zone (always visible) — wrapped to add its own horizontal margin
        self.drop_zone = DropZone()
        self.drop_zone.folders_dropped.connect(self.load_folders)
        self.drop_zone._dir_hint = lambda: self.edit_out.text()
        _dz_wrap = QWidget()
        _dz_lay = QHBoxLayout(_dz_wrap)
        _dz_lay.setContentsMargins(10, 10, 10, 10)
        _dz_lay.addWidget(self.drop_zone)
        main.addWidget(_dz_wrap)

        # Scrollable section list (hidden until content loaded)
        self.scroll = _SectionScroll()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._sections_lay = QVBoxLayout(self._content)
        self._sections_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._sections_lay.setSpacing(10)
        self._sections_lay.setContentsMargins(15, 4, 10, 4)
        self.scroll.setWidget(self._content)
        self.scroll.setVisible(False)
        main.addWidget(self.scroll)

        # Bottom bar (hidden until content loaded)
        self._bottom = QWidget()
        bl = QVBoxLayout(self._bottom)
        # Right margin 20 compensates for main layout's 0 right margin
        bl.setContentsMargins(10, 10, 10, 10)
        bl.setSpacing(10)
        bl.addWidget(_separator())

        # Output directory row
        out_row = QHBoxLayout()
        out_row.setSpacing(10)
        self._out_lbl = QLabel(tr("output"))
        self._out_lbl.setFixedWidth(50)
        self._out_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        out_row.addWidget(self._out_lbl)
        self.edit_out = _LineEdit(str(Path.home() / "Downloads"))
        self.edit_out.setToolTip(tr("tt_output"))
        out_row.addWidget(self.edit_out, stretch=1)
        self._btn_browse = QPushButton(tr("browse"))
        self._btn_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self._btn_browse)
        bl.addLayout(out_row)

        # Output options row: Format | Quality | Cover max
        opts_row = QHBoxLayout()
        opts_row.setSpacing(10)

        self._lbl_fmt = QLabel(tr("fmt_label"))
        self._lbl_fmt.setFixedWidth(50)
        self._lbl_fmt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        opts_row.addWidget(self._lbl_fmt)
        self.combo_fmt = _ComboBox()
        self.combo_fmt.addItem("M4A", "aac")
        self.combo_fmt.addItem("MP3", "libmp3lame")
        self.combo_fmt.setToolTip(tr("tt_fmt"))
        opts_row.addWidget(self.combo_fmt)

        opts_row.addSpacing(10)

        self._lbl_qual = QLabel(tr("qual_label"))
        opts_row.addWidget(self._lbl_qual)
        self.combo_qual = _ComboBox()
        self.combo_qual.setMinimumWidth(90)
        self.combo_qual.addItem(tr("copy_quality"), None)
        self.combo_qual.addItem("48 kbps", "48k")
        self.combo_qual.addItem("64 kbps  (small)", "64k")
        self.combo_qual.addItem("96 kbps  (balance)", "96k")
        self.combo_qual.addItem("128 kbps (quality)", "128k")
        self.combo_qual.addItem("192 kbps", "192k")
        self.combo_qual.addItem("256 kbps", "256k")
        self.combo_qual.setToolTip(tr("tt_quality"))
        opts_row.addWidget(self.combo_qual)

        opts_row.addSpacing(10)

        _s = QSettings("audiobook-maker", "AudiobookMaker")
        self._lbl_cover_out = QLabel(tr("cover"))
        opts_row.addWidget(self._lbl_cover_out)

        def _make_cover_spin(max_val, suffix, setting_key):
            sb = _CoverSpinBox()
            sb.setRange(0, max_val)
            sb.setSpecialValueText("-")
            sb.setSuffix(suffix)
            sb.setSingleStep(50)
            sb.setValue(int(_s.value(setting_key, 0)))
            return sb

        self.spin_cover_w  = _make_cover_spin(9999,  " px", "cover_editor/resize_w")
        self.spin_cover_w.setToolTip(tr("tt_cover_w"))
        opts_row.addWidget(self.spin_cover_w)

        _lbl_x = QLabel("×")
        opts_row.addWidget(_lbl_x)

        self.spin_cover_h  = _make_cover_spin(9999,  " px", "cover_editor/resize_h")
        self.spin_cover_h.setToolTip(tr("tt_cover_h"))
        opts_row.addWidget(self.spin_cover_h)

        _lbl_dot = QLabel("·")
        opts_row.addWidget(_lbl_dot)

        self.spin_cover_kb = _make_cover_spin(99999, " KB", "cover_editor/quality_kb")
        self.spin_cover_kb.setToolTip(tr("tt_cover_kb"))
        opts_row.addWidget(self.spin_cover_kb)

        opts_row.addStretch()
        bl.addLayout(opts_row)

        self.btn_create = QPushButton(tr("create_one"))
        self.btn_create.setObjectName("primary")
        self.btn_create.setFixedHeight(40)
        self.btn_create.clicked.connect(self._start_conversion)
        bl.addSpacing(10)
        bl.addWidget(self.btn_create)

        self._bottom.setVisible(False)
        main.addWidget(self._bottom)

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menubar(self):
        mb = self.menuBar()

        self._menu_settings = mb.addMenu(tr("menu_settings"))

        self._menu_settings_lang = self._menu_settings.addMenu(tr("settings_lang"))
        self._act_lang_en = self._menu_settings_lang.addAction(tr("lang_en"))
        self._act_lang_en.setCheckable(True)
        self._act_lang_en.triggered.connect(lambda: self._set_language("en"))
        self._act_lang_zh = self._menu_settings_lang.addAction(tr("lang_zh"))
        self._act_lang_zh.setCheckable(True)
        self._act_lang_zh.triggered.connect(lambda: self._set_language("zh"))
        self._act_lang_sys = self._menu_settings_lang.addAction(tr("lang_sys"))
        self._act_lang_sys.setCheckable(True)
        self._act_lang_sys.triggered.connect(lambda: self._set_language("sys"))
        self._sync_lang_checks()

        self._menu_settings.addSeparator()

        self._menu_settings_theme = self._menu_settings.addMenu(tr("settings_theme"))
        self._act_theme_light = self._menu_settings_theme.addAction(tr("theme_light"))
        self._act_theme_light.setCheckable(True)
        self._act_theme_light.triggered.connect(lambda: self._set_theme("light"))
        self._act_theme_dark = self._menu_settings_theme.addAction(tr("theme_dark"))
        self._act_theme_dark.setCheckable(True)
        self._act_theme_dark.triggered.connect(lambda: self._set_theme("dark"))
        self._act_theme_sys = self._menu_settings_theme.addAction(tr("theme_sys"))
        self._act_theme_sys.setCheckable(True)
        self._act_theme_sys.triggered.connect(lambda: self._set_theme("sys"))
        self._sync_theme_checks()

        self._menu_edit = mb.addMenu(tr("menu_edit"))

        self._act_undo = self._menu_edit.addAction(tr("undo"))
        self._act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._act_undo.triggered.connect(self._undo)

        self._act_redo = self._menu_edit.addAction(tr("redo"))
        self._act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._act_redo.triggered.connect(self._redo)

        self._menu_edit.addSeparator()
        self._act_rm_order_num = self._menu_edit.addAction(tr("rm_order_num"))
        self._act_rm_order_num.setCheckable(True)
        _rm_default = QSettings("audiobook-maker", "AudiobookMaker").value(
            "remove_order_num", True, type=bool
        )
        self._act_rm_order_num.setChecked(_rm_default)
        self._act_rm_order_num.triggered.connect(self._toggle_rm_order_num)

        self._menu_edit.addSeparator()
        self._menu_cover_fmt = self._menu_edit.addMenu(tr("cover_fmt_menu"))
        self._act_cover_fmt_jpg = self._menu_cover_fmt.addAction(tr("cover_fmt_jpg"))
        self._act_cover_fmt_jpg.setCheckable(True)
        self._act_cover_fmt_jpg.triggered.connect(lambda: self._set_cover_fmt("jpg"))
        self._act_cover_fmt_png = self._menu_cover_fmt.addAction(tr("cover_fmt_png"))
        self._act_cover_fmt_png.setCheckable(True)
        self._act_cover_fmt_png.triggered.connect(lambda: self._set_cover_fmt("png"))
        _saved_fmt = QSettings("audiobook-maker", "AudiobookMaker").value("cover_edit_fmt", "jpg")
        self._act_cover_fmt_jpg.setChecked(_saved_fmt == "jpg")
        self._act_cover_fmt_png.setChecked(_saved_fmt == "png")

        self._menu_edit.aboutToShow.connect(self._refresh_undo_actions)

        self._menu_view = mb.addMenu(tr("menu_view"))
        self._act_expand_all = self._menu_view.addAction(tr("expand_all"))
        self._act_expand_all.triggered.connect(self._expand_all_sections)
        self._act_collapse_all = self._menu_view.addAction(tr("collapse_all"))
        self._act_collapse_all.triggered.connect(self._collapse_all_sections)

    def _toggle_rm_order_num(self, checked: bool):
        QSettings("audiobook-maker", "AudiobookMaker").setValue("remove_order_num", checked)

    def _set_cover_fmt(self, fmt: str):
        QSettings("audiobook-maker", "AudiobookMaker").setValue("cover_edit_fmt", fmt)
        self._act_cover_fmt_jpg.setChecked(fmt == "jpg")
        self._act_cover_fmt_png.setChecked(fmt == "png")

    # ── View actions ─────────────────────────────────────────────────────────

    def _expand_all_sections(self):
        for s in self._sections:
            if not s._expanded:
                s._expanded = True
                s._apply_table_height()
                s._btn_expand.setText(tr("collapse"))

    def _collapse_all_sections(self):
        for s in self._sections:
            if s._expanded:
                s._expanded = False
                s._apply_table_height()
                s._btn_expand.setText(tr("expand"))

    # ── Language / Theme switching ────────────────────────────────────────────

    def _sync_lang_checks(self):
        self._act_lang_en.setChecked(i18n._LANG == "en")
        self._act_lang_zh.setChecked(i18n._LANG == "zh")
        self._act_lang_sys.setChecked(i18n._LANG == "sys")

    def _sync_theme_checks(self):
        self._act_theme_light.setChecked(theme._THEME == "light")
        self._act_theme_dark.setChecked(theme._THEME == "dark")
        self._act_theme_sys.setChecked(theme._THEME == "sys")

    def _set_language(self, lang: str):
        if i18n._LANG == lang:
            return
        i18n._LANG = lang
        QSettings("audiobook-maker", "AudiobookMaker").setValue("lang", lang)
        self._sync_lang_checks()
        self.retranslate_ui()

    def _set_theme(self, thm: str):
        if theme._THEME == thm:
            return
        theme._apply_theme(thm)
        QSettings("audiobook-maker", "AudiobookMaker").setValue("theme", thm)
        self._sync_theme_checks()
        self.drop_zone.retheme()

    def retranslate_ui(self):
        self._menu_edit.setTitle(tr("menu_edit"))
        self._menu_view.setTitle(tr("menu_view"))
        self._act_expand_all.setText(tr("expand_all"))
        self._act_collapse_all.setText(tr("collapse_all"))
        self._menu_settings.setTitle(tr("menu_settings"))
        self._menu_settings_lang.setTitle(tr("settings_lang"))
        self._menu_settings_theme.setTitle(tr("settings_theme"))
        self._act_undo.setText(tr("undo"))
        self._act_redo.setText(tr("redo"))
        self._act_rm_order_num.setText(tr("rm_order_num"))
        self._menu_cover_fmt.setTitle(tr("cover_fmt_menu"))
        self._act_cover_fmt_jpg.setText(tr("cover_fmt_jpg"))
        self._act_cover_fmt_png.setText(tr("cover_fmt_png"))
        self._act_lang_en.setText(tr("lang_en"))
        self._act_lang_zh.setText(tr("lang_zh"))
        self._act_lang_sys.setText(tr("lang_sys"))
        self._act_theme_light.setText(tr("theme_light"))
        self._act_theme_dark.setText(tr("theme_dark"))
        self._act_theme_sys.setText(tr("theme_sys"))

        self.drop_zone.retranslate_ui()

        self._out_lbl.setText(tr("output"))
        self._btn_browse.setText(tr("browse"))
        self._lbl_fmt.setText(tr("fmt_label"))
        self._lbl_qual.setText(tr("qual_label"))
        self._lbl_cover_out.setText("Cover")
        self.combo_qual.setItemText(0, tr("copy_quality"))
        self.edit_out.setToolTip(tr("tt_output"))
        self.combo_fmt.setToolTip(tr("tt_fmt"))
        self.combo_qual.setToolTip(tr("tt_quality"))
        self.spin_cover_w.setToolTip(tr("tt_cover_w"))
        self.spin_cover_h.setToolTip(tr("tt_cover_h"))
        self.spin_cover_kb.setToolTip(tr("tt_cover_kb"))

        n = len(self._sections)
        self.btn_create.setText(_tr_create(n) if n > 0 else tr("create_one"))

        for sec in self._sections:
            sec.retranslate_ui()

    # ── Folder loading ────────────────────────────────────────────────────────

    def load_folders(self, folders: "list[Path]"):
        self._clear_sections()

        # Collect all audiobook dirs across all dropped folders
        all_dirs: list[tuple[Path, Path]] = []  # (dir, root)
        for folder in folders:
            for d in find_audiobook_dirs(folder):
                all_dirs.append((d, folder))

        if not all_dirs:
            label = folders[0].name if len(folders) == 1 else str(folders[0])
            QMessageBox.warning(self, tr("no_audio"), _tr_no_audio(label))
            return

        batch_entries = []
        for i, (d, root) in enumerate(all_dirs):
            if i > 0:
                self._sections_lay.addWidget(_separator())
            section = AudiobookSection(d, root)
            section.delete_requested.connect(self._delete_section)
            section.table.tracks_changed.connect(self._on_tracks_changed)
            self._sections_lay.addWidget(section)
            self._sections.append(section)
            batch_entries.append((section, i, None))

        # Push whole import as one atomic undo entry (in_ui=True)
        self._sec_undo.append((time.monotonic(), batch_entries, True))
        # Reset table/cover timestamps so undo picks the import, not a cover load
        TrackTable._last_push_time = 0.0
        CoverWidget._last_push_time = -1.0

        first_name = folders[0].name
        extra = len(folders) - 1
        n_books  = len(all_dirs)
        n_tracks = sum(len(get_direct_audio(d)) for d, _ in all_dirs)
        self.drop_zone.set_loaded(first_name, n_books, n_tracks, extra)
        self.btn_create.setText(_tr_create(n_books))
        self.scroll.setVisible(True)
        self._bottom.setVisible(True)
        self._fit_window()

    def _clear_sections(self):
        for s in self._sections:
            s.stop_worker()
        self._sections.clear()
        for _, entries, _ in self._sec_undo:
            for sec, _, _ in entries:
                sec.deleteLater()
        for _, entries, _ in self._sec_redo:
            for sec, _, _ in entries:
                sec.deleteLater()
        self._sec_undo.clear()
        self._sec_redo.clear()
        while self._sections_lay.count():
            item = self._sections_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _delete_section(self, section: AudiobookSection):
        """Called by section.delete_requested signal — removes section and pushes undo."""
        restore_tracks = getattr(section, '_restore_tracks', None)
        section._restore_tracks = None
        idx = self._sections.index(section) if section in self._sections else 0
        self._remove_section_from_ui(section)
        self._sec_undo.append((time.monotonic(), [(section, idx, restore_tracks)], False))
        self._sec_redo.clear()
        self._update_after_sections_change()

    def _remove_section_from_ui(self, section: AudiobookSection):
        section.stop_worker()
        if section in self._sections:
            self._sections.remove(section)
        section.setParent(None)
        section.hide()
        self._rebuild_separators()

    def _restore_section_to_ui(self, section: AudiobookSection, idx: int,
                                restore_tracks: "list | None"):
        self._sections.insert(idx, section)
        self._rebuild_separators()
        section.show()
        if restore_tracks is not None:
            section.table._tracks = restore_tracks
            section._restore_tracks = None
            section.table._rebuild()

    def _rebuild_separators(self):
        sb = self.scroll.verticalScrollBar()
        saved = sb.value()
        while self._sections_lay.count():
            item = self._sections_lay.takeAt(0)
            w = item.widget()
            if w:
                if isinstance(w, AudiobookSection):
                    w.setParent(None)
                else:
                    w.deleteLater()
        for i, s in enumerate(self._sections):
            if i > 0:
                self._sections_lay.addWidget(_separator())
            self._sections_lay.addWidget(s)
        sb.setValue(saved)

    def _on_tracks_changed(self):
        """Called when tracks are added/removed in any table; updates drop zone count.
        Note: _after_table_change runs first (connected earlier), so if a section
        was auto-deleted its removal from self._sections has already happened here."""
        if not self._sections or self.drop_zone._loaded_name is None:
            return
        n_tracks = sum(s.track_count for s in self._sections)
        self.drop_zone.update_counts(len(self._sections), n_tracks)

    def _update_after_sections_change(self):
        n = len(self._sections)
        if n == 0:
            self.scroll.setVisible(False)
            self._bottom.setVisible(False)
            self.drop_zone.reset()
            self._fit_window()
        else:
            n_tracks = sum(s.track_count for s in self._sections)
            self.drop_zone.update_counts(n, n_tracks)
            self.btn_create.setText(_tr_create(n))
            self.scroll.setVisible(True)
            self._bottom.setVisible(True)
            self._fit_window()

    # ── Undo / Redo ──────────────────────────────────────────────────────────

    def _active_table(self) -> "TrackTable | None":
        fw = QApplication.focusWidget()
        w = fw
        while w:
            if isinstance(w, TrackTable):
                return w
            w = w.parent()
        return TrackTable._last_modified

    def _refresh_undo_actions(self):
        self._act_undo.setText(tr("undo"))
        self._act_redo.setText(tr("redo"))

    def _apply_sec_op(self, stack_from: list, stack_to: list):
        """Shared logic for undo/redo of section-level operations."""
        ts, entries, in_ui = stack_from.pop()
        if in_ui:
            # Sections are in UI → remove them all
            for section, idx, _ in entries:
                self._remove_section_from_ui(section)
            stack_to.append((time.monotonic(), entries, False))
        else:
            # Sections are hidden → restore them all
            for section, idx, restore_tracks in entries:
                self._restore_section_to_ui(section, idx, restore_tracks)
            stack_to.append((time.monotonic(), entries, True))
        self._update_after_sections_change()

    def _undo(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit):
            fw.undo()
            return
        table = self._active_table()
        cover = CoverWidget._last_modified
        sec_time = self._sec_undo[-1][0] if self._sec_undo else -1.0
        tbl_time = TrackTable._last_push_time if (table and table.can_undo) else -1.0
        cov_time = CoverWidget._last_push_time if (cover and cover.can_undo) else -1.0
        latest = max(sec_time, tbl_time, cov_time)
        if latest == -1.0:
            return
        if cov_time == latest:
            cover.undo()
        elif sec_time == latest:
            self._apply_sec_op(self._sec_undo, self._sec_redo)
        else:
            table.undo()

    def _redo(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit):
            fw.redo()
            return
        table = self._active_table()
        cover = CoverWidget._last_modified
        sec_time = self._sec_redo[-1][0] if self._sec_redo else -1.0
        tbl_time = TrackTable._last_push_time if (table and table.can_redo) else -1.0
        cov_time = CoverWidget._last_push_time if (cover and cover.can_redo) else -1.0
        latest = max(sec_time, tbl_time, cov_time)
        if latest == -1.0:
            return
        if cov_time == latest:
            cover.redo()
        elif sec_time == latest:
            self._apply_sec_op(self._sec_redo, self._sec_undo)
        else:
            table.redo()

    def _fit_window(self):
        QApplication.processEvents()
        cur_w = self.width() if self.isVisible() else 0
        screen_h = QApplication.primaryScreen().availableGeometry().height()
        cap = int(screen_h * 0.8)

        # Compute natural height manually — adjustSize() can't see past QScrollArea's viewport
        lay = self.centralWidget().layout()
        m = lay.contentsMargins()
        dz_h = 70 + 20  # DropZone fixedHeight + wrap margins (10+10)
        content_h = self._content.sizeHint().height() if self.scroll.isVisible() else 0
        bottom_h  = self._bottom.sizeHint().height()  if self._bottom.isVisible()  else 0
        spacing   = lay.spacing() * (sum([self.scroll.isVisible(), self._bottom.isVisible()]))
        natural_h = self.menuBar().height() + m.top() + m.bottom() + dz_h + content_h + bottom_h + spacing

        h = min(natural_h, cap)
        self.resize(cur_w if cur_w > 0 else self.sizeHint().width(), h)

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select output folder", self.edit_out.text())
        if d:
            self.edit_out.setText(d)

    # ── Conversion ───────────────────────────────────────────────────────────

    def _start_conversion(self):
        out_dir = Path(self.edit_out.text())
        audio_codec   = self.combo_fmt.currentData()
        audio_quality = self.combo_qual.currentData()
        cover_max_w   = self.spin_cover_w.value()
        cover_max_h   = self.spin_cover_h.value()
        cover_max_kb  = self.spin_cover_kb.value()

        jobs = [
            s.job(out_dir, audio_codec=audio_codec,
                  audio_quality=audio_quality,
                  cover_max_w=cover_max_w, cover_max_h=cover_max_h,
                  cover_max_kb=cover_max_kb)
            for s in self._sections
        ]
        jobs = [j for j in jobs if j]

        if not jobs:
            QMessageBox.warning(self, tr("nothing_create"), tr("nothing_msg"))
            return

        clashes = [j for j in jobs if j["output"].exists()]
        if clashes:
            names = "\n".join(f"  · {j['output'].name}" for j in clashes)
            ans = QMessageBox.question(
                self, tr("files_exist"), _tr_files_exist(names),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        self._progress = _ProgressDialog(len(jobs), self)
        self._progress.setDetail(tr("starting"))
        self._progress.show()

        self._conv_worker = ConvertWorker(jobs)
        self._conv_worker.progress.connect(self._on_progress)
        self._conv_worker.book_start.connect(lambda _, t: self._on_book_start(t))
        self._conv_worker.book_done.connect(self._on_book_done)
        self._conv_worker.book_error.connect(self._on_book_error)
        self._conv_worker.all_done.connect(self._on_all_done)
        self._progress.canceled.connect(self._on_cancelled)
        self._conv_worker.start()
        self.btn_create.setEnabled(False)

    def _on_progress(self, msg: str):
        if self._progress:
            self._progress.setDetail(msg)

    def _on_book_start(self, title: str):
        if self._progress:
            self._progress.setTitle(title)
            self._progress.setDetail("")

    def _on_book_done(self, idx: int):
        if self._progress:
            self._progress.setValue(idx + 1)

    def _on_book_error(self, idx: int, msg: str):
        QMessageBox.critical(self, _tr_error_book(idx), msg)

    def _on_cancelled(self):
        if self._conv_worker:
            self._conv_worker.terminate()
            self._conv_worker.wait()
        if self._progress:
            self._progress.close()
            self._progress = None
        self.btn_create.setEnabled(True)

    def _on_all_done(self, outputs: list):
        if self._progress:
            self._progress.close()
            self._progress = None
        self.btn_create.setEnabled(True)
        if outputs:
            paths = "\n".join(f"  · {o}" for o in outputs)
            QMessageBox.information(self, tr("done"), _tr_done(len(outputs), paths))

    # ── Geometry ──────────────────────────────────────────────────────────────

    def moveEvent(self, event):
        self._persist_geometry(); super().moveEvent(event)

    def resizeEvent(self, event):
        self._persist_geometry(); super().resizeEvent(event)

    def closeEvent(self, event):
        self._persist_geometry(); super().closeEvent(event)

    def _persist_geometry(self):
        QSettings("audiobook-maker", "AudiobookMaker").setValue("pos", self.pos())
