"""涡旋任务：从 `data/processed/eddy_detection` 读取清洗后 NetCDF。

使用前请先运行 `python scripts/02_preprocess.py`；可选 `--steps clean,split,stats`。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import random

import numpy as np
import torch
from torch.utils.data import Dataset

from utils.dataset_utils import (
    load_norm_stats,
    load_paths_from_manifest,
    project_root,
    standardize_tensor,
)
from data_preprocessing.io import open_nc


class EddyCleanDataset(Dataset):
    """eddy_detection 清洗文件：按文件样本，张量形状多为 `(time, lat, lon)`。"""

    def __init__(
        self,
        processed_dir: str | Path | None = None,
        var_names: tuple[str, ...] = ("adt", "ugos", "vgos"),
        split: str | None = None,
        manifest_path: str | Path | None = None,
        norm_stats_path: str | Path | None = None,
        root: Path | None = None,
    ):
        root = root or project_root()
        self.var_names = var_names
        self._norm = load_norm_stats(Path(norm_stats_path)) if norm_stats_path else None
        if split is None:
            self.dir = Path(processed_dir or root / "data/processed/eddy_detection")
            self.paths = sorted(self.dir.glob("*_clean.nc"))
        else:
            man = Path(manifest_path) if manifest_path else root / "data/processed/splits/eddy.json"
            self.paths = load_paths_from_manifest(man, split, root)

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        path = self.paths[idx]
        ds = open_nc(path)
        try:
            out: dict[str, Any] = {"path": str(path)}
            for v in self.var_names:
                if v in ds:
                    t = torch.from_numpy(np.asarray(ds[v].values, dtype=np.float32))
                    out[v] = standardize_tensor(t, v, self._norm)
            return out
        finally:
            ds.close()


@dataclass(frozen=True)
class EddyLabelConfig:
    """监督训练标签配置。"""

    label_dir: Path
    task_type: str = "binary"  # binary | multiclass
    time_window: int = 1


def _to_date_key(time_value: Any, fallback_idx: int) -> str:
    """将 time 值转换为 YYYYMMDD；无法解析时退化为索引。"""

    try:
        # np.datetime64 -> YYYY-MM-DD
        ts = np.datetime_as_string(np.asarray(time_value, dtype="datetime64[ns]"), unit="D")
        return ts.replace("-", "")
    except (TypeError, ValueError):
        return f"idx_{fallback_idx:07d}"


def build_daily_index(paths: list[Path], var_names: tuple[str, ...]) -> list[dict[str, Any]]:
    """把按文件序列展开为按天样本索引。"""

    out: list[dict[str, Any]] = []
    for p in paths:
        ds = open_nc(p)
        try:
            missing = [v for v in var_names if v not in ds]
            if missing:
                raise KeyError(f"missing vars {missing} in {p}")

            if "time" in ds.coords:
                times = np.asarray(ds["time"].values)
                n_time = int(times.shape[0])
            else:
                n_time = int(np.asarray(ds[var_names[0]].values).shape[0])
                times = np.arange(n_time)

            for t in range(n_time):
                out.append(
                    {
                        "path": p,
                        "time_index": t,
                        "date_key": _to_date_key(times[t], t),
                        "source_stem": p.stem,
                    }
                )
        finally:
            ds.close()
    return out


def load_label(path: Path, date_key: str, task_type: str) -> torch.Tensor:
    """加载单日标签，支持 `npy` 或 `npz`。"""

    if not path.is_file():
        raise FileNotFoundError(f"label file not found: {path}")

    if path.suffix == ".npy":
        arr = np.load(path)
    elif path.suffix == ".npz":
        npz = np.load(path)
        if date_key in npz:
            arr = npz[date_key]
        elif "mask" in npz:
            arr = npz["mask"]
        else:
            keys = list(npz.keys())
            raise KeyError(f"cannot find key {date_key!r} or 'mask' in {path}, keys={keys}")
    else:
        raise ValueError(f"unsupported label suffix: {path.suffix}")

    t = torch.from_numpy(np.asarray(arr))
    if task_type == "multiclass":
        return t.long()
    if task_type == "binary":
        # 统一转为 0/1 浮点标签
        return (t > 0).float()
    raise ValueError(f"unsupported task_type: {task_type}")


class EddySegDataset(Dataset):
    """eddy_detection 监督分割数据集：按天返回 x/y。"""

    def __init__(
        self,
        processed_dir: str | Path | None = None,
        var_names: tuple[str, ...] = ("adt", "ugos", "vgos"),
        split: str | None = None,
        manifest_path: str | Path | None = None,
        norm_stats_path: str | Path | None = None,
        label_cfg: EddyLabelConfig | None = None,
        augment: bool = False,
        root: Path | None = None,
    ):
        root = root or project_root()
        self.var_names = var_names
        self.augment = augment
        self._norm = load_norm_stats(Path(norm_stats_path)) if norm_stats_path else None
        self.label_cfg = label_cfg

        if split is None:
            self.dir = Path(processed_dir or root / "data/processed/eddy_detection")
            self.paths = sorted(self.dir.glob("*_clean.nc"))
        else:
            man = Path(manifest_path) if manifest_path else root / "data/processed/splits/eddy.json"
            self.paths = load_paths_from_manifest(man, split, root)

        self.samples = build_daily_index(self.paths, self.var_names)

    def __len__(self) -> int:
        return len(self.samples)

    def _resolve_label_path(self, sample: dict[str, Any]) -> Path:
        if self.label_cfg is None:
            raise ValueError("label_cfg is required for supervised EddySegDataset")

        base = self.label_cfg.label_dir
        date_key = str(sample["date_key"])
        source_stem = str(sample["source_stem"])

        candidates = [
            base / f"{date_key}.npy",
            base / f"{date_key}.npz",
            base / source_stem / f"{date_key}.npy",
            base / source_stem / f"{date_key}.npz",
            base / f"{source_stem}_{date_key}.npy",
            base / f"{source_stem}_{date_key}.npz",
        ]
        for c in candidates:
            if c.is_file():
                return c
        raise FileNotFoundError(
            f"cannot resolve label file for date={date_key}, source={source_stem} under {base}"
        )

    def _apply_aug(self, x: torch.Tensor, y: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if not self.augment:
            return x, y
        # 保持几何一致性，仅做不改变尺度的增强
        if random.random() < 0.5:
            x = torch.flip(x, dims=[-1])
            y = torch.flip(y, dims=[-1])
        if random.random() < 0.5:
            x = torch.flip(x, dims=[-2])
            y = torch.flip(y, dims=[-2])
        # 当前网格常为 160x320，90/270 度旋转会导致 H/W 交换，影响 batch 堆叠。
        k = random.choice([0, 2])
        if k:
            x = torch.rot90(x, k=k, dims=[-2, -1])
            y = torch.rot90(y, k=k, dims=[-2, -1])
        return x, y

    def __getitem__(self, idx: int) -> dict[str, Any]:
        sample = self.samples[idx]
        path = Path(sample["path"])
        t = int(sample["time_index"])

        ds = open_nc(path)
        try:
            channels: list[torch.Tensor] = []
            for v in self.var_names:
                arr = np.asarray(ds[v].values[t], dtype=np.float32)
                tv = standardize_tensor(torch.from_numpy(arr), v, self._norm)
                channels.append(tv)
            x = torch.stack(channels, dim=0)
        finally:
            ds.close()

        y: torch.Tensor | None = None
        if self.label_cfg is not None:
            lp = self._resolve_label_path(sample)
            y = load_label(lp, str(sample["date_key"]), self.label_cfg.task_type)
            if y.ndim == 2:
                y = y.unsqueeze(0) if self.label_cfg.task_type == "binary" else y
            elif y.ndim == 3 and self.label_cfg.task_type == "multiclass":
                # (1, H, W) -> (H, W)
                if y.shape[0] == 1:
                    y = y[0]
                else:
                    raise ValueError("multiclass label expects shape (H, W) or (1, H, W)")
            elif y.ndim != 3:
                raise ValueError(f"unsupported label shape: {tuple(y.shape)}")

            x, y = self._apply_aug(x, y)
            if self.label_cfg.task_type == "binary":
                y = y.float()
            else:
                y = y.long()

        out: dict[str, Any] = {
            "x": x.float(),
            "path": str(path),
            "time_index": t,
            "date_key": str(sample["date_key"]),
        }
        if y is not None:
            out["y"] = y
        return out
