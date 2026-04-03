"""要素长期预测数据集：基于单个合并 NetCDF 的时间窗口采样。"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import Dataset

from utils.dataset_utils import (
    load_norm_stats,
    project_root,
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


def _to_bool_valid(values: np.ndarray, valid: np.ndarray | None = None) -> np.ndarray:
    finite = np.isfinite(values)
    if valid is None:
        return finite
    vm = np.asarray(valid, dtype=np.float32) > 0.5
    return finite & vm


def _sanitize_values(values: np.ndarray, valid_bool: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    arr = np.where(valid_bool, arr, 0.0)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


class ElementForecastWindowDataset(Dataset):
    """按时间窗构建样本：输入 ``input_steps``，输出 ``output_steps``。"""

    def __init__(
        self,
        data_file: str | Path | None = None,
        var_names: tuple[str, ...] | None = ("sst", "sss", "ssu", "ssv"),
        input_steps: int = 12,
        output_steps: int = 12,
        window_stride: int = 1,
        open_file_lru_size: int = 16,
        split: str | None = None,
        split_ratios: tuple[float, float, float] = (0.7, 0.15, 0.15),
        norm_stats_path: str | Path | None = None,
        root: Path | None = None,
    ):
        if input_steps <= 0 or output_steps <= 0:
            raise ValueError("input_steps and output_steps must be > 0")
        if window_stride <= 0:
            raise ValueError("window_stride must be > 0")
        if len(split_ratios) != 3:
            raise ValueError("split_ratios must be (train_ratio, val_ratio, test_ratio)")

        train_ratio, val_ratio, test_ratio = [float(x) for x in split_ratios]
        ratio_sum = train_ratio + val_ratio + test_ratio
        if ratio_sum <= 0:
            raise ValueError("split ratios sum must be > 0")
        train_ratio, val_ratio, test_ratio = (
            train_ratio / ratio_sum,
            val_ratio / ratio_sum,
            test_ratio / ratio_sum,
        )

        root = root or project_root()
        self.input_steps = input_steps
        self.output_steps = output_steps
        self.window_stride = window_stride
        self._norm = load_norm_stats(Path(norm_stats_path)) if norm_stats_path else None
        self.split = split
        self._split_ratios = (train_ratio, val_ratio, test_ratio)
        # 兼容旧参数名，仅复用 1 个文件句柄。
        self._open_ds_lru: OrderedDict[Path, Any] = OrderedDict()
        self._max_open_files = max(1, min(2, int(open_file_lru_size)))

        self.path = Path(data_file or root / "data/processed/element_forecasting/path.txt")
        if not self.path.is_absolute():
            self.path = root / self.path
            
        if self.path.suffix == ".txt" and self.path.is_file():
            actual_path_str = self.path.read_text(encoding="utf-8").strip()
            self.path = Path(actual_path_str)
            if not self.path.is_absolute():
                self.path = root / self.path

        if not self.path.is_file():
            raise FileNotFoundError(f"dataset file not found: {self.path}")

        if var_names is None:
            self.var_names = _infer_var_names_from_first_file(self.path)
        else:
            self.var_names = var_names

        ds = open_nc(self.path)
        try:
            missing = [v for v in self.var_names if v not in ds]
            if missing:
                raise KeyError(f"missing vars in {self.path}: {missing}")
            total = _time_len(ds, self.var_names)
        finally:
            ds.close()

        self._windows: list[int] = []
        need = self.input_steps + self.output_steps

        total_windows = max(0, (total - need) // self.window_stride + 1)
        if total_windows <= 0:
            return

        all_starts = [i * self.window_stride for i in range(total_windows)]
        train_end = int(total_windows * train_ratio)
        val_end = train_end + int(total_windows * val_ratio)

        if split == "train":
            self._windows = all_starts[:train_end]
        elif split == "val":
            self._windows = all_starts[train_end:val_end]
        elif split == "test":
            self._windows = all_starts[val_end:]
        elif split is None:
            self._windows = all_starts
        else:
            raise ValueError(f"invalid split: {split!r}, expected train/val/test/None")

    def __len__(self) -> int:
        return len(self._windows)

    def _get_open_ds(self, path: Path) -> Any:
        ds = self._open_ds_lru.get(path)
        if ds is not None:
            self._open_ds_lru.move_to_end(path)
            return ds
        ds = open_nc(path)
        self._open_ds_lru[path] = ds
        self._open_ds_lru.move_to_end(path)
        while len(self._open_ds_lru) > self._max_open_files:
            _, evicted = self._open_ds_lru.popitem(last=False)
            evicted.close()
        return ds

    def _close_all_open_ds(self) -> None:
        while self._open_ds_lru:
            _, ds = self._open_ds_lru.popitem(last=False)
            ds.close()

    def __del__(self) -> None:
        try:
            self._close_all_open_ds()
        except Exception:
            # 避免析构阶段异常影响进程退出
            pass

    def _read_multi_var_pairs(self, ds: Any, t0: int, t1: int) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
        """一次时间切片读取该片段的全部变量，减少小文件随机访问开销。"""
        chunk = ds.isel(time=slice(t0, t1))
        values: dict[str, np.ndarray] = {}
        valids: dict[str, np.ndarray] = {}
        for var_name in self.var_names:
            raw = np.asarray(chunk[var_name].values, dtype=np.float32)
            valid_name = f"{var_name}_valid"
            valid = np.asarray(chunk[valid_name].values, dtype=np.float32) if valid_name in chunk else None
            valid_bool = _to_bool_valid(raw, valid)
            values[var_name] = _sanitize_values(raw, valid_bool)
            valids[var_name] = valid_bool.astype(np.float32)
        return values, valids

    def __getitem__(self, idx: int) -> dict[str, Any]:
        t0 = self._windows[idx]
        ds = self._get_open_ds(self.path)
        values, valids = self._read_multi_var_pairs(ds, t0, t0 + self.input_steps + self.output_steps)
        xs: list[torch.Tensor] = []
        ys: list[torch.Tensor] = []
        y_valids: list[torch.Tensor] = []
        for v in self.var_names:
            whole = values[v]
            whole_valid = valids[v]
            x_np = whole[: self.input_steps]
            y_np = whole[self.input_steps : self.input_steps + self.output_steps]
            x_t = standardize_tensor(torch.from_numpy(x_np), v, self._norm)
            y_t = standardize_tensor(torch.from_numpy(y_np), v, self._norm)
            xs.append(x_t)
            ys.append(y_t)

            y_valid_np = whole_valid[self.input_steps : self.input_steps + self.output_steps]
            y_valids.append(torch.from_numpy(y_valid_np).to(dtype=torch.float32))

        x = torch.stack(xs, dim=1)
        y = torch.stack(ys, dim=1)
        x = torch.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
        y = torch.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
        y_valid = torch.stack(y_valids, dim=1)
        return {
            "x": x,
            "y": y,
            "y_valid": y_valid,
            "path": str(self.path),
            "t0": t0,
            "var_names": self.var_names,
        }


# 兼容旧导出名，避免外部调用断裂。
ElementForecastCleanDataset = ElementForecastWindowDataset
