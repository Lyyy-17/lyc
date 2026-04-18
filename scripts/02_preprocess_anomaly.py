"""异常任务预处理：raw -> 训练可用（clean + split + stats）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_preprocessing.task_pipelines import PipelineOptions, run_anomaly_raw_to_train_ready
from utils.logger import setup_logging


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Anomaly preprocessing pipeline (raw -> train-ready)")
    ap.add_argument("--config", type=Path, default=ROOT / "configs/data_config.yaml")
    ap.add_argument("--limit", type=int, default=None, help="最多处理的 raw 年份数（调试）")
    ap.add_argument("-j", "--workers", type=int, default=1, help="清洗并行进程数")
    ap.add_argument("--merge", action="store_true", help="额外生成 anomaly merged 文件")
    ap.add_argument("--validate", action="store_true", help="完成后执行预处理产物校验")
    ap.add_argument("--validate-limit", type=int, default=None, help="校验抽检样本上限")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(log_file=ROOT / "outputs/logs/preprocess_anomaly.log")
    run_anomaly_raw_to_train_ready(
        PipelineOptions(
            config_path=args.config,
            root=ROOT,
            limit=args.limit,
            workers=args.workers,
            validate=args.validate,
            validate_limit=args.validate_limit,
        ),
        merge_clean_files=args.merge,
    )


if __name__ == "__main__":
    main()

