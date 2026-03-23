"""要素长期预测数据集：按时间窗口从 processed NetCDF 采样。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

from utils.dataset_utils import (
    build_cumulative_ends,
    build_global_window_starts,
    discover_clean_paths,
    locate_file_index,
    load_norm_stats,
    load_paths_from_manifest,
    project_root,
    slice_across_files,
    standardize_tensor,
)
from data_preprocessing.io import open_nc


def _iter_data_vars(ds: Any) -> list[str]:
    return [str(k) for k in ds.data_vars.keys()]


def _infer_var_names_from_first_file(path: Path) -> tuple[str, ...]:
    ds = open_nc(path)
    try:
        names = _iter_data_vars(ds)
        if not names:
            raise ValueError(f"no data variables in {path}")
        return tuple(names)
    finally:
        ds.close()


def _time_len(ds: Any, var_names: tuple[str, ...]) -> int:
    for name in var_names:
        if name in ds:
            return int(ds[name].shape[0])
    raise ValueError("cannot infer time dimension from configured variables")


class ElementForecastWindowDataset(Dataset):
    """按时间窗构建样本：输入 ``input_steps``，输出 ``output_steps``。"""

    def __init__(
        self,
        processed_dir: str | Path | None = None,
        var_names: tuple[str, ...] | None = ("sst", "sss", "ssu", "ssv"),
        input_steps: int = 12,
        output_steps: int = 12,
        window_stride: int = 1,
        stitch_across_files: bool = True,
        split: str | None = None,
        manifest_path: str | Path | None = None,
        norm_stats_path: str | Path | None = None,
        root: Path | None = None,
    ):
        if input_steps <= 0 or output_steps <= 0:
            raise ValueError("input_steps and output_steps must be > 0")
        if window_stride <= 0:
            raise ValueError("window_stride must be > 0")

        root = root or project_root()
        self.input_steps = input_steps
        self.output_steps = output_steps
        self.window_stride = window_stride
        self.stitch_across_files = stitch_across_files
        self._norm = load_norm_stats(Path(norm_stats_path)) if norm_stats_path else None

        if split is None:
            self.dir = Path(processed_dir or root / "data/processed/element_forecasting")
            self.paths = discover_clean_paths(self.dir)
        else:
            man = (
                Path(manifest_path)
                if manifest_path
                else root / "data/processed/splits/element_forecasting.json"
            )
            self.paths = load_paths_from_manifest(man, split, root)

        if not self.paths:
            raise ValueError("no clean NetCDF files found")

        if var_names is None:
            self.var_names = _infer_var_names_from_first_file(self.paths[0])
        else:
            self.var_names = var_names

        self._file_time_lens: list[int] = []
        for path in self.paths:
            ds = open_nc(path)
            try:
                missing = [v for v in self.var_names if v not in ds]
                if missing:
                    raise KeyError(f"missing vars in {path}: {missing}")
                tlen = _time_len(ds, self.var_names)
            finally:
                ds.close()
            self._file_time_lens.append(tlen)

        self._cum_ends = build_cumulative_ends(self._file_time_lens)
        total = self._cum_ends[-1] if self._cum_ends else 0

        self._windows: list[tuple[Path, int]] = []
        self._global_starts: list[int] = []
        need = self.input_steps + self.output_steps

        if self.stitch_across_files:
            self._global_starts = build_global_window_starts(
                total_len=total,
                input_steps=self.input_steps,
                output_steps=self.output_steps,
                stride=self.window_stride,
            )
            return

        for path, tlen in zip(self.paths, self._file_time_lens):
            if tlen < need:
                continue
            for t0 in range(0, tlen - need + 1, self.window_stride):
                self._windows.append((path, t0))

    def __len__(self) -> int:
        if self.stitch_across_files:
            return len(self._global_starts)
        return len(self._windows)

    def _slice_one_file(self, path: Path, var_name: str, t0: int, t1: int) -> np.ndarray:
        ds = open_nc(path)
        try:
            return np.asarray(ds[var_name].values[t0:t1], dtype=np.float32)
        finally:
            ds.close()

    def _slice_across_files(self, var_name: str, global_t0: int, length: int) -> np.ndarray:
        return slice_across_files(
            paths=self.paths,
            file_lengths=self._file_time_lens,
            cumulative_ends=self._cum_ends,
            global_t0=global_t0,
            length=length,
            read_slice=lambda p, s, e: self._slice_one_file(p, var_name, s, e),
        )

    def __getitem__(self, idx: int) -> dict[str, Any]:
        if self.stitch_across_files:
            t0_global = self._global_starts[idx]
            t_in = self.input_steps
            t_out = self.output_steps
            xs: list[torch.Tensor] = []
            ys: list[torch.Tensor] = []
            for v in self.var_names:
                x_np = self._slice_across_files(v, t0_global, t_in)
                y_np = self._slice_across_files(v, t0_global + t_in, t_out)
                x_t = standardize_tensor(torch.from_numpy(x_np), v, self._norm)
                y_t = standardize_tensor(torch.from_numpy(y_np), v, self._norm)
                xs.append(x_t)
                ys.append(y_t)

            x = torch.stack(xs, dim=1)
            y = torch.stack(ys, dim=1)
            path_idx = locate_file_index(self._cum_ends, t0_global)
            return {
                "x": x,
                "y": y,
                "path": str(self.paths[path_idx]),
                "t0": t0_global,
                "var_names": self.var_names,
            }

        path, t0 = self._windows[idx]
        ds = open_nc(path)
        try:
            xs: list[torch.Tensor] = []
            ys: list[torch.Tensor] = []
            for v in self.var_names:
                arr = np.asarray(ds[v].values, dtype=np.float32)
                x_np = arr[t0 : t0 + self.input_steps]
                y_np = arr[t0 + self.input_steps : t0 + self.input_steps + self.output_steps]
                x_t = standardize_tensor(torch.from_numpy(x_np), v, self._norm)
                y_t = standardize_tensor(torch.from_numpy(y_np), v, self._norm)
                xs.append(x_t)
                ys.append(y_t)

            x = torch.stack(xs, dim=1)
            y = torch.stack(ys, dim=1)
            return {
                "x": x,
                "y": y,
                "path": str(path),
                "t0": t0,
                "var_names": self.var_names,
            }
        finally:
            ds.close()


# 兼容旧导出名，避免外部调用断裂。
ElementForecastCleanDataset = ElementForecastWindowDataset
