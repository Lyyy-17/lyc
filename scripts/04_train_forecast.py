"""
要素预报基线训练入口。项目根目录执行::

  python scripts/04_train_forecast.py --epochs 5 --batch-size 2
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from baseline.element_forecasting.train import main  # noqa: E402

if __name__ == "__main__":
    main()
