"""data_preprocessing.cleaner：小数组行为回归（不依赖真实赛题数据）。"""
from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from data_preprocessing.cleaner import (
    clean_anomaly_oper,
    clean_anomaly_wave,
    clean_eddy,
    clean_element,
    load_config,
)


def _eddy_cfg(fill: float) -> dict:
    return {"fill": {"eddy_float": fill}}


def test_clean_eddy_masks_sentinel_and_keeps_coords() -> None:
    # 与 float32 格点值可精确相等的哨兵（避免 -2147483647 在 float32 下与 cfg 不完全一致）
    fill = np.float32(-99999.0)
    arr = np.array([[[1.0, float(fill)], [3.0, 4.0]]], dtype=np.float32)
    ds = xr.Dataset(
        data_vars={"adt": (("time", "latitude", "longitude"), arr)},
        coords={
            "time": [0],
            "latitude": [0, 1],
            "longitude": [0, 1],
        },
    )
    out = clean_eddy(ds, _eddy_cfg(float(fill)))
    assert "adt" in out and "adt_valid" in out
    assert float(out["adt_valid"].values[0, 0, 1]) == 0.0
    assert "time" in out.coords and "latitude" in out.coords


def test_clean_element_uses_element_fill() -> None:
    fill = -30000.0
    arr = np.array([1.0, fill, 2.0], dtype=np.float32)
    ds = xr.Dataset(
        data_vars={"sst": (("time",), arr)},
        coords={"time": [0, 1, 2]},
    )
    out = clean_element(ds, {"fill": {"element": fill}})
    assert "sst_valid" in out
    assert float(out["sst_valid"].values[1]) == 0.0


def test_clean_anomaly_oper_wind_speed() -> None:
    u = np.array([[[3.0, 4.0]]], dtype=np.float32)
    v = np.zeros_like(u)
    ds = xr.Dataset(
        data_vars={
            "u10": (("valid_time", "latitude", "longitude"), u),
            "v10": (("valid_time", "latitude", "longitude"), v),
        },
        coords={
            "valid_time": [0],
            "latitude": [0],
            "longitude": [0, 1],
        },
    )
    out = clean_anomaly_oper(ds, {})
    assert "wind_speed" in out
    assert float(out["wind_speed"].values[0, 0, 0]) == pytest.approx(3.0)
    assert float(out["wind_speed"].values[0, 0, 1]) == pytest.approx(4.0)


def test_load_config_yaml(tmp_path) -> None:
    p = tmp_path / "cfg.yaml"
    p.write_text("fill:\n  eddy_float: -99.0\n  element: -1.0\n", encoding="utf-8")
    cfg = load_config(p)
    assert cfg["fill"]["eddy_float"] == -99.0
    assert cfg["fill"]["element"] == -1.0


def test_clean_anomaly_wave_nan() -> None:
    arr = np.array([1.0, np.nan], dtype=np.float32)
    ds = xr.Dataset(
        data_vars={"swh": (("valid_time",), arr)},
        coords={"valid_time": [0, 1]},
    )
    out = clean_anomaly_wave(ds, {})
    assert "swh_valid" in out
    assert float(out["swh_valid"].values[1]) == 0.0
