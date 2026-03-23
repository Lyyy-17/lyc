"""要素预测评估指标。"""
from __future__ import annotations

import torch


def mse(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
	return torch.mean((pred - target) ** 2)


def rmse(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
	return torch.sqrt(mse(pred, target) + 1e-12)


def mae(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
	return torch.mean(torch.abs(pred - target))


def nse(pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
	"""Nash-Sutcliffe Efficiency。"""

	num = torch.sum((pred - target) ** 2)
	denom = torch.sum((target - torch.mean(target)) ** 2) + 1e-12
	return 1.0 - num / denom


def compute_regression_metrics(pred: torch.Tensor, target: torch.Tensor) -> dict[str, float]:
	return {
		"mse": float(mse(pred, target).item()),
		"rmse": float(rmse(pred, target).item()),
		"mae": float(mae(pred, target).item()),
		"nse": float(nse(pred, target).item()),
	}
