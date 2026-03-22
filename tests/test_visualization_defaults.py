"""utils.visualization_defaults：导入与最小出图冒烟。"""
from __future__ import annotations

import os
import tempfile

import pytest

pytest.importorskip("matplotlib")


def test_apply_and_savefig() -> None:
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from utils.visualization_defaults import (
        DEFAULT_DPI,
        DEFAULT_DPI_SAVE,
        apply_matplotlib_defaults,
        slice_plot_kwargs,
        standard_savefig_kwargs,
    )

    assert DEFAULT_DPI == DEFAULT_DPI_SAVE
    apply_matplotlib_defaults()
    fig, ax = plt.subplots()
    ax.plot([0, 1], [1, 0])
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        fig.savefig(path, **standard_savefig_kwargs())
        assert os.path.getsize(path) > 50
    finally:
        os.unlink(path)
    assert "figsize" in slice_plot_kwargs()
    assert "cmap" in slice_plot_kwargs()
