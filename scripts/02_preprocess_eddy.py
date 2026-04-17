"""涡旋任务预处理：raw -> 训练可用（clean + META4 标签 + split + stats）。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_preprocessing.task_pipelines import PipelineOptions, run_eddy_raw_to_train_ready
from utils.logger import setup_logging


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Eddy preprocessing pipeline (raw -> train-ready, META4 labels)")
    ap.add_argument("--config", type=Path, default=ROOT / "configs/data_config.yaml")
    ap.add_argument("--limit", type=int, default=None, help="最多处理的 raw 文件数（调试）")
    ap.add_argument("-j", "--workers", type=int, default=1, help="清洗并行进程数")
    ap.add_argument("--skip-labels", action="store_true", help="跳过 META4 标签生成（仅 clean + split + stats）")
    ap.add_argument("--merge", action="store_true", help="额外生成 eddy merged clean 文件")
    ap.add_argument("--validate", action="store_true", help="完成后执行预处理产物校验")
    ap.add_argument("--validate-limit", type=int, default=None, help="校验抽检样本上限")
    ap.add_argument(
        "--pet-src",
        type=Path,
        default=None,
        help="py-eddy-tracker 源码 src 目录（默认自动探测项目内 py-eddy-tracker-master）",
    )
    ap.add_argument(
        "--meta4-overwrite",
        action="store_true",
        help="META4 标签已存在时仍覆盖重算（02c/02h 的 --overwrite）",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(log_file=ROOT / "outputs/logs/preprocess_eddy.log")
    run_eddy_raw_to_train_ready(
        PipelineOptions(
            config_path=args.config,
            root=ROOT,
            limit=args.limit,
            workers=args.workers,
            validate=args.validate,
            validate_limit=args.validate_limit,
        ),
        build_labels=not args.skip_labels,
        pet_src=args.pet_src,
        meta4_overwrite=args.meta4_overwrite,
        merge_clean_files=args.merge,
    )


if __name__ == "__main__":
    main()
