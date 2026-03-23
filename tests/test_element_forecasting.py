"""要素预测模块单测：数据窗、模型前向、配置覆盖。"""
from __future__ import annotations

import torch

from element_forecasting.dataset import ElementForecastWindowDataset
from element_forecasting.model import HybridElementForecastModel
from element_forecasting.trainer import resolve_core_config
from tests.conftest import write_element_clean_nc


def test_dataset_cross_file_stitching_windows(tmp_path) -> None:
    d = tmp_path / "data/processed/element_forecasting"
    d.mkdir(parents=True)
    f1 = d / "19940101_clean.nc"
    f2 = d / "19940102_clean.nc"

    # file1: sst=[0,1,2], file2: sst=[10,11,12]
    write_element_clean_nc(f1, t=3, base=0.0, vars_names=("sst",))
    write_element_clean_nc(f2, t=3, base=10.0, vars_names=("sst",))

    ds_no_stitch = ElementForecastWindowDataset(
        processed_dir=d,
        var_names=("sst",),
        input_steps=2,
        output_steps=2,
        stitch_across_files=False,
        split=None,
        root=tmp_path,
    )
    assert len(ds_no_stitch) == 0

    ds_stitch = ElementForecastWindowDataset(
        processed_dir=d,
        var_names=("sst",),
        input_steps=2,
        output_steps=2,
        stitch_across_files=True,
        split=None,
        root=tmp_path,
    )
    # total t=6, need=4 => windows=3
    assert len(ds_stitch) == 3

    s = ds_stitch[1]
    x = s["x"][:, 0, 0, 0]
    y = s["y"][:, 0, 0, 0]
    # global t=1: x=[1,2], y=[10,11]，跨文件拼接成功
    assert torch.allclose(x, torch.tensor([1.0, 2.0]))
    assert torch.allclose(y, torch.tensor([10.0, 11.0]))


def test_hybrid_model_forward_shape() -> None:
    x = torch.randn(2, 4, 3, 5, 6)
    model = HybridElementForecastModel(
        in_channels=3,
        input_steps=4,
        output_steps=2,
        d_model=16,
        nhead=4,
        num_layers=2,
        block_size=4,
        enable_arima=False,
    )
    out = model(x)
    assert out["pred"].shape == (2, 2, 3, 5, 6)
    assert out["pred_transformer"].shape == (2, 2, 3, 5, 6)
    assert out["pred_arima"].shape == (2, 2, 3, 5, 6)
    assert out["fusion_weights"].shape == (2, 2)


def test_resolve_core_config_override_priority() -> None:
    model_cfg = {
        "var_names": ["m1", "m2"],
        "input_steps": 8,
        "output_steps": 4,
    }
    train_cfg = {
        "var_names": ["t1", "t2", "t3"],
        "input_steps": 10,
        "window_stride": 3,
        "stitch_across_files": False,
    }

    cfg = resolve_core_config(
        args_var_names="a,b",
        args_input_steps=12,
        args_output_steps=6,
        args_window_stride=1,
        args_stitch_across_files=True,
        train_cfg=train_cfg,
        model_cfg=model_cfg,
    )

    assert cfg["var_names"] == ("a", "b")
    assert cfg["input_steps"] == 12
    assert cfg["output_steps"] == 6
    assert cfg["window_stride"] == 1
    assert cfg["stitch_across_files"] is True

    # 不提供 CLI 时，train_cfg 优先于 model_cfg
    cfg2 = resolve_core_config(
        args_var_names=None,
        args_input_steps=None,
        args_output_steps=None,
        args_window_stride=None,
        args_stitch_across_files=None,
        train_cfg=train_cfg,
        model_cfg=model_cfg,
    )
    assert cfg2["var_names"] == ("t1", "t2", "t3")
    assert cfg2["input_steps"] == 10
    assert cfg2["output_steps"] == 4
    assert cfg2["window_stride"] == 3
    assert cfg2["stitch_across_files"] is False
