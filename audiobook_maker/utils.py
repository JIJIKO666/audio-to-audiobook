from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import QSettings

# ── Chinese ordinal → integer (for natural sort) ──────────────────────────────
_ZH_NUM: dict[str, int] = {
    '上': 1, '中': 2, '下': 3,
    '一': 1, '壹': 1,
    '二': 2, '贰': 2, '两': 2,
    '三': 3, '叁': 3,
    '四': 4, '肆': 4,
    '五': 5, '伍': 5,
    '六': 6, '陆': 6,
    '七': 7, '柒': 7,
    '八': 8, '捌': 8,
    '九': 9, '玖': 9,
    '十': 10, '拾': 10,
}
_ZH_CHARS = ''.join(_ZH_NUM)

# Split on digit runs OR individual Chinese ordinal characters
_NATURAL_SPLIT = re.compile(rf"(\d+|[{_ZH_CHARS}])")


def _natural_key(s: str) -> list:
    """Natural sort key.

    • Digit runs → integers (so '9' < '10').
    • Chinese ordinals (上中下, 一二三…) → their semantic integers
      (so '番外上' < '番外中' < '番外下', '第一' < '第二').
    • Extension stripped before comparison so the base name always sorts
      before any suffix variant:
        '第10集.m4a' < '第10集 新增.m4a'
        '10.m4a'     < '10(1).m4a'
        'extra 01'   < 'extra 01-a'
    """
    dot = s.rfind('.')
    if 0 < dot <= len(s) - 2:   # has a non-empty extension
        s = s[:dot]
    result = []
    for t in _NATURAL_SPLIT.split(s):
        if t.isdigit():
            result.append(int(t))
        elif t in _ZH_NUM:
            result.append(_ZH_NUM[t])
        else:
            result.append(t.lower())
    return result


# test:
# for line in """1.概念PV 1
# 1.  概念PV 1
# 02 第二课时 2
# 03)第15集(上) 3
# 03) 第15集(上) 3
# 4_消息提示音 4
# [5] 番外1 妻管严 5
# [5]番外1 妻管严 5
# 【6】番外 6
# 【6】 番外 6
# 07-概念PV 7
# 07 - 概念PV 7
# 8- 消息提示音 8
# 9 5000w
# ---
# 69小剧场
# 10
# 2026/03/05
# 26/03/05
# 7-12
# 7-12 gyu
# 番外2 弟子.m4a
# chapter 05.m4a
# 小剧场 剑名.m4a""".splitlines():
#     print(_extract_order_num(line))


# _ORDER_PREFIX_RE = re.compile(r"^[\(\[【]?(\d+)[\)\]】]?(?:[.\s_]+|(?:-(?!\d)))+")
_ORDER_PREFIX_RE = re.compile(
    r"""^                         # start
    [\(\[【]?                     # 0 or 1 opening bracket
    (\d+)                        # group 1: number
    (?:                          # exactly 1 separator, not captured
        \s*[\)\]】._]\s*              # normal separator chars
        |                        # or
        \s*-(?!\d)\s*                 # hyphen not followed by digit
        |                        # or
        \s+
    )
    (.+)                         # group 2: any chars until end
    $                            # end
    """,
    re.X,
)


def _extract_order_num(stem: str) -> tuple[int | None, str]:
    """Return (order_number, remaining_title) or (None, stem) if no prefix found."""
    m = _ORDER_PREFIX_RE.match(stem)
    if m:
        # print(f"|{m.group(1)}|{m.group(2)}")
        return int(m.group(1)), m.group(2).strip("_- ") or stem
    return None, stem


def clean_title(p: Path) -> str:
    remove = QSettings("audiobook-maker", "AudiobookMaker").value(
        "remove_order_num", True, type=bool
    )
    num, stripped = _extract_order_num(p.stem)
    if remove and num is not None:
        return stripped
    return p.stem


def fmt_dur(secs: float | None) -> str:
    if secs is None:
        return "—"
    s = int(secs)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def fmt_size(b: int) -> str:
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB"
    return f"{b / 1024:.0f} KB"
