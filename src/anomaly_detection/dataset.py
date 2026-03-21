"""风-浪异常：从 `data/processed/anomaly_detection` 读取各年 `oper_clean` + `wave_clean`。

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


class AnomalyCleanDataset(Dataset):
    """每年目录下 oper_clean + wave_clean，返回 oper / wave 两组张量。"""

    def __init__(
        self,
        processed_anomaly_dir: str | Path | None = None,
        split: str | None = None,
        manifest_path: str | Path | None = None,
        norm_stats_path: str | Path | None = None,
        root: Path | None = None,
    ):
        root = root or project_root()
        self._norm = load_norm_stats(Path(norm_stats_path)) if norm_stats_path else None
        if split is None:
            base = Path(processed_anomaly_dir or root / "data/processed/anomaly_detection")
            self.pairs: list[tuple[Path, Path]] = []
            for ydir in sorted(d for d in base.iterdir() if d.is_dir()):
                op = ydir / "oper_clean.nc"
                wv = ydir / "wave_clean.nc"
                if op.is_file() and wv.is_file():
                    self.pairs.append((op, wv))
        else:
            man = (
                Path(manifest_path)
                if manifest_path
                else root / "data/processed/splits/anomaly_detection.json"
            )
            dirs = load_paths_from_manifest(man, split, root)
            self.pairs = []
            for ydir in dirs:
                op, wv = ydir / "oper_clean.nc", ydir / "wave_clean.nc"
                if op.is_file() and wv.is_file():
                    self.pairs.append((op, wv))

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        op, wv = self.pairs[idx]
        ds_o = open_nc(op)
        ds_w = open_nc(wv)
        try:
            oper_keys = ("u10", "v10", "wind_speed")
            oper: dict[str, torch.Tensor] = {}
            for k in oper_keys:
                if k in ds_o:
                    t = torch.from_numpy(np.asarray(ds_o[k].values, dtype=np.float32))
                    oper[k] = standardize_tensor(t, k, self._norm)
            wave: dict[str, torch.Tensor] = {}
            for k in ("swh", "mwp", "mwd"):
                if k in ds_w:
                    t = torch.from_numpy(np.asarray(ds_w[k].values, dtype=np.float32))
                    wave[k] = standardize_tensor(t, k, self._norm)
            return {
                "oper": oper,
                "wave": wave,
                "paths": (str(op), str(wv)),
            }
        finally:
            ds_o.close()
            ds_w.close()
