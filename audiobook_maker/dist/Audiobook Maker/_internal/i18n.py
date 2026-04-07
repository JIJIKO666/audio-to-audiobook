from __future__ import annotations

_LANG: str = "en"

_STR: dict[str, dict[str, str]] = {
    "en": {
        "drag_hint":       "Drag-drop a audio folder or click to browse",
        "drop_sub":        "audiobook",
        "delete":          "Delete",
        "delete_book":     "Delete Book",
        "album":           "Album",
        "title_field":     "Title",
        "title_ph":        "Title",
        "artist":          "Artist",
        "remove_aud":      "Remove Audio",
        "expand":          "Expand",
        "collapse":        "Collapse",
        "move_first":      "Move to First",
        "move_last":       "Move to Last",
        "output":          "Output",
        "browse":          "Browse…",
        "create_one":      "Create Audiobook",
        "cover":           "Cover",
        "preview":         "Preview",
        "upload":          "Upload…",
        "menu_edit":       "Edit",
        "undo":            "Undo",
        "redo":            "Redo",
        "rm_order_num":    "Remove Order Number from Track Title",
        "cover_fmt_menu":  "Cover Edit Format",
        "cover_fmt_jpg":   "JPEG",
        "cover_fmt_png":   "PNG",
        "menu_view":       "View",
        "expand_all":      "Expand All Tracks",
        "collapse_all":    "Collapse All Tracks",
        "menu_lang":       "Language",
        "lang_en":         "English",
        "lang_zh":         "中文",
        "lang_sys":        "Follow System",
        "menu_settings":   "Settings",
        "settings_lang":   "Language",
        "settings_theme":  "Theme",
        "theme_light":     "Light",
        "theme_dark":      "Dark",
        "theme_sys":       "Follow System",
        "no_audio":        "No Audio Found",
        "nothing_create":  "Nothing to Create",
        "nothing_msg":     "All sections are empty.",
        "files_exist":     "Files Exist",
        "creating":        "Creating Audiobooks",
        "starting":        "Starting…",
        "cancel":          "Cancel",
        "done":            "Done",
        "col_num":         "#",
        "col_title":       "Chapter Title",
        "col_fmt":         "Format",
        "col_size":        "Size",
        "col_dur":         "Duration",
        "fmt_label":       "Format",
        "qual_label":      "Quality",
        "cover_max_label": "Cover max",
        "cover_kb_hint":   "KB · 600×600 px",
        "copy_quality":    "-",
        "edit_cover":      "Edit Cover",
        "crop":            "Crop",
        "crop_free":       "Free",
        "apply_crop":      "Apply",
        "resize":          "Resize",
        "apply":           "Apply",
        "save_to":         "Save to…",
        "save":            "Save",
        "tt_album":        "Keep the album name consistent within the same book series",
        "tt_title":        "Enter the series name of the same album, such as Volume 1, Season 1, or blank",
        "tt_artist":       "Author / artist",
        "tt_cover_thumb":  "Drag-drop to upload, click / right-click to edit",
        "tt_output":       "Folder where the audiobook file will be saved",
        "tt_fmt":          "Output audio format",
        "tt_quality":      "Audio bitrate ('-' keeps the original bitrate)",
        "tt_cover_w":      "Cover width on export ('-' keeps the original width)",
        "tt_cover_h":      "Cover height on export ('-' keeps the original height)",
        "tt_cover_kb":     "Max cover file size ('-' keeps the original size)",
        "no_sel_title":    "No Selection",
        "no_sel_msg":      "Please select audio tracks to remove.",
    },
    "zh": {
        "drag_hint":       "拖入音频文件夹或点击浏览",
        "drop_sub":        "有声书",
        "delete":          "删除",
        "delete_book":     "删除有声书",
        "album":           "专辑",
        "title_field":     "标题",
        "title_ph":        "标题",
        "artist":          "艺术家",
        "remove_aud":      "删除音频",
        "expand":          "展开",
        "collapse":        "收起",
        "move_first":      "移至首位",
        "move_last":       "移至末位",
        "output":          "输出",
        "browse":          "浏览…",
        "create_one":      "创建有声书",
        "cover":           "封面",
        "preview":         "预览",
        "upload":          "上传…",
        "menu_edit":       "编辑",
        "undo":            "撤销",
        "redo":            "重做",
        "rm_order_num":    "删除曲目序号",
        "cover_fmt_menu":  "封面编辑格式",
        "cover_fmt_jpg":   "JPEG",
        "cover_fmt_png":   "PNG",
        "menu_view":       "视图",
        "expand_all":      "展开所有曲目",
        "collapse_all":    "收起所有曲目",
        "menu_lang":       "语言",
        "lang_en":         "English",
        "lang_zh":         "中文",
        "lang_sys":        "跟随系统",
        "menu_settings":   "设置",
        "settings_lang":   "语言",
        "settings_theme":  "主题",
        "theme_light":     "浅色",
        "theme_dark":      "深色",
        "theme_sys":       "跟随系统",
        "no_audio":        "未找到音频",
        "nothing_create":  "无内容",
        "nothing_msg":     "所有分区均为空。",
        "files_exist":     "文件已存在",
        "creating":        "正在创建有声书",
        "starting":        "正在启动…",
        "cancel":          "取消",
        "done":            "完成",
        "col_num":         "#",
        "col_title":       "章节标题",
        "col_fmt":         "格式",
        "col_size":        "大小",
        "col_dur":         "时长",
        "fmt_label":       "格式",
        "qual_label":      "质量",
        "cover_max_label": "封面上限",
        "cover_kb_hint":   "KB · 600×600 px",
        "copy_quality":    "-",
        "edit_cover":      "编辑封面",
        "crop":            "裁剪",
        "crop_free":       "自由",
        "apply_crop":      "应用",
        "resize":          "尺寸",
        "apply":           "应用",
        "save_to":         "另存为…",
        "save":            "保存",
        "tt_album":        "建议同一系列的专辑名保持一致",
        "tt_title":        "建议输入同专辑的系列号，比如第一卷、第一季，可以为空",
        "tt_artist":       "作者／艺术家",
        "tt_cover_thumb":  "拖入上传，点击／右键编辑",
        "tt_output":       "有声书文件的保存目录",
        "tt_fmt":          "输出音频格式",
        "tt_quality":      "音频比特率（'-' 保持原始比特率）",
        "tt_cover_w":      "导出封面宽度（'-' 保持原始宽度）",
        "tt_cover_h":      "导出封面高度（'-' 保持原始高度）",
        "tt_cover_kb":     "封面文件大小上限（'-' 保持原始大小）",
        "no_sel_title":    "未选择",
        "no_sel_msg":      "请先选择要删除的音频轨道。",
    },
}


