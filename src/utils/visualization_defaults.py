"""
本项目 matplotlib 可视化统一约定（图幅、DPI、字号、色图、线宽、网格等）。

在脚本或 notebook 入口调用一次 :func:`apply_matplotlib_defaults` 即可与仓库内其它图保持一致；
仅需个别常量时用 ``from utils.visualization_defaults import DEFAULT_FIGSIZE, ...``。
"""
from __future__ import annotations

from typing import Any

# --- 图幅与导出 ---
DEFAULT_FIGSIZE: tuple[float, float] = (9.0, 6.0)
DEFAULT_DPI: int = 150

# --- 色图（语义分离，避免混用）---
DEFAULT_CMAP: str = "viridis"
DEFAULT_CMAP_SEQUENTIAL: str = "viridis"
DEFAULT_CMAP_DIVERGING: str = "RdBu_r"

# --- 字号（pt，与 matplotlib rcParams 一致）---
DEFAULT_FONT_SIZE: float = 11.0
TITLE_FONT_SIZE: float = 12.0
AXIS_LABEL_FONT_SIZE: float = 11.0
TICK_FONT_SIZE: float = 10.0
LEGEND_FONT_SIZE: float = 10.0

# --- 线、点 ---
DEFAULT_LINEWIDTH: float = 1.5
DEFAULT_MARKERSIZE: float = 5.0

# --- 坐标轴与网格 ---
DEFAULT_GRID_ALPHA: float = 0.3
DEFAULT_AXES_FACECOLOR: str = "white"
DEFAULT_FIGURE_FACECOLOR: str = "white"


def apply_matplotlib_defaults() -> None:
    """将常用 rcParams 设为项目约定（幂等；建议在入口或首次绘图前调用一次）。"""
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "figure.figsize": DEFAULT_FIGSIZE,
            "figure.facecolor": DEFAULT_FIGURE_FACECOLOR,
            "figure.dpi": 100,
            "savefig.dpi": DEFAULT_DPI,
            "savefig.facecolor": DEFAULT_FIGURE_FACECOLOR,
            "image.cmap": DEFAULT_CMAP,
            "font.size": DEFAULT_FONT_SIZE,
            "axes.titlesize": TITLE_FONT_SIZE,
            "axes.labelsize": AXIS_LABEL_FONT_SIZE,
            "axes.facecolor": DEFAULT_AXES_FACECOLOR,
            "axes.grid": True,
            "xtick.labelsize": TICK_FONT_SIZE,
            "ytick.labelsize": TICK_FONT_SIZE,
            "legend.fontsize": LEGEND_FONT_SIZE,
            "grid.alpha": DEFAULT_GRID_ALPHA,
            "grid.linestyle": "--",
            "lines.linewidth": DEFAULT_LINEWIDTH,
            "lines.markersize": DEFAULT_MARKERSIZE,
        }
    )


def standard_savefig_kwargs() -> dict[str, Any]:
    """与 :func:`apply_matplotlib_defaults` 配套的 ``fig.savefig(**kwargs)`` 推荐参数。"""
    return {
        "dpi": DEFAULT_DPI,
        "bbox_inches": "tight",
        "facecolor": DEFAULT_FIGURE_FACECOLOR,
    }


def slice_plot_kwargs() -> dict[str, Any]:
    """二维格点场单帧图与 :func:`apply_matplotlib_defaults` 一致的 ``figsize`` / ``dpi`` / ``cmap``。"""
    return {"figsize": DEFAULT_FIGSIZE, "dpi": DEFAULT_DPI, "cmap": DEFAULT_CMAP}


__all__ = [
    "DEFAULT_FIGSIZE",
    "DEFAULT_DPI",
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
    "DEFAULT_GRID_ALPHA",
    "DEFAULT_AXES_FACECOLOR",
    "DEFAULT_FIGURE_FACECOLOR",
    "apply_matplotlib_defaults",
    "standard_savefig_kwargs",
    "slice_plot_kwargs",
]
