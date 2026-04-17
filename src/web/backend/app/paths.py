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
