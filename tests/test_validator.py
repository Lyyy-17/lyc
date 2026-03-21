"""data_preprocessing.validator：迷你 NetCDF 与划分清单校验。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from data_preprocessing.splitter import TASK_ANOMALY, TASK_EDDY, TASK_ELEMENT
from data_preprocessing.validator import (
    validate_anomaly_year_dir,
    validate_eddy_nc,
    validate_element_nc,
    validate_manifest_and_samples,
    validate_split_manifest,
)
from tests.conftest import (
    minimal_split_cfg,
    write_anomaly_year_dir,
    write_eddy_clean_nc,
    write_element_clean_nc,
)


def test_validate_eddy_nc_clean(tmp_path: Path) -> None:
    p = tmp_path / "sample_clean.nc"
    write_eddy_clean_nc(p)
    assert validate_eddy_nc(p) == []


def test_validate_eddy_nc_missing_variable(tmp_path: Path) -> None:
    p = tmp_path / "bad_clean.nc"
    t, la, lo = 2, 2, 2
    shape = (t, la, lo)
    ones = np.ones(shape, dtype=np.float32)
    ds = xr.Dataset(
        data_vars={
            "adt": (("time", "latitude", "longitude"), ones),
            "adt_valid": (("time", "latitude", "longitude"), ones),
        },
        coords={
            "time": [0.0, 1.0],
            "latitude": np.arange(la, dtype=np.float32),
            "longitude": np.arange(lo, dtype=np.float32),
        },
    )
    ds.to_netcdf(p)
    issues = validate_eddy_nc(p)
    assert any("缺少变量" in s for s in issues)


def test_validate_eddy_nc_time_not_strictly_increasing(tmp_path: Path) -> None:
    p = tmp_path / "time_dup_clean.nc"
    write_eddy_clean_nc(p, time_coord=[0.0, 0.0])
    issues = validate_eddy_nc(p)
    assert any("非严格递增" in s for s in issues)


def test_validate_element_nc_clean(tmp_path: Path) -> None:
    p = tmp_path / "el_clean.nc"
    write_element_clean_nc(p)
    assert validate_element_nc(p) == []


def test_validate_anomaly_year_dir_ok(tmp_path: Path) -> None:
    ydir = tmp_path / "data/processed/anomaly_detection" / "2019"
    write_anomaly_year_dir(ydir)
    assert validate_anomaly_year_dir(ydir) == []


def test_validate_split_manifest_paths_exist(tmp_path: Path) -> None:
    root = tmp_path
    d = root / "data/processed/eddy_detection"
    d.mkdir(parents=True)
    f = d / "a_clean.nc"
    f.write_bytes(b"x")
    man = root / "data/processed/splits/eddy.json"
    man.parent.mkdir(parents=True, exist_ok=True)
    rel = "data/processed/eddy_detection/a_clean.nc"
    man.write_text(
        json.dumps({"train": [rel], "val": [], "test": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert validate_split_manifest(man, root) == []


def test_validate_split_manifest_missing_path(tmp_path: Path) -> None:
    root = tmp_path
    man = root / "data/processed/splits/eddy.json"
    man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(
        json.dumps({"train": ["data/processed/eddy_detection/missing.nc"], "val": [], "test": []}),
        encoding="utf-8",
    )
    issues = validate_split_manifest(man, root)
    assert issues and "不存在" in issues[0]


def test_validate_manifest_and_samples_no_processed_files(tmp_path: Path) -> None:
    cfg = minimal_split_cfg(
        "data/processed/eddy_detection",
        "data/processed/element_forecasting",
        "data/processed/anomaly_detection",
    )
    for sub in ("eddy_detection", "element_forecasting", "anomaly_detection"):
        (tmp_path / "data/processed" / sub).mkdir(parents=True, exist_ok=True)
    out = validate_manifest_and_samples(cfg, tmp_path, check_splits=False)
    assert out["task_summaries"][TASK_EDDY]["checked"] == 0
    assert out["task_summaries"][TASK_EDDY]["failed"] == 0
    assert out["task_summaries"][TASK_ELEMENT]["checked"] == 0
    assert out["task_summaries"][TASK_ANOMALY]["checked"] == 0
