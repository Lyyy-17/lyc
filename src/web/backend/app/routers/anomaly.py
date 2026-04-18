"""异常检测：标签/事件与 manifest 对齐检查。"""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException

from src.anomaly_detection.dataset import AnomalyFrameDataset

from .. import state
from ..paths import read_path_txt, resolve_path
from ..schemas import AnomalyInspectRequest
from ..time_utils import to_epoch_seconds

router = APIRouter(prefix="/api/anomaly", tags=["anomaly"])


@router.post("/inspect")
def inspect_anomaly(req: AnomalyInspectRequest):
    split = str(req.split).strip().lower()
    if split not in {"train", "val", "test"}:
        raise HTTPException(status_code=400, detail="split must be one of train/val/test")

    labels_path = resolve_path(req.labels_json.strip('"\''))
    events_path = resolve_path(req.events_json.strip('"\''))
    manifest_path = resolve_path(req.manifest_path.strip('"\''))
    processed_input = req.processed_dir.strip('"\'')
    if processed_input in {"", "data/processed/anomaly_detection", "data/processed/anomaly_detection/path.txt"}:
        processed_input = read_path_txt("data/processed/anomaly_detection/path.txt") or processed_input
    processed_dir = resolve_path(processed_input)
    norm_stats_path = resolve_path(req.norm_stats_path.strip('"\''))

    if not os.path.exists(labels_path):
        raise HTTPException(status_code=404, detail=f"labels file not found: {labels_path}")
    if not os.path.exists(events_path):
        raise HTTPException(status_code=404, detail=f"events file not found: {events_path}")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail=f"manifest file not found: {manifest_path}")

    try:
        with open(labels_path, "r", encoding="utf-8") as f:
            labels_obj = json.load(f)
        with open(events_path, "r", encoding="utf-8") as f:
            events_obj = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid json: {e}")

    if not isinstance(labels_obj, dict):
        raise HTTPException(status_code=400, detail="labels_json must be an object with split keys")

    split_labels_raw = labels_obj.get(split)
    if not isinstance(split_labels_raw, list):
        raise HTTPException(status_code=400, detail=f"labels_json missing list for split={split}")

    labels = [1 if int(v) == 1 else 0 for v in split_labels_raw]

    events: list[dict] = []
    if isinstance(events_obj, list):
        for ev in events_obj:
            if not isinstance(ev, dict) or "start" not in ev or "end" not in ev:
                continue
            try:
                start = int(ev["start"])
                end = int(ev["end"])
            except Exception:
                continue
            if end < start:
                continue
            events.append({"name": str(ev.get("name", "event")), "start": start, "end": end})

    cache_key = (processed_dir, manifest_path, split)
    cached_timestamps = state.anomaly_timestamps_cache.get(cache_key)
    if cached_timestamps is None:
        ds = AnomalyFrameDataset(
            processed_anomaly_dir=processed_dir,
            split=split,
            manifest_path=manifest_path,
            norm_stats_path=norm_stats_path if os.path.exists(norm_stats_path) else None,
            open_file_lru_size=max(0, int(req.open_file_lru_size)),
        )
        try:
            timestamps = [to_epoch_seconds(ts) for ts in ds.get_timestamps()]
        finally:
            ds.close()
        state.anomaly_timestamps_cache[cache_key] = timestamps
    else:
        timestamps = cached_timestamps

    n_pair = min(len(labels), len(timestamps))
    if n_pair == 0:
        raise HTTPException(status_code=400, detail="empty split after loading labels/timestamps")

    if len(labels) != len(timestamps):
        labels = labels[:n_pair]
        timestamps = timestamps[:n_pair]

    def _hit_events(ts: int) -> list[str]:
        if ts < 0:
            return []
        return [ev["name"] for ev in events if ev["start"] <= ts <= ev["end"]]

    positive_points: list[dict] = []
    matched_positive = 0
    matched_event_names: set[str] = set()

    for idx, (y, ts) in enumerate(zip(labels, timestamps)):
        if y != 1:
            continue
        hits = _hit_events(ts)
        if hits:
            matched_positive += 1
            matched_event_names.update(hits)
        positive_points.append(
            {
                "index": idx,
                "timestamp": ts,
                "event_hits": hits,
                "matched": bool(hits),
            }
        )

    max_points = max(1, int(req.max_points))
    preview = positive_points[:max_points]

    return {
        "split": split,
        "num_samples": n_pair,
        "num_positive": int(sum(labels)),
        "positive_ratio": float(sum(labels) / n_pair),
        "num_events": len(events),
        "matched_positive": matched_positive,
        "matched_positive_ratio": float(matched_positive / max(1, sum(labels))),
        "matched_event_count": len(matched_event_names),
        "points": preview,
        "truncated": len(positive_points) > len(preview),
        "labels_timestamps_aligned": len(split_labels_raw) == len(timestamps),
    }
