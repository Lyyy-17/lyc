"""
只读不写：按任务抽样 raw NetCDF，统计缺测率、有限值最值。

在项目根目录执行:
  python scripts/01_data_inspect.py
  python scripts/01_data_inspect.py --out outputs/data_stats/summary.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_preprocessing.cleaner import load_config  # noqa: E402
from data_preprocessing.io import open_nc  # noqa: E402
from utils.logger import get_logger, setup_logging  # noqa: E402

_log = get_logger(__name__)


def _sample_files(paths: list[Path], k: int, seed: int) -> list[Path]:
    if k <= 0 or len(paths) <= k:
        return sorted(paths)
    rng = random.Random(seed)
    return sorted(rng.sample(paths, k))


def _stats_dataarray(name: str, da: xr.DataArray, fill: float | None) -> dict:
    arr = np.asarray(da.values, dtype=np.float64)
    flat = arr.ravel()
    n = flat.size
    nan_c = int(np.isnan(flat).sum())
    inf_c = int(np.isinf(flat).sum())
    fill_c = 0
    if fill is not None and n:
        fill_c = int((flat == float(fill)).sum())
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        vmin = vmax = None
    else:
        vmin, vmax = float(finite.min()), float(finite.max())
    return {
        "variable": name,
        "shape": list(arr.shape),
        "count": n,
        "nan": nan_c,
        "inf": inf_c,
        "eq_fill": fill_c,
        "min": vmin,
        "max": vmax,
    }


def summarize_file(path: Path, task: str, fill_map: dict) -> dict:
    ds = open_nc(path)
    rows = []
    try:
        if task == "eddy":
            fill = float(fill_map.get("eddy_float", -2147483647.0))
            for v in ("adt", "ugos", "vgos"):
                if v in ds:
                    rows.append(_stats_dataarray(v, ds[v], fill))
        elif task == "element":
            fill = float(fill_map.get("element", -30000.0))
            for v in ("sst", "sss", "ssu", "ssv"):
                if v in ds:
                    rows.append(_stats_dataarray(v, ds[v], fill))
        elif task == "anomaly_oper":
            for v in ("u10", "v10"):
                if v in ds:
                    rows.append(_stats_dataarray(v, ds[v], None))
        elif task == "anomaly_wave":
            for v in ("swh", "mwp", "mwd"):
                if v in ds:
                    rows.append(_stats_dataarray(v, ds[v], None))
    finally:
        ds.close()
    return {"file": str(path.relative_to(ROOT)), "task": task, "variables": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="抽样统计 raw NetCDF（只读）")
    ap.add_argument("--config", type=Path, default=ROOT / "configs/data_config.yaml")
    ap.add_argument("--out", type=Path, default=None, help="写入 JSON；默认仅打印")
    args = ap.parse_args()
    setup_logging()

    cfg = load_config(args.config)
    paths_cfg = cfg.get("paths", {}).get("raw", {})
    st = cfg.get("stats", {})
    max_f = int(st.get("max_files_per_task", 5))
    seed = int(st.get("random_seed", 42))

    raw_eddy = ROOT / paths_cfg.get("eddy", "data/raw/eddy_detection")
    raw_el = ROOT / paths_cfg.get("element_forecasting", "data/raw/element_forecasting")
    raw_an = ROOT / paths_cfg.get("anomaly", "data/raw/anomaly_detection")

    report: dict = {"tasks": []}
    fill_map = cfg.get("fill", {})

    eddy_files = sorted(raw_eddy.glob("*.nc")) if raw_eddy.is_dir() else []
    for p in _sample_files(eddy_files, max_f, seed):
        report["tasks"].append(summarize_file(p, "eddy", fill_map))

    el_files = sorted(raw_el.glob("*.nc")) if raw_el.is_dir() else []
    for p in _sample_files(el_files, max_f, seed + 1):
        report["tasks"].append(summarize_file(p, "element", fill_map))

    if raw_an.is_dir():
        years = sorted([d for d in raw_an.iterdir() if d.is_dir()])
        for ydir in _sample_files(years, min(max_f, len(years)) if years else 0, seed + 2):
            op = ydir / "data_stream-oper_stepType-instant.nc"
            wv = ydir / "data_stream-wave_stepType-instant.nc"
            if op.is_file():
                report["tasks"].append(summarize_file(op, "anomaly_oper", fill_map))
            if wv.is_file():
                report["tasks"].append(summarize_file(wv, "anomaly_wave", fill_map))

    text = json.dumps(report, ensure_ascii=False, indent=2)
    sys.stdout.write(text + "\n")
    sys.stdout.flush()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        _log.info("Wrote %s", args.out.resolve())


if __name__ == "__main__":
    main()
