"""基于 clean NetCDF 生成涡旋伪标签（binary mask）。

默认输出到 ``data/processed/eddy_detection_labels/<source_stem>/<YYYYMMDD>.npy``。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_preprocessing.io import open_nc


def _to_date_key(time_value: np.ndarray | object, idx: int) -> str:
    try:
        ts = np.datetime_as_string(np.asarray(time_value, dtype="datetime64[ns]"), unit="D")
        return ts.replace("-", "")
    except (TypeError, ValueError):
        return f"idx_{idx:07d}"


def _okubo_weiss_like(ugos: np.ndarray, vgos: np.ndarray) -> np.ndarray:
    """二维速度场的 OW 近似（忽略坐标尺度因子，仅用于伪标签）。"""

    du_dy, du_dx = np.gradient(ugos)
    dv_dy, dv_dx = np.gradient(vgos)
    sn = du_dx - dv_dy
    ss = dv_dx + du_dy
    w = dv_dx - du_dy
    # 常见定义之一：OW = sn^2 + ss^2 - w^2
    return sn * sn + ss * ss - w * w


def generate_labels_for_file(
    nc_path: Path,
    out_dir: Path,
    quantile: float,
    min_pixels: int,
    max_days: int | None,
) -> dict[str, int]:
    ds = open_nc(nc_path)
    try:
        if "ugos" not in ds or "vgos" not in ds:
            raise KeyError(f"missing ugos/vgos in {nc_path}")

        u = np.asarray(ds["ugos"].values, dtype=np.float32)
        v = np.asarray(ds["vgos"].values, dtype=np.float32)
        if u.ndim != 3 or v.ndim != 3:
            raise ValueError(f"expect (time, lat, lon), got ugos={u.shape}, vgos={v.shape}")

        times = np.asarray(ds["time"].values) if "time" in ds.coords else np.arange(u.shape[0])
        source_dir = out_dir / nc_path.stem
        source_dir.mkdir(parents=True, exist_ok=True)

        n_days = u.shape[0] if max_days is None else min(u.shape[0], max_days)
        valid_days = 0
        for t in range(n_days):
            ow = _okubo_weiss_like(u[t], v[t])
            thr = float(np.nanquantile(ow, quantile))
            mask = (ow < thr).astype(np.uint8)

            # 简单去噪：面积太小的整天标签直接清空
            if int(mask.sum()) < min_pixels:
                mask[:] = 0
            else:
                valid_days += 1

            date_key = _to_date_key(times[t], t)
            np.save(source_dir / f"{date_key}.npy", mask)

        return {"days": int(n_days), "valid_days": valid_days}
    finally:
        ds.close()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Generate pseudo eddy labels from clean NetCDF")
    ap.add_argument("--processed-dir", default="data/processed/eddy_detection")
    ap.add_argument("--output-dir", default="data/processed/eddy_detection_labels")
    ap.add_argument("--manifest", default="data/processed/splits/eddy.json")
    ap.add_argument("--split", default="train,val", help="comma separated splits to process")
    ap.add_argument("--quantile", type=float, default=0.12, help="OW threshold quantile, lower -> stricter mask")
    ap.add_argument("--min-pixels", type=int, default=80, help="minimum positive pixels per day")
    ap.add_argument("--max-files", type=int, default=None, help="for smoke run")
    ap.add_argument("--max-days", type=int, default=None, help="max days per file, for smoke run")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    processed_dir = (ROOT / args.processed_dir).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    manifest_path = (ROOT / args.manifest).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if manifest_path.is_file():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        wanted = [s.strip() for s in str(args.split).split(",") if s.strip()]
        rels: list[str] = []
        for s in wanted:
            rels.extend(m.get(s, []))
        paths = [(ROOT / r).resolve() for r in rels]
    else:
        paths = sorted(processed_dir.glob("*_clean.nc"))

    if args.max_files is not None:
        paths = paths[: max(0, int(args.max_files))]

    if not paths:
        raise SystemExit("no clean nc files found for label generation")

    total_days = 0
    total_valid = 0
    for p in paths:
        stat = generate_labels_for_file(
            p,
            output_dir,
            quantile=float(args.quantile),
            min_pixels=int(args.min_pixels),
            max_days=(None if args.max_days is None else int(args.max_days)),
        )
        total_days += stat["days"]
        total_valid += stat["valid_days"]
        print(f"[OK] {p.name}: days={stat['days']}, valid={stat['valid_days']}")

    print(f"DONE: files={len(paths)}, days={total_days}, valid_days={total_valid}, out={output_dir}")


if __name__ == "__main__":
    main()
