"""
要素预报 ConvLSTM 基线训练入口。

在项目根目录、``PYTHONPATH=src``::

    python -m baseline.element_forecasting.train --epochs 2 --batch-size 1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from .model import ElementForecastConvLSTMBaseline  # noqa: E402
from .sequence_dataset import ElementForecastSequenceDataset  # noqa: E402
from utils.logger import get_logger, setup_logging, tqdm, tqdm_logging  # noqa: E402

_log = get_logger(__name__)


def _collate(batch: list[dict]) -> dict:
    x = torch.stack([b["x"] for b in batch], dim=0)
    y = torch.stack([b["y"] for b in batch], dim=0)
    return {"x": x, "y": y, "paths": [b["path"] for b in batch]}


def main() -> None:
    ap = argparse.ArgumentParser(description="要素预报 ConvLSTM 基线训练")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--input-len", type=int, default=12)
    ap.add_argument("--forecast-len", type=int, default=12)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument(
        "--norm",
        type=Path,
        default=ROOT / "data/processed/normalization/element_forecasting_norm.json",
        help="训练集 mean/std JSON；不存在则不做逐变量标准化",
    )
    ap.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="覆盖默认 data/processed/splits/element_forecasting.json（极少样本冒烟测试等）",
    )
    args = ap.parse_args()
    setup_logging()

    norm_path = args.norm if args.norm.is_file() else None
    if norm_path is None:
        _log.warning("norm file missing, training without per-variable standardization: %s", args.norm)

    man_kw: dict = {
        "input_len": args.input_len,
        "forecast_len": args.forecast_len,
        "norm_stats_path": norm_path,
        "root": ROOT,
    }
    if args.manifest is not None:
        man_kw["manifest_path"] = args.manifest

    train_ds = ElementForecastSequenceDataset(split="train", **man_kw)
    val_ds = ElementForecastSequenceDataset(split="val", **man_kw)
    if len(train_ds) == 0:
        raise SystemExit(
            "train dataset empty: run scripts/02_preprocess.py with split/stats, "
            "or check element_forecasting split manifest and time length >= input_len+forecast_len."
        )

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=_collate,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        collate_fn=_collate,
        num_workers=0,
    )

    in_ch = train_ds[0]["x"].shape[1]
    model = ElementForecastConvLSTMBaseline(
        in_channels=in_ch,
        hidden_channels=args.hidden,
        num_layers=args.layers,
        forecast_len=args.forecast_len,
    ).to(args.device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()

    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        n = 0
        with tqdm_logging():
            for batch in tqdm(train_loader, desc=f"epoch {epoch+1}/{args.epochs} train"):
                x = batch["x"].to(args.device)
                y = batch["y"].to(args.device)
                opt.zero_grad(set_to_none=True)
                pred = model(x)
                loss = loss_fn(pred, y)
                loss.backward()
                opt.step()
                total += float(loss.item()) * x.size(0)
                n += x.size(0)
        _log.info("train mse: %.6f", total / max(n, 1))

        if len(val_ds) == 0:
            _log.warning("val dataset empty, skip val metrics")
            continue

        model.eval()
        v_total = 0.0
        v_n = 0
        with torch.no_grad():
            for batch in val_loader:
                x = batch["x"].to(args.device)
                y = batch["y"].to(args.device)
                pred = model(x)
                loss = loss_fn(pred, y)
                v_total += float(loss.item()) * x.size(0)
                v_n += x.size(0)
        _log.info("val mse: %.6f", v_total / max(v_n, 1))


if __name__ == "__main__":
    main()
