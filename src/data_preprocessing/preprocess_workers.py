"""供多进程调用的单文件/单年清洗任务（须为模块级函数以便 Windows spawn pickle）。"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def _ensure_src_on_path(root: Path) -> None:
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _encoding(ds, complevel: int) -> dict:
    enc: dict = {}
    for v in ds.data_vars:
        enc[v] = {"zlib": True, "complevel": complevel}
    return enc


def _write_dataset_netcdf(ds, out_path: Path, enc: dict) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".nc", dir=out_path.parent)
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        ds.to_netcdf(tmp_path, encoding=enc)
        os.replace(tmp_path, out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def clean_eddy_one(in_path: str, root: str, cfg: dict, complevel: int) -> str:
    root_p = Path(root)
    _ensure_src_on_path(root_p)
    from data_preprocessing.cleaner import clean_eddy
    from data_preprocessing.io import open_nc

    path = Path(in_path)
    out_dir = root_p / cfg["paths"]["processed"]["eddy"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ds = open_nc(path)
    try:
        clean = clean_eddy(ds, cfg)
    finally:
        ds.close()
    out_path = out_dir / f"{path.stem}_clean.nc"
    _write_dataset_netcdf(clean, out_path, _encoding(clean, complevel))
    return f"OK {path.name} -> {out_path.relative_to(root_p)}"


def clean_element_one(in_path: str, root: str, cfg: dict, complevel: int) -> str:
    root_p = Path(root)
    _ensure_src_on_path(root_p)
    from data_preprocessing.cleaner import clean_element
    from data_preprocessing.io import open_nc

    path = Path(in_path)
    out_dir = root_p / cfg["paths"]["processed"]["element_forecasting"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ds = open_nc(path)
    try:
        clean = clean_element(ds, cfg)
    finally:
        ds.close()
    out_path = out_dir / f"{path.stem}_clean.nc"
    _write_dataset_netcdf(clean, out_path, _encoding(clean, complevel))
    return f"OK {path.name} -> {out_path.relative_to(root_p)}"


def clean_anomaly_year_one(ydir: str, root: str, cfg: dict, complevel: int) -> list[str]:
    """处理 raw 下一年目录：oper + wave 各写一文件。"""
    root_p = Path(root)
    _ensure_src_on_path(root_p)
    from data_preprocessing.cleaner import clean_anomaly_oper, clean_anomaly_wave
    from data_preprocessing.io import open_nc

    raw_year = Path(ydir)
    out_dir = root_p / cfg["paths"]["processed"]["anomaly"] / raw_year.name
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    op = raw_year / "data_stream-oper_stepType-instant.nc"
    wv = raw_year / "data_stream-wave_stepType-instant.nc"
    if op.is_file():
        ds = open_nc(op)
        try:
            clean = clean_anomaly_oper(ds, cfg)
        finally:
            ds.close()
        p = out_dir / "oper_clean.nc"
        _write_dataset_netcdf(clean, p, _encoding(clean, complevel))
        lines.append(f"OK {op.name} -> {p.relative_to(root_p)}")
    if wv.is_file():
        ds = open_nc(wv)
        try:
            clean = clean_anomaly_wave(ds, cfg)
        finally:
            ds.close()
        p = out_dir / "wave_clean.nc"
        _write_dataset_netcdf(clean, p, _encoding(clean, complevel))
        lines.append(f"OK {wv.name} -> {p.relative_to(root_p)}")
    return lines
