"""子命令 templates：生成 labels/events 评估模板。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from anomaly_detection.dataset import AnomalyFrameDataset

from .common import load_yaml, resolve_anomaly_processed_dir, resolve_path


def _parse_splits(text: str) -> list[str]:
    splits = [s.strip() for s in str(text).split(",") if s.strip()]
    if not splits:
        raise ValueError("splits is empty")
    for s in splits:
        if s not in {"train", "val", "test"}:
            raise ValueError(f"unsupported split: {s}")
    return splits


def _subset_len(n: int, max_n: int | None) -> int:
    if max_n is None:
        return n
    if max_n <= 0:
        return n
    return min(n, int(max_n))


def register_parser(sub: argparse.Action) -> argparse.ArgumentParser:
    p = sub.add_parser("templates", help="生成 labels/events JSON 模板（待填 0/1）")
    p.add_argument("--data-config", default="configs/data_config.yaml")
    p.add_argument("--train-config", default="configs/anomaly_detection/train.yaml")
    p.add_argument("--processed-dir", default=None)
    p.add_argument("--manifest", default=None)
    p.add_argument("--norm-stats", default=None)
    p.add_argument("--open-file-lru-size", type=int, default=None)
    p.add_argument("--splits", default="val,test", help="comma-separated: train,val,test")
    p.add_argument("--max-samples-per-split", type=int, default=None)
    p.add_argument("--label-init-value", type=int, default=-1, help="占位标签，默认 -1")
    p.add_argument("--output-dir", default="outputs/anomaly_detection/templates")
    p.add_argument("--force", action="store_true", help="覆盖已存在的模板文件")
    return p


def run(args: argparse.Namespace, root: Path) -> None:
    from utils.logger import get_logger

    _log = get_logger(__name__)

    data_cfg = load_yaml(resolve_path(args.data_config, root=root, default=root / "configs/data_config.yaml"))
    train_cfg = load_yaml(resolve_path(args.train_config, root=root, default=root / "configs/anomaly_detection/train.yaml"))

    default_processed_rel = "data/processed/anomaly_detection"
    processed_dir = resolve_anomaly_processed_dir(
        root,
        args.processed_dir or train_cfg.get("processed_dir") or data_cfg.get("paths", {}).get("processed", {}).get("anomaly"),
        default_rel=default_processed_rel,
        default_path=root / default_processed_rel,
    )
    manifest = resolve_path(
        args.manifest or train_cfg.get("manifest_path") or data_cfg.get("artifacts", {}).get("split_manifests", {}).get("anomaly_detection"),
        root=root,
        default=root / "data/processed/splits/anomaly_detection.json",
    )
    norm_stats = resolve_path(
        args.norm_stats or train_cfg.get("norm_stats_path") or data_cfg.get("artifacts", {}).get("normalization_files", {}).get("anomaly_detection"),
        root=root,
        default=root / "data/processed/normalization/anomaly_detection_norm.json",
    )
    open_file_lru_size = int(
        args.open_file_lru_size if args.open_file_lru_size is not None else train_cfg.get("open_file_lru_size", 6)
    )

    splits = _parse_splits(args.splits)
    out_dir = resolve_path(args.output_dir, root=root, default=root / "outputs/anomaly_detection/templates")
    out_dir.mkdir(parents=True, exist_ok=True)

    labels_template: dict[str, list[int]] = {}
    split_meta: dict[str, dict[str, Any]] = {}
    global_ts: list[int] = []

    for split in splits:
        ds = AnomalyFrameDataset(
            processed_anomaly_dir=processed_dir,
            split=split,
            manifest_path=manifest,
            norm_stats_path=norm_stats if norm_stats.is_file() else None,
            root=root,
            open_file_lru_size=open_file_lru_size,
        )
        n_total = len(ds)
        n_use = _subset_len(n_total, args.max_samples_per_split)
        labels_template[split] = [int(args.label_init_value)] * n_use

        ts_min: int | None = None
        ts_max: int | None = None
        for i in range(n_use):
            sample = ds[i]
            ts = sample.get("timestamp")
            if ts is None:
                continue
            try:
                tsi = int(ts)
            except Exception:
                continue
            if tsi < 0:
                continue
            global_ts.append(tsi)
            if ts_min is None or tsi < ts_min:
                ts_min = tsi
            if ts_max is None or tsi > ts_max:
                ts_max = tsi

        split_meta[split] = {
            "num_samples": int(n_use),
            "source_total_samples": int(n_total),
            "timestamp_min": ts_min,
            "timestamp_max": ts_max,
        }
        ds.close()

    if global_ts:
        ev_start = int(min(global_ts))
        ev_end = int(max(global_ts))
    else:
        ev_start, ev_end = 0, 0

    events_template: list[dict[str, Any]] = [
        {
            "name": "typhoon_example",
            "start": ev_start,
            "end": ev_end,
            "note": "replace start/end with real typhoon time window",
        }
    ]

    labels_path = out_dir / "labels.template.json"
    events_path = out_dir / "events.template.json"
    meta_path = out_dir / "template_meta.json"

    for p in (labels_path, events_path, meta_path):
        if p.exists() and not args.force:
            raise SystemExit(f"{p} already exists; use --force to overwrite")

    labels_path.write_text(json.dumps(labels_template, ensure_ascii=False, indent=2), encoding="utf-8")
    events_path.write_text(json.dumps(events_template, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "processed_dir": str(processed_dir),
                "manifest": str(manifest),
                "splits": splits,
                "label_init_value": int(args.label_init_value),
                "split_meta": split_meta,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    _log.info("Wrote labels template: %s", labels_path)
    _log.info("Wrote events template: %s", events_path)
    _log.info("Wrote template meta: %s", meta_path)
