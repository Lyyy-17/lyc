"""供各任务模块 Dataset 复用：划分清单、标准化 JSON、张量标准化。

从本文件导入即可，例如 ``from utils.dataset_utils import project_root, load_paths_from_manifest``。
"""
from __future__ import annotations

import json
from pathlib import Path

import torch


def project_root() -> Path:
    """项目根目录（含 `data/`、`src/`）。"""
    return Path(__file__).resolve().parents[2]


def load_paths_from_manifest(manifest_path: Path, split: str, root: Path) -> list[Path]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if split not in data:
        raise KeyError(f"split {split!r} not in {manifest_path}")
    return [root / Path(r) for r in data[split]]


def load_norm_stats(path: Path) -> dict[str, tuple[float, float]]:
    j = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, tuple[float, float]] = {}
    for k, v in j.get("variables", {}).items():
        out[k] = (float(v["mean"]), float(v["std"]))
    return out


def standardize_tensor(
    t: torch.Tensor,
    key: str,
    norm: dict[str, tuple[float, float]] | None,
) -> torch.Tensor:
    if norm is None or key not in norm:
        return t
    m, s = norm[key]
    return (t - m) / s
