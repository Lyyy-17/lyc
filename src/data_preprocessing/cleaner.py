"""单文件清洗：哨兵/NaN → 掩膜与 valid 变量。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import xarray as xr


def _mask_sentinel(da: xr.DataArray, fill: float | None) -> tuple[xr.DataArray, xr.DataArray]:
    """返回 (清洗后数组, valid 掩膜 1=可用)."""
    if fill is None:
        valid = xr.ones_like(da, dtype=np.float32)
        valid = valid.where(np.isfinite(da), 0.0)
        out = da.where(np.isfinite(da))
        return out, valid
    v = da.astype(np.float64)
    bad = v == float(fill)
    out = da.where(~bad)
    valid = (~bad).astype(np.float32)
    valid = valid * np.isfinite(out).astype(np.float32)
    out = out.where(valid > 0)
    return out, valid


def _mask_nan(da: xr.DataArray) -> tuple[xr.DataArray, xr.DataArray]:
    fin = np.isfinite(da.values)
    valid = xr.DataArray(fin.astype(np.float32), dims=da.dims, coords=da.coords)
    out = da.where(fin)
    return out, valid


def clean_eddy(ds: xr.Dataset, cfg: Mapping[str, Any]) -> xr.Dataset:
    fill = float(cfg.get("fill", {}).get("eddy_float", -2147483647.0))
    out = xr.Dataset(attrs=dict(ds.attrs))
    for name in ("adt", "ugos", "vgos"):
        if name not in ds:
            continue
        da, vm = _mask_sentinel(ds[name], fill)
        out[name] = da
        out[f"{name}_valid"] = vm
    for c in ("time", "latitude", "longitude"):
        if c in ds:
            out[c] = ds[c]
    return out


def clean_element(ds: xr.Dataset, cfg: Mapping[str, Any]) -> xr.Dataset:
    fill = float(cfg.get("fill", {}).get("element", -30000.0))
    out = xr.Dataset(attrs=dict(ds.attrs))
    vars_ = ("sst", "sss", "ssu", "ssv")
    for name in vars_:
        if name not in ds:
            continue
        da, vm = _mask_sentinel(ds[name], fill)
        out[name] = da
        out[f"{name}_valid"] = vm

    for c in ("time", "lat", "lon"):
        if c in ds:
            out[c] = ds[c]
    return out


def clean_anomaly_oper(ds: xr.Dataset, cfg: Mapping[str, Any]) -> xr.Dataset:
    out = xr.Dataset(attrs=dict(ds.attrs))
    for name in ("u10", "v10"):
        if name not in ds:
            continue
        da, vm = _mask_nan(ds[name])
        out[name] = da
        out[f"{name}_valid"] = vm
    for c in ("valid_time", "latitude", "longitude"):
        if c in ds:
            out[c] = ds[c]
    if "u10" in out and "v10" in out:
        spd = np.sqrt(np.square(out["u10"]) + np.square(out["v10"]))
        out["wind_speed"] = xr.DataArray(spd, dims=out["u10"].dims, coords=out["u10"].coords)
    return out


def clean_anomaly_wave(ds: xr.Dataset, cfg: Mapping[str, Any]) -> xr.Dataset:
    out = xr.Dataset(attrs=dict(ds.attrs))
    for name in ("swh", "mwp", "mwd"):
        if name not in ds:
            continue
        da, vm = _mask_nan(ds[name])
        out[name] = da
        out[f"{name}_valid"] = vm
    for c in ("valid_time", "latitude", "longitude"):
        if c in ds:
            out[c] = ds[c]
    return out


def load_config(path: str | Path) -> dict[str, Any]:
    import yaml

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_project_root(cfg: Mapping[str, Any], config_path: Path) -> Path:
    root = cfg.get("project", {}).get("root", ".")
    p = (config_path.parent.parent if root == "." else Path(root)).resolve()
    return p if root != "." else config_path.parent.parent.resolve()
