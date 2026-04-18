"""进程内缓存（预测会话、涡旋模型与数据集句柄等）。"""
from __future__ import annotations

from threading import Lock
from typing import Any

from src.eddy_detection.model import EddyUNet

prediction_cache: dict[str, Any] = {}
eddy_prediction_cache: dict[str, Any] = {}
anomaly_timestamps_cache: dict[tuple[str, str, str], list[int]] = {}
eddy_model_cache: dict[tuple[str, int, int, str, int, int], EddyUNet] = {}
eddy_dataset_meta_cache: dict[str, dict[str, Any]] = {}
eddy_norm_cache: dict[str, Any] = {"path": "", "variables": {}}
eddy_dataset_handle_cache: dict[str, dict[str, Any]] = {}
eddy_window_cache: dict[tuple[str, int, int, int, int], dict[str, Any]] = {}
eddy_cache_lock = Lock()
