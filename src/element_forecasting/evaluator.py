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


def masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
	"""
	掩膜版 MSE：仅在 mask==1 的位置计算。

	pred/target/mask 形状需可广播到一致；mask 为 0/1 或任意非负权重都可。
	"""
	p = pred.float()
	t = target.float()
	m = mask.float()
	diff2 = (p - t).pow(2)
	num = torch.sum(diff2 * m)
	den = torch.sum(m).clamp_min(eps)
	return num / den


def masked_weighted_mse(
	pred: torch.Tensor,
	target: torch.Tensor,
	mask: torch.Tensor,
	channel_weights: torch.Tensor | None = None,
	eps: float = 1e-12,
) -> torch.Tensor:
	"""按通道加权的掩膜 MSE。"""
	p = pred.float()
	t = target.float()
	m = mask.float()
	w = torch.ones_like(p) if channel_weights is None else channel_weights.float()
	diff2 = (p - t).pow(2)
	num = torch.sum(diff2 * m * w)
	den = torch.sum(m * w).clamp_min(eps)
	return num / den


def masked_spatial_mean_mse(
	pred: torch.Tensor,
	target: torch.Tensor,
	mask: torch.Tensor,
	channel_weights: torch.Tensor | None = None,
	eps: float = 1e-12,
) -> torch.Tensor:
	"""空间均值约束：比较每个样本/步长/变量的空间均值误差，并支持通道加权。"""
	p = pred.float()
	t = target.float()
	m = mask.float()

	den_hw = torch.sum(m, dim=(-2, -1), keepdim=True).clamp_min(eps)
	p_mean = torch.sum(p * m, dim=(-2, -1), keepdim=True) / den_hw
	t_mean = torch.sum(t * m, dim=(-2, -1), keepdim=True) / den_hw
	mean_diff2 = (p_mean - t_mean).pow(2)

	valid_bt = (den_hw > eps).float()
	w = torch.ones_like(mean_diff2) if channel_weights is None else channel_weights.float()
	num = torch.sum(mean_diff2 * valid_bt * w)
	den = torch.sum(valid_bt * w).clamp_min(eps)
	return num / den


def masked_rmse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
	return torch.sqrt(masked_mse(pred, target, mask, eps=eps) + eps)


def masked_mae(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
	p = pred.float()
	t = target.float()
	m = mask.float()
	absdiff = torch.abs(p - t)
	num = torch.sum(absdiff * m)
	den = torch.sum(m).clamp_min(eps)
	return num / den


def masked_nse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor, eps: float = 1e-12) -> torch.Tensor:
	"""
	掩膜版 NSE：
	mean 取 mask 覆盖的有效点；分子/分母也只在有效点统计。
	"""
	p = pred.float()
	t = target.float()
	m = mask.float()
	den = torch.sum(m).clamp_min(eps)

	mean_t = torch.sum(t * m) / den
	ss_res = torch.sum(((p - t) ** 2) * m)
	ss_tot = torch.sum(((t - mean_t) ** 2) * m) + eps
	return 1.0 - ss_res / ss_tot


def compute_regression_metrics_masked(
	pred: torch.Tensor,
	target: torch.Tensor,
	mask: torch.Tensor,
) -> dict[str, float]:
	return {
		"mse": float(masked_mse(pred, target, mask).item()),
		"rmse": float(masked_rmse(pred, target, mask).item()),
		"mae": float(masked_mae(pred, target, mask).item()),
		"nse": float(masked_nse(pred, target, mask).item()),
	}
