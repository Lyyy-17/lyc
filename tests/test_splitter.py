"""data_preprocessing.splitter：划分比例、清单写出、训练集 μ/σ（迷你 NetCDF）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_preprocessing.splitter import (
    TASK_EDDY,
    list_processed_eddy,
    list_processed_element,
    list_processed_samples,
    compute_train_standardization,
    split_train_val_test,
    write_split_manifest,
)
from tests.conftest import write_eddy_clean_nc, minimal_split_cfg


def test_split_ratios_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="split ratios"):
        split_train_val_test([1, 2, 3], 0.5, 0.5, 0.5, seed=1)


def test_split_train_val_test_partitions_and_deterministic() -> None:
    items = list(range(20))
    a = split_train_val_test(items, 0.7, 0.15, 0.15, seed=99)
    b = split_train_val_test(items, 0.7, 0.15, 0.15, seed=99)
    assert a == b
    tr, va, te = a
    assert len(tr) + len(va) + len(te) == 20
    assert set(tr) | set(va) | set(te) == set(items)


def test_split_train_val_test_empty() -> None:
    assert split_train_val_test([], 0.7, 0.15, 0.15, seed=1) == ([], [], [])


def test_list_processed_eddy_glob(tmp_path: Path) -> None:
    cfg = minimal_split_cfg(
        "data/processed/eddy_detection",
        "data/processed/element_forecasting",
        "data/processed/anomaly_detection",
    )
    d = tmp_path / "data/processed/eddy_detection"
    d.mkdir(parents=True)
    (d / "z_clean.nc").write_bytes(b"x")
    (d / "a_clean.nc").write_bytes(b"y")
    got = list_processed_eddy(cfg, tmp_path)
    assert got == [d / "a_clean.nc", d / "z_clean.nc"]


def test_list_processed_samples_dispatch(tmp_path: Path) -> None:
    cfg = minimal_split_cfg(
        "data/processed/eddy_detection",
        "data/processed/element_forecasting",
        "data/processed/anomaly_detection",
    )
    ed = tmp_path / "data/processed/eddy_detection"
    ed.mkdir(parents=True)
    f = ed / "only_clean.nc"
    f.write_bytes(b"1")
    assert list_processed_samples(TASK_EDDY, cfg, tmp_path) == [f]


def test_write_split_manifest_paths_relative(tmp_path: Path) -> None:
    root = tmp_path
    d = root / "data/processed/eddy_detection"
    d.mkdir(parents=True)
    a = d / "a_clean.nc"
    b = d / "b_clean.nc"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    out_dir = root / "data/processed/splits"
    p = write_split_manifest(TASK_EDDY, [a], [b], [], root, out_dir)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["train"] == ["data/processed/eddy_detection/a_clean.nc"]
    assert data["val"] == ["data/processed/eddy_detection/b_clean.nc"]
    assert data["test"] == []


def test_compute_train_standardization_eddy_one_file(tmp_path: Path) -> None:
    rel_dir = Path("data/processed/eddy_detection")
    nc = tmp_path / rel_dir / "one_clean.nc"
    write_eddy_clean_nc(nc)
    train_rel = [f"{rel_dir.as_posix()}/one_clean.nc"]
    out = compute_train_standardization(TASK_EDDY, train_rel, tmp_path)
    assert "adt" in out and "ugos" in out and "vgos" in out
    assert out["adt"]["std"] >= 1e-12 or out["adt"]["std"] == 1.0


def test_compute_train_standardization_empty_train_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        compute_train_standardization(TASK_EDDY, [], Path("."))


def test_list_processed_element(tmp_path: Path) -> None:
    cfg = minimal_split_cfg(
        "data/processed/eddy_detection",
        "data/processed/element_forecasting",
        "data/processed/anomaly_detection",
    )
    d = tmp_path / "data/processed/element_forecasting"
    d.mkdir(parents=True)
    p = d / "x_clean.nc"
    p.write_bytes(b"1")
    assert list_processed_element(cfg, tmp_path) == [p]
