"""data_preprocessing.io：临时 NetCDF  round-trip。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import xarray as xr

from data_preprocessing.io import open_nc


def test_open_nc_reads_roundtrip() -> None:
    arr = np.array([1.0, 2.0], dtype=np.float32)
    ds = xr.Dataset(
        data_vars={"x": (("t",), arr)},
        coords={"t": [0, 1]},
    )
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "tiny.nc"
        ds.to_netcdf(path)
        loaded = open_nc(path)
        try:
            assert "x" in loaded.data_vars
            assert np.allclose(loaded["x"].values, arr)
        finally:
            loaded.close()
