"""清洗后数据质量检查：变量完整性、时间维单调、有效格点比例、划分清单路径存在性。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import xarray as xr

from data_preprocessing.io import open_nc
from data_preprocessing.splitter import (
    TASK_ANOMALY,
    TASK_EDDY,
    TASK_ELEMENT,
    list_processed_samples,
)

_log = logging.getLogger(__name__)


def _finite_ratio_masked(da: xr.DataArray, valid: xr.DataArray | None) -> float:
    arr = np.asarray(da.values, dtype=np.float64).ravel()
    if valid is not None:
        m = np.asarray(valid.values, dtype=np.float64).ravel() > 0.5
        if not m.any():
            return 0.0
        sub = arr[m]
        return float(np.sum(np.isfinite(sub)) / max(sub.size, 1))
    return float(np.mean(np.isfinite(arr)))


def _time_coord_issues(ds: xr.Dataset) -> list[str]:
    issues: list[str] = []
    for tn in ("time", "valid_time"):
        if tn not in ds.coords:
            continue
        t = np.asarray(ds.coords[tn].values, dtype=np.float64).ravel()
        if t.size < 2:
            return issues
        dt = np.diff(t)
        if np.any(dt <= 0):
            issues.append(f"坐标 {tn} 非严格递增（存在重复或乱序）")
        return issues
    return issues


def validate_eddy_nc(path: Path) -> list[str]:
    """检查涡旋 ``*_clean.nc``；返回问题列表，空表示通过。"""
    issues: list[str] = []
    ds = open_nc(path)
    try:
        for name in ("adt", "ugos", "vgos"):
            if name not in ds:
                issues.append(f"缺少变量 {name}")
                continue
            vm = f"{name}_valid"
            if vm not in ds:
                issues.append(f"缺少掩膜 {vm}")
                continue
            fr = _finite_ratio_masked(ds[name], ds[vm])
            if fr < 0.01:
                issues.append(f"{name} 有效点上有限值比例过低 ({fr:.4f})")
        issues.extend(_time_coord_issues(ds))
        return issues
    finally:
        ds.close()


def validate_element_nc(path: Path) -> list[str]:
    """检查要素 ``*_clean.nc``。"""
    issues: list[str] = []
    ds = open_nc(path)
    try:
        for name in ("sst", "sss", "ssu", "ssv"):
            if name not in ds:
                issues.append(f"缺少变量 {name}")
                continue
            vm = f"{name}_valid"
            if vm not in ds:
                issues.append(f"缺少掩膜 {vm}")
                continue
            fr = _finite_ratio_masked(ds[name], ds[vm])
            if fr < 0.01:
                issues.append(f"{name} 有效点上有限值比例过低 ({fr:.4f})")
        issues.extend(_time_coord_issues(ds))
        return issues
    finally:
        ds.close()


def _validate_anomaly_single(path: Path, kind: str) -> list[str]:
    issues: list[str] = []
    ds = open_nc(path)
    try:
        if kind == "oper":
            for name in ("u10", "v10"):
                if name not in ds:
                    issues.append(f"oper 缺少 {name}")
                else:
                    vm = f"{name}_valid"
                    if vm not in ds:
                        issues.append(f"oper 缺少 {vm}")
        else:
            for name in ("swh", "mwp", "mwd"):
                if name not in ds:
                    issues.append(f"wave 缺少 {name}")
                else:
                    vm = f"{name}_valid"
                    if vm not in ds:
                        issues.append(f"wave 缺少 {vm}")
        issues.extend(_time_coord_issues(ds))
        return issues
    finally:
        ds.close()


def validate_anomaly_year_dir(year_dir: Path) -> list[str]:
    """检查某年目录下 ``oper_clean.nc`` 与 ``wave_clean.nc``。"""
    op = year_dir / "oper_clean.nc"
    wv = year_dir / "wave_clean.nc"
    issues: list[str] = []
    if not op.is_file():
        issues.append(f"缺少 {op.name}")
    if not wv.is_file():
        issues.append(f"缺少 {wv.name}")
    if issues:
        return issues
    issues.extend(_validate_anomaly_single(op, "oper"))
    issues.extend(_validate_anomaly_single(wv, "wave"))
    return issues


def validate_split_manifest(manifest_path: Path, root: Path) -> list[str]:
    """检查划分 JSON 中列出的路径是否均存在（相对 ``root``）。"""
    issues: list[str] = []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = root.resolve()
    for split_name in ("train", "val", "test"):
        rels = data.get(split_name, [])
        for r in rels:
            p = root / r
            if p.is_file():
                continue
            if p.is_dir() and (p / "oper_clean.nc").is_file():
                continue
            issues.append(f"{split_name}: 不存在 {r}")
    return issues


@dataclass
class ValidationSummary:
    """``run_validation_for_task`` 汇总结果。"""

    task: str
    checked: int = 0
    failed: int = 0
    messages: list[str] = field(default_factory=list)


def _validate_one_sample(task: str, sample: Path) -> list[str]:
    if task == TASK_EDDY:
        return validate_eddy_nc(sample)
    if task == TASK_ELEMENT:
        return validate_element_nc(sample)
    if task == TASK_ANOMALY:
        return validate_anomaly_year_dir(sample)
    raise ValueError(f"unknown task: {task}")


def run_validation_for_task(
    task: str,
    cfg: Mapping[str, Any],
    root: Path,
    *,
    limit: int | None = None,
) -> ValidationSummary:
    """
    对 ``list_processed_samples`` 返回的全部（或前 ``limit`` 条）样本做校验。

    失败样本的问题会写入日志 ``warning``，并在 :attr:`ValidationSummary.messages` 中保留若干条示例。
    """
    samples = list_processed_samples(task, cfg, root)
    if limit is not None:
        samples = samples[: max(0, limit)]

    summary = ValidationSummary(task=task, checked=len(samples))
    max_logged = 20
    for i, p in enumerate(samples):
        errs = _validate_one_sample(task, p)
        if errs:
            summary.failed += 1
            rel = p.resolve().relative_to(root.resolve()) if p.exists() else p
            line = f"{rel}: " + "; ".join(errs)
            _log.warning("%s", line)
            if len(summary.messages) < max_logged:
                summary.messages.append(line)
    if summary.failed == 0:
        _log.info("validate %s: %s samples OK", task, summary.checked)
    else:
        _log.warning("validate %s: %s failed / %s checked", task, summary.failed, summary.checked)
    return summary


def validate_manifest_and_samples(
    cfg: Mapping[str, Any],
    root: Path,
    *,
    check_splits: bool = True,
    sample_limit: int | None = None,
) -> dict[str, Any]:
    """
    可选：校验三个任务的 ``splits/*.json`` 路径存在性，并对各任务 processed 抽样校验。

    返回简单字典便于脚本打印或测试断言。
    """
    root = root.resolve()
    split_dir = root / cfg.get("paths", {}).get("splits", "data/processed/splits")
    out: dict[str, Any] = {"split_manifest_issues": {}, "task_summaries": {}}

    if check_splits:
        mapping = [
            ("eddy", "eddy.json"),
            ("element_forecasting", "element_forecasting.json"),
            ("anomaly_detection", "anomaly_detection.json"),
        ]
        for key, name in mapping:
            mp = split_dir / name
            if mp.is_file():
                issues = validate_split_manifest(mp, root)
                out["split_manifest_issues"][key] = issues
                if issues:
                    for m in issues[:50]:
                        _log.warning("manifest %s: %s", name, m)
                else:
                    _log.info("manifest OK: %s", mp.relative_to(root))
            else:
                out["split_manifest_issues"][key] = [f"missing {mp}"]

    for task in (TASK_EDDY, TASK_ELEMENT, TASK_ANOMALY):
        summ = run_validation_for_task(task, cfg, root, limit=sample_limit)
        out["task_summaries"][task] = {
            "checked": summ.checked,
            "failed": summ.failed,
            "sample_messages": summ.messages,
        }

    return out
