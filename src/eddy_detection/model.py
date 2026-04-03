"""涡旋分割 baseline：轻量 U-Net。"""
from __future__ import annotations

import torch
import torch.nn as nn


class DoubleConv(nn.Module):
	"""Conv-BN-ReLU x2。"""

	def __init__(self, in_channels: int, out_channels: int):
		super().__init__()
		self.block = nn.Sequential(
			nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
			nn.BatchNorm2d(out_channels),
			nn.ReLU(inplace=True),
			nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
			nn.BatchNorm2d(out_channels),
			nn.ReLU(inplace=True),
		)

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		return self.block(x)


class Down(nn.Module):
	"""下采样阶段：MaxPool + DoubleConv。"""

	def __init__(self, in_channels: int, out_channels: int):
		super().__init__()
		self.block = nn.Sequential(nn.MaxPool2d(2), DoubleConv(in_channels, out_channels))

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		return self.block(x)


class Up(nn.Module):
	"""上采样阶段：双线性插值 + skip concat + DoubleConv。"""

	def __init__(self, in_channels: int, out_channels: int):
		super().__init__()
		self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
		self.conv = DoubleConv(in_channels, out_channels)

	def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
		x = self.up(x)
		# 保证拼接前空间大小一致
		if x.shape[-2:] != skip.shape[-2:]:
			x = nn.functional.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)
		x = torch.cat([skip, x], dim=1)
		return self.conv(x)


class UNetEddy(nn.Module):
	"""用于海洋涡旋识别的 U-Net baseline。"""

	def __init__(
		self,
		in_channels: int = 3,
		num_classes: int = 1,
		base_channels: int = 32,
	):
		super().__init__()
		c = base_channels
		self.inc = DoubleConv(in_channels, c)
		self.down1 = Down(c, c * 2)
		self.down2 = Down(c * 2, c * 4)
		self.down3 = Down(c * 4, c * 8)
		self.bottleneck = Down(c * 8, c * 16)

		self.up1 = Up(c * 16 + c * 8, c * 8)
		self.up2 = Up(c * 8 + c * 4, c * 4)
		self.up3 = Up(c * 4 + c * 2, c * 2)
		self.up4 = Up(c * 2 + c, c)
		self.out_conv = nn.Conv2d(c, num_classes, kernel_size=1)

	def forward(self, x: torch.Tensor) -> torch.Tensor:
		x1 = self.inc(x)
		x2 = self.down1(x1)
		x3 = self.down2(x2)
		x4 = self.down3(x3)
		xb = self.bottleneck(x4)

		x = self.up1(xb, x4)
		x = self.up2(x, x3)
		x = self.up3(x, x2)
		x = self.up4(x, x1)
		return self.out_conv(x)
