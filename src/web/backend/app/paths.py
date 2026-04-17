"""项目根路径与相对路径解析（供 Web 后端各模块复用）。"""
from __future__ import annotations

import os
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = str(_APP_DIR.parent.parent.parent.parent)


def resolve_path(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.join(PROJECT_ROOT, p)


def read_path_txt(path_txt_rel: str) -> str:
    path_txt = resolve_path(path_txt_rel)
    if not os.path.exists(path_txt):
        return ""
    try:
        with open(path_txt, "r", encoding="utf-8") as f:
            return str(f.read().strip())
    except Exception:
        return ""


def resolve_data_path_or_path_txt(raw_path: str) -> str:
    """Resolve data path; if input is a path.txt, read target path from it."""
    s = str(raw_path or "").strip().strip('"\'')
    if not s:
        return resolve_path(s)

    abs_input = resolve_path(s)
    if s.endswith("path.txt") or abs_input.endswith("path.txt"):
        target = read_path_txt(s)
        if target:
            return resolve_path(target)
    return abs_input
