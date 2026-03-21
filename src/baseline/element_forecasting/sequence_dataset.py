"""从 element 清洗 NetCDF 构造 (历史帧, 未来帧) 序列样本。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

from data_preprocessing.io import open_nc
from utils.dataset_utils import (
    load_norm_stats,
    load_paths_from_manifest,
    project_root,
    standardize_tensor,
)


def _time_len(ds: Any, var_names: tuple[str, ...]) -> int:
    for v in var_names:
        if v in ds:
            return int(ds[v].shape[0])
    raise ValueError("no variable found for time length")


class ElementForecastSequenceDataset(Dataset):
    """
    每个样本为一段连续时间窗：输入 ``input_len`` 帧，目标 ``forecast_len`` 帧。

    在 ``__init__`` 中扫描所有文件的时间长度并建立 ``(文件, t0)`` 索引。
    """

    def __init__(
        self,
        split: str,
        input_len: int = 12,
        forecast_len: int = 12,
        window_stride: int = 1,
        var_names: tuple[str, ...] = ("sst", "sss", "ssu", "ssv"),
        manifest_path: str | Path | None = None,
        norm_stats_path: str | Path | None = None,
        root: Path | None = None,
    ) -> None:
        super().__init__()
        self.input_len = input_len
        self.forecast_len = forecast_len
        self.var_names = var_names
        root = root or project_root()
        man = (
            Path(manifest_path)
            if manifest_path
            else root / "data/processed/splits/element_forecasting.json"
        )
        self.paths = load_paths_from_manifest(man, split, root)
        self._norm = load_norm_stats(Path(norm_stats_path)) if norm_stats_path else None

        self._windows: list[tuple[Path, int]] = []
        need = input_len + forecast_len
        for p in self.paths:
            ds = open_nc(p)
            try:
                tlen = _time_len(ds, var_names)
            finally:
                ds.close()
            if tlen < need:
                continue
            for t0 in range(0, tlen - need + 1, window_stride):
                self._windows.append((p, t0))

    def __len__(self) -> int:
        return len(self._windows)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        path, t0 = self._windows[idx]
        ds = open_nc(path)
        try:
            t_in = self.input_len
            t_out = self.forecast_len
            xs: list[torch.Tensor] = []
            ys: list[torch.Tensor] = []
            for v in self.var_names:
                if v not in ds:
                    continue
                arr = np.asarray(ds[v].values, dtype=np.float32)
                x_np = arr[t0 : t0 + t_in]
                y_np = arr[t0 + t_in : t0 + t_in + t_out]
                xv = torch.from_numpy(x_np)
                yv = torch.from_numpy(y_np)
                xs.append(standardize_tensor(xv, v, self._norm))
                ys.append(standardize_tensor(yv, v, self._norm))
            if not xs:
                raise RuntimeError(f"no variables in {path}")
            x = torch.stack(xs, dim=1)
            y = torch.stack(ys, dim=1)
            return {"x": x, "y": y, "path": str(path)}
        finally:
            ds.close()
