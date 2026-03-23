"""要素长期预测推理器。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import torch

from element_forecasting.model import HybridElementForecastModel


class ElementForecastPredictor:
	def __init__(self, checkpoint_path: str | Path, device: str = "auto") -> None:
		ckpt = torch.load(Path(checkpoint_path), map_location="cpu")
		model_cfg = ckpt.get("model_config", {})
		in_channels = int(ckpt["in_channels"])
		input_steps = int(ckpt["input_steps"])
		output_steps = int(ckpt["output_steps"])

		if device == "auto":
			device = "cuda" if torch.cuda.is_available() else "cpu"
		self.device = torch.device(device)

		self.model = HybridElementForecastModel(
			in_channels=in_channels,
			input_steps=input_steps,
			output_steps=output_steps,
			d_model=int(model_cfg.get("d_model", 128)),
			nhead=int(model_cfg.get("nhead", 4)),
			num_layers=int(model_cfg.get("num_layers", 6)),
			block_size=int(model_cfg.get("block_size", 4)),
			dropout=float(model_cfg.get("dropout", 0.1)),
			spatial_downsample=int(model_cfg.get("spatial_downsample", 4)),
			arima_max_p=int(model_cfg.get("arima_max_p", 2)),
			arima_max_d=int(model_cfg.get("arima_max_d", 1)),
			arima_max_q=int(model_cfg.get("arima_max_q", 2)),
			arima_order=model_cfg.get("arima_order"),
			enable_arima=bool(model_cfg.get("enable_arima", True)),
		)
		self.model.load_state_dict(ckpt["model_state"])
		self.model.to(self.device)
		self.model.eval()
		self.var_names = tuple(ckpt.get("var_names", []))
		self.input_steps = input_steps
		self.output_steps = output_steps

	@torch.no_grad()
	def predict(self, x: torch.Tensor) -> dict[str, Any]:
		"""x shape: ``(B, input_steps, C, H, W)``。"""

		x = x.to(self.device)
		out = self.model(x)
		return {
			"pred": out["pred"].cpu(),
			"pred_transformer": out["pred_transformer"].cpu(),
			"pred_arima": out["pred_arima"].cpu(),
			"fusion_weights": out["fusion_weights"].cpu(),
			"var_names": self.var_names,
		}
