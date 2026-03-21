"""数据集划分与基于训练集的均值/方差（标准化参数）估计。"""
from __future__ import annotations

import json
import logging
import math
import random
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from tqdm import tqdm

from data_preprocessing.io import open_nc

_log = logging.getLogger(__name__)

TASK_EDDY = "eddy"
TASK_ELEMENT = "element_forecasting"
TASK_ANOMALY = "anomaly_detection"


def _rel(p: Path, root: Path) -> str:
    return p.resolve().relative_to(root.resolve()).as_posix()


def list_processed_eddy(cfg: Mapping[str, Any], root: Path) -> list[Path]:
    d = root / cfg["paths"]["processed"]["eddy"]
    return sorted(d.glob("*_clean.nc"))


def list_processed_element(cfg: Mapping[str, Any], root: Path) -> list[Path]:
    d = root / cfg["paths"]["processed"]["element_forecasting"]
    return sorted(d.glob("*_clean.nc"))


def list_processed_anomaly(cfg: Mapping[str, Any], root: Path) -> list[Path]:
    base = root / cfg["paths"]["processed"]["anomaly"]
    out: list[Path] = []
    for ydir in sorted(d for d in base.iterdir() if d.is_dir()):
        if (ydir / "oper_clean.nc").is_file() and (ydir / "wave_clean.nc").is_file():
            out.append(ydir)
    return out


def list_processed_samples(task: str, cfg: Mapping[str, Any], root: Path) -> list[Path]:
    if task == TASK_EDDY:
        return list_processed_eddy(cfg, root)
    if task == TASK_ELEMENT:
        return list_processed_element(cfg, root)
    if task == TASK_ANOMALY:
        return list_processed_anomaly(cfg, root)
    raise ValueError(f"unknown task: {task}")


