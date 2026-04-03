"""涡旋识别训练入口。

项目根目录执行示例::

  python scripts/03_train_eddy.py --epochs 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import torch
import yaml
from torch.utils.data import DataLoader
from torch.utils.data import Subset

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
	sys.path.insert(0, str(SRC))

from eddy_detection.dataset import EddyLabelConfig, EddySegDataset
from eddy_detection.model import UNetEddy
from eddy_detection.trainer import EddyTrainConfig, fit
from utils.logger import get_logger, setup_logging

_log = get_logger(__name__)


def _load_yaml(path: Path) -> dict[str, Any]:
	if not path.is_file():
		return {}
	data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
	return data if isinstance(data, dict) else {}


def _resolve_path(path_like: str | Path | None, *, default: Path) -> Path:
	if path_like is None:
		return default
	p = Path(path_like)
	return p if p.is_absolute() else (ROOT / p)


def _resolve_device(v: str) -> str:
	if v == "auto":
		return "cuda" if torch.cuda.is_available() else "cpu"
	return v


def parse_args() -> argparse.Namespace:
	ap = argparse.ArgumentParser(description="Train eddy segmentation baseline (UNet)")
	ap.add_argument("--data-config", default="configs/data_config.yaml")
	ap.add_argument("--model-config", default="configs/eddy_detection/model.yaml")
	ap.add_argument("--train-config", default="configs/eddy_detection/train.yaml")

	ap.add_argument("--epochs", type=int, default=None)
	ap.add_argument("--batch-size", type=int, default=None)
	ap.add_argument("--num-workers", type=int, default=None)
	ap.add_argument("--lr", type=float, default=None)
	ap.add_argument("--device", default=None)

	ap.add_argument("--task-type", choices=["binary", "multiclass"], default=None)
	ap.add_argument("--label-dir", default=None)
	ap.add_argument("--manifest", default=None)
	ap.add_argument("--processed-dir", default=None)
	ap.add_argument("--norm-stats", default=None)

	ap.add_argument("--output-dir", default=None)
	ap.add_argument("--save-name", default=None)
	ap.add_argument("--seed", type=int, default=None)
	ap.add_argument("--max-train-samples", type=int, default=None)
	ap.add_argument("--max-val-samples", type=int, default=None)
	ap.add_argument("--open-file-lru-size", type=int, default=None)
	return ap.parse_args()


def main() -> None:
	args = parse_args()
	setup_logging(log_file=ROOT / "outputs/logs/eddy_detection_train.log")

	data_cfg = _load_yaml(_resolve_path(args.data_config, default=ROOT / "configs/data_config.yaml"))
	model_cfg = _load_yaml(_resolve_path(args.model_config, default=ROOT / "configs/eddy_detection/model.yaml"))
	train_cfg = _load_yaml(_resolve_path(args.train_config, default=ROOT / "configs/eddy_detection/train.yaml"))

	seed = int(args.seed if args.seed is not None else train_cfg.get("seed", 42))
	torch.manual_seed(seed)

	var_names_raw = train_cfg.get("var_names", ["adt", "ugos", "vgos"])
	var_names = tuple(str(v) for v in var_names_raw)

	manifest = _resolve_path(
		args.manifest or train_cfg.get("manifest_path") or data_cfg.get("artifacts", {}).get("split_manifests", {}).get("eddy"),
		default=ROOT / "data/processed/splits/eddy.json",
	)
	processed_dir = _resolve_path(
		args.processed_dir or train_cfg.get("processed_dir") or data_cfg.get("paths", {}).get("processed", {}).get("eddy"),
		default=ROOT / "data/processed/eddy_detection",
	)
	norm_stats = _resolve_path(
		args.norm_stats or train_cfg.get("norm_stats_path") or data_cfg.get("artifacts", {}).get("normalization_files", {}).get("eddy"),
		default=ROOT / "data/processed/normalization/eddy_norm.json",
	)
	label_dir = _resolve_path(
		args.label_dir or train_cfg.get("label_dir"),
		default=ROOT / "data/processed/eddy_detection_labels",
	)

	task_type = str(args.task_type or train_cfg.get("task_type", "binary"))
	label_cfg = EddyLabelConfig(label_dir=label_dir, task_type=task_type)
	open_file_lru_size = int(
		args.open_file_lru_size
		if args.open_file_lru_size is not None
		else train_cfg.get("open_file_lru_size", 8)
	)

	train_ds = EddySegDataset(
		processed_dir=processed_dir,
		var_names=var_names,
		split="train",
		manifest_path=manifest,
		norm_stats_path=norm_stats if norm_stats.is_file() else None,
		label_cfg=label_cfg,
		augment=bool(train_cfg.get("augment", True)),
		open_file_lru_size=open_file_lru_size,
		root=ROOT,
	)
	val_ds = EddySegDataset(
		processed_dir=processed_dir,
		var_names=var_names,
		split="val",
		manifest_path=manifest,
		norm_stats_path=norm_stats if norm_stats.is_file() else None,
		label_cfg=label_cfg,
		augment=False,
		open_file_lru_size=open_file_lru_size,
		root=ROOT,
	)

	max_train = args.max_train_samples if args.max_train_samples is not None else train_cfg.get("max_train_samples")
	max_val = args.max_val_samples if args.max_val_samples is not None else train_cfg.get("max_val_samples")
	if max_train is not None:
		max_train = int(max_train)
		if max_train > 0 and len(train_ds) > max_train:
			train_ds = Subset(train_ds, list(range(max_train)))
	if max_val is not None:
		max_val = int(max_val)
		if max_val > 0 and len(val_ds) > max_val:
			val_ds = Subset(val_ds, list(range(max_val)))

	if len(train_ds) == 0:
		raise SystemExit("train dataset is empty")
	if len(val_ds) == 0:
		raise SystemExit("val dataset is empty")

	sample = train_ds[0]
	in_channels = int(sample["x"].shape[0])

	if task_type == "binary":
		num_classes = int(model_cfg.get("num_classes", 1))
		if num_classes != 1:
			_log.warning("binary task expects num_classes=1, got %s; force to 1", num_classes)
			num_classes = 1
	else:
		num_classes = int(model_cfg.get("num_classes", 3))
		if num_classes < 2:
			raise SystemExit("multiclass task requires num_classes >= 2")

	batch_size = int(args.batch_size if args.batch_size is not None else train_cfg.get("batch_size", 8))
	num_workers = int(args.num_workers if args.num_workers is not None else train_cfg.get("num_workers", 0))

	train_loader = DataLoader(
		train_ds,
		batch_size=batch_size,
		shuffle=True,
		num_workers=num_workers,
		pin_memory=torch.cuda.is_available(),
	)
	val_loader = DataLoader(
		val_ds,
		batch_size=batch_size,
		shuffle=False,
		num_workers=num_workers,
		pin_memory=torch.cuda.is_available(),
	)

	model = UNetEddy(
		in_channels=in_channels,
		num_classes=num_classes,
		base_channels=int(model_cfg.get("base_channels", 32)),
	)

	output_dir = _resolve_path(args.output_dir or train_cfg.get("output_dir"), default=ROOT / "outputs/eddy_detection")
	tcfg = EddyTrainConfig(
		task_type=task_type,
		dice_weight=float(train_cfg.get("dice_weight", 0.5)),
		lr=float(args.lr if args.lr is not None else train_cfg.get("lr", 1e-3)),
		epochs=int(args.epochs if args.epochs is not None else train_cfg.get("epochs", 1)),
		device=_resolve_device(str(args.device or train_cfg.get("device", "auto"))),
		output_dir=output_dir,
		save_name=str(args.save_name or train_cfg.get("save_name", "unet_best.pt")),
	)

	_log.info("Start eddy training: task=%s, train=%d, val=%d", task_type, len(train_ds), len(val_ds))
	_log.info("Model: in_channels=%d, num_classes=%d", in_channels, num_classes)
	_log.info("Train config: epochs=%d, batch_size=%d, device=%s", tcfg.epochs, batch_size, tcfg.device)

	history = fit(model, train_loader, val_loader, tcfg)

	output_dir.mkdir(parents=True, exist_ok=True)
	hist_path = output_dir / "history.json"
	hist_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
	_log.info("Training done. best checkpoint=%s, history=%s", output_dir / tcfg.save_name, hist_path)


if __name__ == "__main__":
	main()