def _detect_system_lang() -> str:
    """Return 'zh' if the system locale is Chinese, else 'en'."""
    import locale
    loc = locale.getdefaultlocale()[0] or ""
    return "zh" if loc.startswith("zh") else "en"


def _effective_lang() -> str:
    """Return the actual display language ('en' or 'zh')."""
    if _LANG == "sys":
        return _detect_system_lang()
    return _LANG if _LANG in ("en", "zh") else "en"


def tr(key: str) -> str:
    lang = _effective_lang()
    return _STR.get(lang, _STR["en"]).get(key, _STR["en"].get(key, key))


def _tr_loaded(n_b: int, n_t: int) -> str:
    if _effective_lang() == "zh":
        return f"{n_b} 本有声书  ·  共 {n_t} 首  ·  拖入 / 点击更改"
    pl = "s" if n_b != 1 else ""
    return f"{n_b} audiobook{pl}  ·  {n_t} tracks total  ·  Drag-drop / click to change"


def _tr_create(n: int) -> str:
    if n == 1:
        return tr("create_one")
    return f"创建 {n} 本有声书" if _effective_lang() == "zh" else f"Create {n} Audiobooks"


def _tr_no_audio(folder: str) -> str:
    if _effective_lang() == "zh":
        return f"未在以下目录找到音频文件：\n{folder}"
    return f"No audio files found in:\n{folder}"


def _tr_files_exist(names: str) -> str:
    if _effective_lang() == "zh":
        return f"以下文件将被覆盖：\n{names}\n\n是否继续？"
    return f"These files already exist and will be overwritten:\n{names}\n\nContinue?"


def _tr_done(n: int, paths: str) -> str:
    if _effective_lang() == "zh":
        return f"{n} 本有声书已保存至：\n{paths}"
    pl = "s" if n != 1 else ""
    return f"{n} audiobook{pl} saved to:\n{paths}"


def _tr_error_book(idx: int) -> str:
    if _effective_lang() == "zh":
        return f"错误（第 {idx + 1} 本）"
    return f"Error (book {idx + 1})"
