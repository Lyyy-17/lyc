"""涡旋分割训练循环（最小可跑版）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F


def _dice_loss_binary(logits: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
	probs = torch.sigmoid(logits)
	target = target.float()
	dims = (1, 2, 3)
	inter = (probs * target).sum(dim=dims)
	den = probs.sum(dim=dims) + target.sum(dim=dims)
	dice = (2.0 * inter + eps) / (den + eps)
	return 1.0 - dice.mean()


def _dice_loss_multiclass(logits: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
	num_classes = logits.shape[1]
	probs = torch.softmax(logits, dim=1)
	target_oh = F.one_hot(target.long(), num_classes=num_classes).permute(0, 3, 1, 2).float()
	dims = (0, 2, 3)
	inter = (probs * target_oh).sum(dim=dims)
	den = probs.sum(dim=dims) + target_oh.sum(dim=dims)
	dice = (2.0 * inter + eps) / (den + eps)
	return 1.0 - dice.mean()


def _binary_iou_f1(logits: torch.Tensor, target: torch.Tensor, threshold: float = 0.5, eps: float = 1e-6) -> tuple[float, float]:
	pred = (torch.sigmoid(logits) >= threshold).float()
	tgt = target.float()
	tp = (pred * tgt).sum().item()
	fp = (pred * (1.0 - tgt)).sum().item()
	fn = ((1.0 - pred) * tgt).sum().item()
	iou = tp / (tp + fp + fn + eps)
	f1 = (2.0 * tp) / (2.0 * tp + fp + fn + eps)
	return float(iou), float(f1)


def _multiclass_iou_f1(logits: torch.Tensor, target: torch.Tensor, eps: float = 1e-6) -> tuple[float, float]:
	pred = torch.argmax(logits, dim=1)
	target = target.long()
	num_classes = logits.shape[1]

	ious: list[float] = []
	f1s: list[float] = []
	for c in range(num_classes):
		p = (pred == c)
		t = (target == c)
		tp = (p & t).sum().item()
		fp = (p & (~t)).sum().item()
		fn = ((~p) & t).sum().item()
		ious.append(tp / (tp + fp + fn + eps))
		f1s.append((2.0 * tp) / (2.0 * tp + fp + fn + eps))
	return float(sum(ious) / len(ious)), float(sum(f1s) / len(f1s))


def build_loss(task_type: str, dice_weight: float = 0.5) -> Any:
	"""返回 `loss_fn(logits, target)`，默认 BCE/CE + Dice。"""

	if task_type == "binary":
		bce = nn.BCEWithLogitsLoss()

		def loss_fn(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
			if target.ndim == 3:
				target_ = target.unsqueeze(1)
			else:
				target_ = target
			target_ = target_.float()
			return (1.0 - dice_weight) * bce(logits, target_) + dice_weight * _dice_loss_binary(logits, target_)

		return loss_fn

	if task_type == "multiclass":
		ce = nn.CrossEntropyLoss()

		def loss_fn(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
			target_ = target.long()
			if target_.ndim == 4 and target_.shape[1] == 1:
				target_ = target_[:, 0]
			return (1.0 - dice_weight) * ce(logits, target_) + dice_weight * _dice_loss_multiclass(logits, target_)

		return loss_fn

	raise ValueError(f"unsupported task_type: {task_type}")


def train_one_epoch(
	model: nn.Module,
	loader: torch.utils.data.DataLoader,
	optimizer: torch.optim.Optimizer,
	loss_fn: Any,
	device: torch.device | str,
) -> dict[str, float]:
	model.train()
	loss_sum = 0.0
	n_batches = 0

	for batch in loader:
		x = batch["x"].to(device).float().nan_to_num(0.0)
		y = batch["y"].to(device).nan_to_num(0.0)

		optimizer.zero_grad(set_to_none=True)
		logits = model(x)
		loss = loss_fn(logits, y)
		if not torch.isfinite(loss):
			continue
		loss.backward()
		optimizer.step()

		loss_sum += float(loss.item())
		n_batches += 1

	return {"loss": loss_sum / max(1, n_batches)}


@torch.no_grad()
def validate_one_epoch(
	model: nn.Module,
	loader: torch.utils.data.DataLoader,
	loss_fn: Any,
	device: torch.device | str,
	task_type: str,
) -> dict[str, float]:
	model.eval()
	loss_sum = 0.0
	n_batches = 0
	iou_sum = 0.0
	f1_sum = 0.0

	for batch in loader:
		x = batch["x"].to(device).float().nan_to_num(0.0)
		y = batch["y"].to(device).nan_to_num(0.0)

		logits = model(x)
		loss = loss_fn(logits, y)
		if not torch.isfinite(loss):
			continue

		if task_type == "binary":
			iou, f1 = _binary_iou_f1(logits, y if y.ndim == 4 else y.unsqueeze(1))
		else:
			iou, f1 = _multiclass_iou_f1(logits, y if y.ndim == 3 else y[:, 0])

		loss_sum += float(loss.item())
		iou_sum += iou
		f1_sum += f1
		n_batches += 1

	d = max(1, n_batches)
	return {
		"loss": loss_sum / d,
		"iou": iou_sum / d,
		"f1": f1_sum / d,
	}


@dataclass
class EddyTrainConfig:
	task_type: str = "binary"
	dice_weight: float = 0.5
	lr: float = 1e-3
	epochs: int = 10
	device: str = "cuda" if torch.cuda.is_available() else "cpu"
	output_dir: Path = Path("outputs/eddy_detection")
	save_name: str = "best.pt"


def fit(
	model: nn.Module,
	train_loader: torch.utils.data.DataLoader,
	val_loader: torch.utils.data.DataLoader,
	cfg: EddyTrainConfig,
) -> list[dict[str, float]]:
	"""执行训练并保存最佳 checkpoint，返回逐 epoch 历史。"""

	device = torch.device(cfg.device)
	model = model.to(device)
	optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr)
	loss_fn = build_loss(cfg.task_type, dice_weight=cfg.dice_weight)

	cfg.output_dir.mkdir(parents=True, exist_ok=True)
	best_path = cfg.output_dir / cfg.save_name

	best_val = float("inf")
	history: list[dict[str, float]] = []

	for epoch in range(1, cfg.epochs + 1):
		tr = train_one_epoch(model, train_loader, optimizer, loss_fn, device)
		va = validate_one_epoch(model, val_loader, loss_fn, device, cfg.task_type)
		row = {
			"epoch": float(epoch),
			"train_loss": tr["loss"],
			"val_loss": va["loss"],
			"val_iou": va["iou"],
			"val_f1": va["f1"],
		}
		history.append(row)

		if torch.isfinite(torch.tensor(va["loss"])) and va["loss"] < best_val:
			best_val = va["loss"]
			torch.save(
				{
					"epoch": epoch,
					"model_state_dict": model.state_dict(),
					"optimizer_state_dict": optimizer.state_dict(),
					"val_loss": va["loss"],
					"task_type": cfg.task_type,
				},
				best_path,
			)

	return history
