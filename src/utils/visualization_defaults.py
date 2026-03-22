"""
本项目 matplotlib 可视化统一约定（图幅、DPI、字号、色图、线宽、网格等）。

在脚本或 notebook 入口调用一次 :func:`apply_matplotlib_defaults` 即可与仓库内其它图保持一致；
仅需个别常量时用 ``from utils.visualization_defaults import DEFAULT_FIGSIZE, ...``。
"""
from __future__ import annotations

from typing import Any

# --- 图幅与导出 ---
DEFAULT_FIGSIZE: tuple[float, float] = (10.0, 6.0)  # 稍微加宽一点，更符合现代宽屏和黄金比例
DEFAULT_DPI_DISPLAY: int = 150  # 屏幕内联显示的 DPI (适配高分屏)
DEFAULT_DPI_SAVE: int = 300     # 保存高质量图片 (出版/报告级别)
# 兼容旧代码：曾用 DEFAULT_DPI 表示保存图时的 DPI
DEFAULT_DPI: int = DEFAULT_DPI_SAVE

# --- 色图与颜色循环（现代感配色）---
# 分类色板：类似 Seaborn deep，柔和且区分度高
DEFAULT_COLOR_CYCLE: list[str] = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3", 
    "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"
]
DEFAULT_CMAP: str = "viridis"
DEFAULT_CMAP_SEQUENTIAL: str = "viridis"
DEFAULT_CMAP_DIVERGING: str = "RdBu_r"

# --- 字号（pt，拉开视觉层级）---
DEFAULT_FONT_SIZE: float = 12.0
TITLE_FONT_SIZE: float = 14.0       # 标题更醒目
AXIS_LABEL_FONT_SIZE: float = 12.0  # 轴标签清晰
TICK_FONT_SIZE: float = 11.0        # 刻度适中
LEGEND_FONT_SIZE: float = 11.0

# --- 线、点 ---
DEFAULT_LINEWIDTH: float = 2.0      # 提升线条粗细，让数据更突出
DEFAULT_MARKERSIZE: float = 6.0

# --- 坐标轴与网格 ---
DEFAULT_GRID_COLOR: str = "#E5E5E5" # 浅灰色网格
DEFAULT_AXES_FACECOLOR: str = "white"
DEFAULT_FIGURE_FACECOLOR: str = "white"


def apply_matplotlib_defaults() -> None:
    """将常用 rcParams 设为项目约定（幂等；建议在入口或首次绘图前调用一次）。"""
    import matplotlib as mpl
    from cycler import cycler

    mpl.rcParams.update(
        {
            # 图幅与分辨率
            "figure.figsize": DEFAULT_FIGSIZE,
            "figure.facecolor": DEFAULT_FIGURE_FACECOLOR,
            "figure.dpi": DEFAULT_DPI_DISPLAY,
            "savefig.dpi": DEFAULT_DPI_SAVE,
            "savefig.facecolor": DEFAULT_FIGURE_FACECOLOR,
            "savefig.bbox": "tight",  # 默认紧凑保存，防止标签被截断
            
            # 颜色与色图
            "image.cmap": DEFAULT_CMAP,
            "axes.prop_cycle": cycler(color=DEFAULT_COLOR_CYCLE),
            
            # 字体大小 (建议考虑配置 font.family 为 sans-serif 如 Arial)
            "font.size": DEFAULT_FONT_SIZE,
            "axes.titlesize": TITLE_FONT_SIZE,
            "axes.titlepad": 12.0,    # 让标题和图表拉开一点呼吸感
            "axes.labelsize": AXIS_LABEL_FONT_SIZE,
            "axes.labelpad": 8.0,
            "xtick.labelsize": TICK_FONT_SIZE,
            "ytick.labelsize": TICK_FONT_SIZE,
            "legend.fontsize": LEGEND_FONT_SIZE,
            "legend.frameon": False,  # 移除图例边框，显得更干净
            
            # 坐标轴与线条
            "axes.facecolor": DEFAULT_AXES_FACECOLOR,
            "axes.linewidth": 1.0,
            "lines.linewidth": DEFAULT_LINEWIDTH,
            "lines.markersize": DEFAULT_MARKERSIZE,
            
            # 去除图表顶部和右侧的“盒子感”边框 (极简风核心)
            "axes.spines.top": False,
            "axes.spines.right": False,
            
            # 网格 (使用浅色实线代替虚线，减少视觉噪音)
            "axes.grid": True,
            "axes.grid.axis": "both", # 视需求可改为 'y' 仅保留水平网格
            "grid.color": DEFAULT_GRID_COLOR,
            "grid.linestyle": "-",
            "grid.linewidth": 0.8,
            "grid.alpha": 1.0,
            
            # 刻度线向外，看起来更规整
            "xtick.direction": "out",
            "ytick.direction": "out",
        }
    )


def standard_savefig_kwargs() -> dict[str, Any]:
    """与 :func:`apply_matplotlib_defaults` 配套的 ``fig.savefig(**kwargs)`` 推荐参数。"""
    return {
        "dpi": DEFAULT_DPI_SAVE,
        "bbox_inches": "tight",
        "facecolor": DEFAULT_FIGURE_FACECOLOR,
        # 可以视需要加上 "transparent": False
    }


def slice_plot_kwargs() -> dict[str, Any]:
    """二维格点场单帧图与 :func:`apply_matplotlib_defaults` 一致的参数推荐。"""
    return {
        "figsize": DEFAULT_FIGSIZE, 
        "dpi": DEFAULT_DPI_DISPLAY, 
        "cmap": DEFAULT_CMAP
    }


__all__ = [
    "DEFAULT_FIGSIZE",
    "DEFAULT_DPI",
    "DEFAULT_DPI_DISPLAY",
    "DEFAULT_DPI_SAVE",
    "DEFAULT_COLOR_CYCLE",
    "DEFAULT_CMAP",
    "DEFAULT_CMAP_SEQUENTIAL",
    "DEFAULT_CMAP_DIVERGING",
    "DEFAULT_FONT_SIZE",
    "TITLE_FONT_SIZE",
    "AXIS_LABEL_FONT_SIZE",
    "TICK_FONT_SIZE",
    "LEGEND_FONT_SIZE",
    "DEFAULT_LINEWIDTH",
    "DEFAULT_MARKERSIZE",
    "DEFAULT_GRID_COLOR",
    "DEFAULT_AXES_FACECOLOR",
    "DEFAULT_FIGURE_FACECOLOR",
    "apply_matplotlib_defaults",
    "standard_savefig_kwargs",
    "slice_plot_kwargs",
]