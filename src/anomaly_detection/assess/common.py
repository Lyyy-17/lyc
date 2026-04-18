"""异常评估子命令共用：路径解析与 YAML 加载。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def resolve_path(path_like: str | Path | None, *, root: Path, default: Path) -> Path:
    if path_like is None:
        return default
    p = Path(path_like)
    return p if p.is_absolute() else (root / p)


def read_path_txt(root: Path, path_txt_rel: str) -> str:
    path_txt = root / path_txt_rel
    if not path_txt.is_file():
        return ""
    try:
        return path_txt.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def resolve_anomaly_processed_dir(
    root: Path,
    raw_value: str | Path | None,
    *,
    default_rel: str,
    default_path: Path,
) -> Path:
    default_rel_posix = default_rel.replace("\\", "/")
    raw_text = "" if raw_value is None else str(raw_value).strip()
    use_path_txt = raw_text in {"", default_rel, default_rel_posix}
    if use_path_txt:
        path_txt_value = read_path_txt(root, "data/processed/anomaly_detection/path.txt")
        if path_txt_value:
            return resolve_path(path_txt_value, root=root, default=default_path)
    return resolve_path(raw_value, root=root, default=default_path)