def split_train_val_test(
    items: list[Any],
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> tuple[list[Any], list[Any], list[Any]]:
    s = float(train_ratio) + float(val_ratio) + float(test_ratio)
    if not math.isclose(s, 1.0, rel_tol=1e-5):
        raise ValueError(f"split ratios must sum to 1.0, got {s}")
    n = len(items)
    if n == 0:
        return [], [], []
    idx = list(range(n))
    rng = random.Random(seed)
    rng.shuffle(idx)
    n_tr = int(round(train_ratio * n))
    n_va = int(round(val_ratio * n))
    n_te = n - n_tr - n_va
    while n_tr + n_va + n_te > n and n_te > 0:
        n_te -= 1
    while n_tr + n_va + n_te > n and n_va > 0:
        n_va -= 1
    while n_tr + n_va + n_te > n and n_tr > 1:
        n_tr -= 1
    while n_tr + n_va + n_te < n:
        n_tr += 1
    if n_tr < 1:
        n_tr = 1
        n_va = min(n_va, max(0, n - n_tr - n_te))
    i_tr = idx[:n_tr]
    i_va = idx[n_tr : n_tr + n_va]
    i_te = idx[n_tr + n_va : n_tr + n_va + n_te]
    tr = [items[i] for i in i_tr]
    va = [items[i] for i in i_va]
    te = [items[i] for i in i_te]
    return tr, va, te


def write_split_manifest(
    task: str,
    train: list[Path],
    val: list[Path],
    test: list[Path],
    root: Path,
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{task}.json" if task != TASK_ANOMALY else "anomaly_detection.json"
    path = out_dir / name
    data = {
        "task": task,
        "train": [_rel(p, root) for p in train],
        "val": [_rel(p, root) for p in val],
        "test": [_rel(p, root) for p in test],
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _masked_values(da: Any, valid_da: Any | None) -> np.ndarray:
    arr = np.asarray(da.values, dtype=np.float64).ravel()
    if valid_da is not None:
        m = np.asarray(valid_da.values, dtype=np.float64).ravel() > 0
    else:
        m = np.isfinite(arr)
    return arr[m]


def _accumulate(arr: np.ndarray, state: tuple[float, float, int]) -> tuple[float, float, int]:
    s, ss, c = state
    if arr.size == 0:
        return s, ss, c
    s = s + float(np.nansum(arr))
    ss = ss + float(np.nansum(arr * arr))
    c = c + int(np.sum(np.isfinite(arr)))
    return s, ss, c


def compute_train_standardization(
    task: str,
    train_rel_paths: list[str],
    root: Path,
) -> dict[str, dict[str, float]]:
    """仅用训练集路径估计每变量 mean/std（有效像素上）。"""
    if not train_rel_paths:
        raise ValueError("train split is empty; cannot compute standardization")

    if task == TASK_EDDY:
        vars_ = ("adt", "ugos", "vgos")
    elif task == TASK_ELEMENT:
        vars_ = ("sst", "sss", "ssu", "ssv")
    elif task == TASK_ANOMALY:
        vars_ = ("u10", "v10", "wind_speed", "swh", "mwp", "mwd")
    else:
        raise ValueError(f"unknown task: {task}")

    acc: dict[str, tuple[float, float, int]] = {v: (0.0, 0.0, 0) for v in vars_}

    for rel in tqdm(train_rel_paths, desc=f"stats {task}", unit="sample"):
        if task == TASK_ANOMALY:
            ydir = root / rel
            op = ydir / "oper_clean.nc"
            wv = ydir / "wave_clean.nc"
            ds_o = open_nc(op)
            ds_w = open_nc(wv)
            try:
                for name in ("u10", "v10", "wind_speed"):
                    if name not in ds_o:
                        continue
                    da = ds_o[name]
                    vd = ds_o.get(f"{name}_valid")
                    arr = _masked_values(da, vd)
                    acc[name] = _accumulate(arr, acc[name])
                for name in ("swh", "mwp", "mwd"):
                    if name not in ds_w:
                        continue
                    da = ds_w[name]
                    vd = ds_w.get(f"{name}_valid")
                    arr = _masked_values(da, vd)
                    acc[name] = _accumulate(arr, acc[name])
            finally:
                ds_o.close()
                ds_w.close()
        else:
            p = root / rel
            ds = open_nc(p)
            try:
                for name in vars_:
                    if name not in ds:
                        continue
                    da = ds[name]
                    vd = ds.get(f"{name}_valid")
                    arr = _masked_values(da, vd)
                    acc[name] = _accumulate(arr, acc[name])
            finally:
                ds.close()

    out: dict[str, dict[str, float]] = {}
    for name, (s, ss, c) in acc.items():
        if c == 0:
            continue
        mean = s / c
        var = max(0.0, ss / c - mean * mean)
        std = math.sqrt(var)
        if std < 1e-12:
            std = 1.0
        out[name] = {"mean": mean, "std": std}
    return out


def write_standardization_json(
    task: str,
    variables: dict[str, dict[str, float]],
    root: Path,
    norm_dir: Path,
) -> Path:
    norm_dir.mkdir(parents=True, exist_ok=True)
    name = f"{task}_norm.json" if task != TASK_ANOMALY else "anomaly_detection_norm.json"
    path = norm_dir / name
    payload = {"task": task, "variables": variables}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def run_split_for_task(
    task: str,
    cfg: Mapping[str, Any],
    root: Path,
) -> Path:
    sp = cfg.get("split", {})
    tr = float(sp.get("train_ratio", 0.7))
    va = float(sp.get("val_ratio", 0.15))
    te = float(sp.get("test_ratio", 0.15))
    seed = int(sp.get("seed", 42))
    samples = list_processed_samples(task, cfg, root)
    train, val, test = split_train_val_test(samples, tr, va, te, seed)
    out_dir = root / cfg["paths"]["splits"]
    path = write_split_manifest(task, train, val, test, root, out_dir)
    _log.info(
        "split %s: train=%s val=%s test=%s -> %s",
        task,
        len(train),
        len(val),
        len(test),
        path.relative_to(root),
    )
    return path


def run_standardization_for_task(
    task: str,
    cfg: Mapping[str, Any],
    root: Path,
) -> Path | None:
    split_dir = root / cfg["paths"]["splits"]
    name = f"{task}.json" if task != TASK_ANOMALY else "anomaly_detection.json"
    man_path = split_dir / name
    if not man_path.is_file():
        _log.warning("skip stats: missing manifest %s", man_path.relative_to(root))
        return None
    data = json.loads(man_path.read_text(encoding="utf-8"))
    train_rel = data.get("train", [])
    variables = compute_train_standardization(task, train_rel, root)
    norm_dir = root / cfg["paths"]["normalization"]
    out = write_standardization_json(task, variables, root, norm_dir)
    _log.info("norm %s (%s vars) -> %s", task, len(variables), out.relative_to(root))
    return out
