"""要素预报基线：ConvLSTM 编码 + 1×1 卷积解码为多步输出。"""
from __future__ import annotations

import torch
import torch.nn as nn

from .convlstm import ConvLSTMEncoder


class ElementForecastConvLSTMBaseline(nn.Module):
    """
    输入历史 ``T_in`` 帧、多变量通道，预测未来 ``T_out`` 帧（同通道数）。

    形状：``x`` 为 ``(B, T_in, C, H, W)``，输出 ``(B, T_out, C, H, W)``。
    """

    def __init__(
        self,
        in_channels: int = 4,
        hidden_channels: int = 64,
        kernel_size: int = 3,
        num_layers: int = 2,
        forecast_len: int = 12,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.forecast_len = forecast_len
        self.encoder = ConvLSTMEncoder(
            in_channels=in_channels,
            hidden_channels=hidden_channels,
            kernel_size=kernel_size,
            num_layers=num_layers,
        )
        self.head = nn.Conv2d(
            hidden_channels,
            forecast_len * in_channels,
            kernel_size=1,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() != 5:
            raise ValueError(f"expected (B,T,C,H,W), got {tuple(x.shape)}")
        b, _, _, h, w = x.shape
        seq = x.permute(1, 0, 2, 3, 4).contiguous()
        h_last = self.encoder(seq)
        out = self.head(h_last)
        return out.view(b, self.forecast_len, self.in_channels, h, w)
