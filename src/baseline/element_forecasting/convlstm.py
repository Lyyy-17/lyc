"""多层 ConvLSTM 编码器（时空序列）。"""
from __future__ import annotations

import torch
import torch.nn as nn


class ConvLSTMCell(nn.Module):
    """单步 ConvLSTM，输入与上一时刻隐状态在通道维拼接后卷积。"""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        kernel_size: int | tuple[int, int],
    ) -> None:
        super().__init__()
        self.hidden_channels = hidden_channels
        if isinstance(kernel_size, tuple):
            kh, kw = kernel_size
            padding = (kh // 2, kw // 2)
        else:
            kh = kw = kernel_size
            padding = kh // 2
        self._conv = nn.Conv2d(
            in_channels + hidden_channels,
            4 * hidden_channels,
            kernel_size,
            padding=padding,
        )

    def forward(
        self,
        x: torch.Tensor,
        h: torch.Tensor,
        c: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        combined = torch.cat([x, h], dim=1)
        gates = self._conv(combined)
        i, f, g, o = torch.chunk(gates, 4, dim=1)
        i = torch.sigmoid(i)
        f = torch.sigmoid(f)
        g = torch.tanh(g)
        o = torch.sigmoid(o)
        c_next = f * c + i * g
        h_next = o * torch.tanh(c_next)
        return h_next, c_next


class ConvLSTMEncoder(nn.Module):
    """多层 ConvLSTM 沿时间展开；层间为同一时刻上前一层输出作为下一层输入。"""

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        kernel_size: int = 3,
        num_layers: int = 2,
    ) -> None:
        super().__init__()
        self.num_layers = num_layers
        self.hidden_channels = hidden_channels
        cells: list[ConvLSTMCell] = []
        for layer in range(num_layers):
            inc = in_channels if layer == 0 else hidden_channels
            cells.append(ConvLSTMCell(inc, hidden_channels, kernel_size))
        self.cells = nn.ModuleList(cells)

    def forward(self, x_seq: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        x_seq
            ``(T, B, C, H, W)`` 输入序列。

        Returns
        -------
        最后一层、最后一个时间步的隐状态 ``(B, hidden_channels, H, W)``。
        """
        t_steps, b, _, h, w = x_seq.shape
        device = x_seq.device
        dtype = x_seq.dtype
        h_states: list[torch.Tensor | None] = [None] * self.num_layers
        c_states: list[torch.Tensor | None] = [None] * self.num_layers

        for t in range(t_steps):
            layer_ins: list[torch.Tensor] = []
            for layer in range(self.num_layers):
                if layer == 0:
                    inp = x_seq[t]
                else:
                    inp = layer_ins[layer - 1]
                if h_states[layer] is None:
                    h_states[layer] = torch.zeros(
                        b, self.hidden_channels, h, w, device=device, dtype=dtype
                    )
                    c_states[layer] = torch.zeros_like(h_states[layer])
                assert h_states[layer] is not None and c_states[layer] is not None
                h_states[layer], c_states[layer] = self.cells[layer](
                    inp, h_states[layer], c_states[layer]
                )
                layer_ins.append(h_states[layer])

        assert h_states[-1] is not None
        return h_states[-1]
