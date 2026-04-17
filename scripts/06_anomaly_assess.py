"""异常检测评估统一入口：templates / ibtracs / compare。

原 05b / 05c / 05d 已并入本脚本，实现位于 src/anomaly_detection/assess/。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from anomaly_detection.assess import compare_cmd, ibtracs_cmd, templates_cmd  # noqa: E402
from utils.logger import get_logger, setup_logging  # noqa: E402

_log = get_logger(__name__)

_LOG_BY_CMD = {
    "templates": "anomaly_prepare_templates.log",
    "ibtracs": "anomaly_generate_ibtracs_labels.log",
    "compare": "anomaly_compare_methods.log",
}

_HANDLERS = {
    "templates": templates_cmd.run,
    "ibtracs": ibtracs_cmd.run,
    "compare": compare_cmd.run,
}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="异常检测评估：生成模板、IBTrACS 标签、多方法对比。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python scripts/06_anomaly_assess.py templates --splits val,test\n"
            "  python scripts/06_anomaly_assess.py ibtracs --padding-hours 12\n"
            "  python scripts/06_anomaly_assess.py compare --labels-json outputs/anomaly_detection/labels.json"
        ),
    )
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")
    templates_cmd.register_parser(sub)
    ibtracs_cmd.register_parser(sub)
    compare_cmd.register_parser(sub)
    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    cmd = str(args.command)
    log_name = _LOG_BY_CMD.get(cmd, "anomaly_assess.log")
    setup_logging(log_file=ROOT / "outputs/logs" / log_name)

    handler = _HANDLERS.get(cmd)
    if handler is None:
        _log.error("未知子命令: %s", cmd)
        return 2
    handler(args, ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
