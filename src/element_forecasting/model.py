"""要素长期预测混合模型：Transformer + Block Attn-Res + ARIMA + 注意力融合。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import warnings

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tools.sm_exceptions import ConvergenceWarning


class RMSNorm(nn.Module):
	"""轻量 RMSNorm，用于稳定 block-level attention 聚合。"""

	def __init__(self, dim: int, eps: float = 1e-6) -> None:
		super().__init__()
		self.eps = eps
		self.weight = nn.Parameter(torch.ones(dim))

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		rms = x.pow(2).mean(dim=-1, keepdim=True).add(self.eps).sqrt()
		return (x / rms) * self.weight


def block_attn_res(
	blocks: list[torch.Tensor],
	partial_block: torch.Tensor,
	proj: nn.Linear,
	norm: RMSNorm,
) -> torch.Tensor:
	"""Inter-block attention: 聚合历史 block 与当前 partial block 的上下文。"""

	v = torch.stack(blocks + [partial_block], dim=0)
	k = norm(v)
	logits = torch.einsum("d, n b t d -> n b t", proj.weight.squeeze(0), k)
	weights = logits.softmax(dim=0)
	h = torch.einsum("n b t, n b t d -> b t d", weights, v)
	return h


class BlockResidualTransformerLayer(nn.Module):
	"""在 Attention 与 MLP 之前都注入一次 block_attn_res。"""

	def __init__(self, d_model: int, nhead: int, mlp_ratio: float = 4.0, dropout: float = 0.1) -> None:
		super().__init__()
		self.norm1 = RMSNorm(d_model)
		self.norm2 = RMSNorm(d_model)
		self.self_attn = nn.MultiheadAttention(
			embed_dim=d_model,
			num_heads=nhead,
			dropout=dropout,
			batch_first=True,
		)
		hidden = int(d_model * mlp_ratio)
		self.mlp = nn.Sequential(
			nn.Linear(d_model, hidden),
			nn.GELU(),
			nn.Dropout(dropout),
			nn.Linear(hidden, d_model),
			nn.Dropout(dropout),
		)
		self.block_proj_attn = nn.Linear(d_model, 1, bias=False)
		self.block_proj_mlp = nn.Linear(d_model, 1, bias=False)
		self.block_norm_attn = RMSNorm(d_model)
		self.block_norm_mlp = RMSNorm(d_model)

	def forward(
		self,
		x: torch.Tensor,
		blocks: list[torch.Tensor],
		partial_block: torch.Tensor | None,
	) -> torch.Tensor:
		partial = x if partial_block is None else partial_block
		x = x + block_attn_res(blocks, partial, self.block_proj_attn, self.block_norm_attn)
		attn_out, _ = self.self_attn(self.norm1(x), self.norm1(x), self.norm1(x), need_weights=False)
		x = x + attn_out
		x = x + block_attn_res(blocks, partial, self.block_proj_mlp, self.block_norm_mlp)
		x = x + self.mlp(self.norm2(x))
		return x


class BlockResidualTransformerEncoder(nn.Module):
	"""维护 ``blocks`` 与 ``partial_block`` 的 Transformer 编码器。"""

	def __init__(self, num_layers: int, d_model: int, nhead: int, block_size: int, dropout: float = 0.1) -> None:
		super().__init__()
		self.layers = nn.ModuleList(
			[
				BlockResidualTransformerLayer(d_model=d_model, nhead=nhead, dropout=dropout)
				for _ in range(num_layers)
			]
		)
		self.block_size = max(2, int(block_size))
		self.block_stride = max(1, self.block_size // 2)

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		blocks: list[torch.Tensor] = []
		partial_block: torch.Tensor | None = None
		for layer_number, layer in enumerate(self.layers, start=1):
			x = layer(x, blocks=blocks, partial_block=partial_block)
			partial_block = x if partial_block is None else (partial_block + x)
			if layer_number % self.block_stride == 0:
				blocks.append(partial_block)
				partial_block = None
		return x


class TransformerForecastBranch(nn.Module):
	"""将每个网格点作为 token 序列建模并输出多步预测。"""

	def __init__(
		self,
		in_channels: int,
		input_steps: int,
		output_steps: int,
		d_model: int = 128,
		nhead: int = 4,
		num_layers: int = 6,
		block_size: int = 4,
		dropout: float = 0.1,
		spatial_downsample: int = 4,
	) -> None:
		super().__init__()
		self.in_channels = in_channels
		self.input_steps = input_steps
		self.output_steps = output_steps
		self.spatial_downsample = max(1, int(spatial_downsample))
		self.in_proj = nn.Linear(in_channels, d_model)
		self.pos_emb = nn.Parameter(torch.zeros(1, input_steps, d_model))
		self.encoder = BlockResidualTransformerEncoder(
			num_layers=num_layers,
			d_model=d_model,
			nhead=nhead,
			block_size=block_size,
			dropout=dropout,
		)
		self.out_proj = nn.Linear(d_model, output_steps * in_channels)

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		if x.dim() != 5:
			raise ValueError(f"expected x with shape (B,T,C,H,W), got {tuple(x.shape)}")
		bsz, t_in, ch, h, w = x.shape
		if t_in != self.input_steps:
			raise ValueError(f"expected input_steps={self.input_steps}, got {t_in}")
		if ch != self.in_channels:
			raise ValueError(f"expected in_channels={self.in_channels}, got {ch}")

		if self.spatial_downsample > 1:
			xr = x.reshape(bsz * t_in, ch, h, w)
			xr = F.avg_pool2d(xr, kernel_size=self.spatial_downsample, stride=self.spatial_downsample)
			h_r, w_r = xr.shape[-2], xr.shape[-1]
			x_work = xr.reshape(bsz, t_in, ch, h_r, w_r)
		else:
			h_r, w_r = h, w
			x_work = x

		# 每个空间位置独立建模时间序列，统一批处理提升吞吐。
		token = x_work.permute(0, 3, 4, 1, 2).reshape(bsz * h_r * w_r, t_in, ch)
		h_tok = self.in_proj(token) + self.pos_emb[:, :t_in, :]
		h_tok = self.encoder(h_tok)
		tail = h_tok[:, -1, :]
		pred_low = self.out_proj(tail).view(bsz, h_r, w_r, self.output_steps, ch)
		pred_low = pred_low.permute(0, 3, 4, 1, 2).contiguous()

		if self.spatial_downsample > 1:
			up = pred_low.reshape(bsz * self.output_steps, ch, h_r, w_r)
			up = F.interpolate(up, size=(h, w), mode="bilinear", align_corners=False)
			return up.reshape(bsz, self.output_steps, ch, h, w).contiguous()
		return pred_low


@dataclass
class ARIMAConfig:
	max_p: int = 2
	max_d: int = 1
	max_q: int = 2
	fixed_order: tuple[int, int, int] | None = None


class ARIMABranch:
	"""对每个变量拟合独立 ARIMA，并输出未来 horizon 预测。"""

	def __init__(self, cfg: ARIMAConfig | None = None) -> None:
		self.cfg = cfg or ARIMAConfig()

	def _select_order(self, series: np.ndarray) -> tuple[int, int, int]:
		if self.cfg.fixed_order is not None:
			return self.cfg.fixed_order

		best_order = (1, 0, 0)
		best_aic = float("inf")
		for p in range(self.cfg.max_p + 1):
			for d in range(self.cfg.max_d + 1):
				for q in range(self.cfg.max_q + 1):
					if p == 0 and d == 0 and q == 0:
						continue
					try:
						with warnings.catch_warnings():
							warnings.simplefilter("ignore", category=UserWarning)
							warnings.simplefilter("ignore", category=RuntimeWarning)
							warnings.simplefilter("ignore", category=ConvergenceWarning)
							fit = ARIMA(series, order=(p, d, q)).fit()
						if fit.aic < best_aic:
							best_aic = float(fit.aic)
							best_order = (p, d, q)
					except Exception:
						continue
		return best_order

	def forecast_batch(self, seq: np.ndarray, horizon: int) -> np.ndarray:
		"""seq: ``[B, T, C]`` -> out: ``[B, horizon, C]``。"""

		bsz, _, n_vars = seq.shape
		out = np.zeros((bsz, horizon, n_vars), dtype=np.float32)
		for b in range(bsz):
			for c in range(n_vars):
				s = seq[b, :, c]
				try:
					order = self._select_order(s)
					with warnings.catch_warnings():
						warnings.simplefilter("ignore", category=UserWarning)
						warnings.simplefilter("ignore", category=RuntimeWarning)
						warnings.simplefilter("ignore", category=ConvergenceWarning)
						fit = ARIMA(s, order=order).fit()
					fc = np.asarray(fit.forecast(steps=horizon), dtype=np.float32)
				except Exception:
					fc = np.repeat(np.asarray([s[-1]], dtype=np.float32), horizon)
				out[b, :, c] = fc
		return out

	def forecast_from_tensor(self, x: torch.Tensor, horizon: int) -> torch.Tensor:
		# 变量级 ARIMA：先对空间求均值，得到每个变量的一维时间序列。
		seq = x.detach().mean(dim=(3, 4)).cpu().numpy()
		arr = self.forecast_batch(seq, horizon=horizon)
		base = torch.from_numpy(arr).to(device=x.device, dtype=x.dtype)
		return base.unsqueeze(-1).unsqueeze(-1).expand(-1, -1, -1, x.size(3), x.size(4)).contiguous()


class AttentionStackingFusion(nn.Module):
	"""使用注意力权重融合 Transformer 与 ARIMA 两路预测。"""

	def __init__(self, in_channels: int, attn_dim: int = 64) -> None:
		super().__init__()
		self.query = nn.Sequential(
			nn.Linear(in_channels, attn_dim),
			nn.GELU(),
			nn.Linear(attn_dim, attn_dim),
		)
		self.key = nn.Linear(in_channels, attn_dim)
		self.scale = attn_dim**-0.5

	def forward(
		self,
		x: torch.Tensor,
		pred_transformer: torch.Tensor,
		pred_arima: torch.Tensor,
	) -> tuple[torch.Tensor, torch.Tensor]:
		ctx = x.mean(dim=(1, 3, 4))
		q = self.query(ctx)

		# branch summary: [B, 2, C]
		summary_t = pred_transformer.mean(dim=(1, 3, 4))
		summary_a = pred_arima.mean(dim=(1, 3, 4))
		summary = torch.stack([summary_t, summary_a], dim=1)
		k = self.key(summary)

		scores = torch.einsum("bd,bnd->bn", q, k) * self.scale
		weights = scores.softmax(dim=-1)
		fused = (
			weights[:, 0].view(-1, 1, 1, 1, 1) * pred_transformer
			+ weights[:, 1].view(-1, 1, 1, 1, 1) * pred_arima
		)
		return fused, weights


class HybridElementForecastModel(nn.Module):
	"""长时序预测混合框架主模型。"""

	def __init__(
		self,
		in_channels: int,
		input_steps: int,
		output_steps: int,
		d_model: int = 128,
		nhead: int = 4,
		num_layers: int = 6,
		block_size: int = 4,
		dropout: float = 0.1,
		arima_max_p: int = 2,
		arima_max_d: int = 1,
		arima_max_q: int = 2,
		arima_order: Sequence[int] | None = None,
		enable_arima: bool = True,
		spatial_downsample: int = 4,
	) -> None:
		super().__init__()
		fixed_order: tuple[int, int, int] | None = None
		if arima_order is not None:
			if len(arima_order) != 3:
				raise ValueError("arima_order must be length-3 sequence")
			fixed_order = (int(arima_order[0]), int(arima_order[1]), int(arima_order[2]))

		self.output_steps = output_steps
		self.enable_arima = enable_arima
		self.transformer = TransformerForecastBranch(
			in_channels=in_channels,
			input_steps=input_steps,
			output_steps=output_steps,
			d_model=d_model,
			nhead=nhead,
			num_layers=num_layers,
			block_size=block_size,
			dropout=dropout,
			spatial_downsample=spatial_downsample,
		)
		self.arima_branch = ARIMABranch(
			ARIMAConfig(
				max_p=arima_max_p,
				max_d=arima_max_d,
				max_q=arima_max_q,
				fixed_order=fixed_order,
			)
		)
		self.fusion = AttentionStackingFusion(in_channels=in_channels)

	def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
		pred_transformer = self.transformer(x)
		if self.enable_arima:
			pred_arima = self.arima_branch.forecast_from_tensor(x, horizon=self.output_steps)
		else:
			pred_arima = torch.zeros_like(pred_transformer)
		pred, weights = self.fusion(x, pred_transformer, pred_arima)
		return {
			"pred": pred,
			"pred_transformer": pred_transformer,
			"pred_arima": pred_arima,
			"fusion_weights": weights,
		}
