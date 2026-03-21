"""涡旋任务：从 `data/processed/eddy_detection` 读取清洗后 NetCDF。

使用前请先运行 `python scripts/02_preprocess.py`；可选 `--steps clean,split,stats`。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

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
