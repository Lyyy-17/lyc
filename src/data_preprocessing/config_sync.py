"""将划分清单与标准化 JSON 合并回写 `data_config.yaml`（便于训练单文件读取）。

首次回写前会复制一份 `data_config.yaml.bak` 保留原注释与排版；之后仍会以 PyYAML 整文件重写主配置。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import logging

import yaml

_log = logging.getLogger(__name__)


def merge_pipeline_artifacts_into_config(config_path: Path, root: Path) -> None:
    bak = config_path.with_name(config_path.name + ".bak")
    if config_path.is_file() and not bak.is_file():
        shutil.copy2(config_path, bak)

    text = config_path.read_text(encoding="utf-8")
    cfg: dict[str, Any] = yaml.safe_load(text) or {}

    norm_dir = root / cfg.get("paths", {}).get("normalization", "data/processed/normalization")
    split_dir = root / cfg.get("paths", {}).get("splits", "data/processed/splits")

    mapping: list[tuple[str, str, str]] = [
        ("eddy", "eddy.json", "eddy_norm.json"),
        ("element_forecasting", "element_forecasting.json", "element_forecasting_norm.json"),
        ("anomaly_detection", "anomaly_detection.json", "anomaly_detection_norm.json"),
    ]

    artifacts: dict[str, Any] = {
        "split_manifests": {},
        "normalization_files": {},
        "split_counts": {},
    }
    standardization: dict[str, Any] = {}

    for task_key, split_name, norm_name in mapping:
        sp = split_dir / split_name
        np = norm_dir / norm_name
        if sp.is_file():
            rel_sp = sp.resolve().relative_to(root.resolve()).as_posix()
            artifacts["split_manifests"][task_key] = rel_sp
            data = json.loads(sp.read_text(encoding="utf-8"))
            artifacts["split_counts"][task_key] = {
                "train": len(data.get("train", [])),
                "val": len(data.get("val", [])),
                "test": len(data.get("test", [])),
            }
        if np.is_file():
            rel_np = np.resolve().relative_to(root.resolve()).as_posix()
            artifacts["normalization_files"][task_key] = rel_np
            j = json.loads(np.read_text(encoding="utf-8"))
            standardization[task_key] = j.get("variables", {})

    cfg["artifacts"] = artifacts
    cfg["standardization"] = standardization

    out = yaml.safe_dump(
        cfg,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    config_path.write_text(
        "# 数据路径与清洗参数（相对项目根目录）\n"
        "# 末尾 artifacts / standardization 由 scripts/02_preprocess.py 在 --steps 含 stats 时自动回写\n"
        + out,
        encoding="utf-8",
    )
    _log.info("updated config: %s", config_path.relative_to(root))
