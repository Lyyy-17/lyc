# OceanRace — Agent / 协作说明

## 日志

本项目统一使用 **`src/utils/logger.py`**，请勿在业务代码里用 `print` 代替正式日志。

- 模块内：`from utils.logger import get_logger` → `logger = get_logger(__name__)`。
- 程序入口最早调用：`from utils.logger import setup_logging` → `setup_logging()`；可选写入 `outputs/logs/...`。
- 环境变量：`OCEAN_LOG_LEVEL`（默认 `INFO`）。

详见 `src/utils/README.md` 中「logger」小节。进度条与日志并存时：``from utils.logger import tqdm, tqdm_logging``，在 ``with tqdm_logging():`` 内使用 ``tqdm(...)``。Cursor 规则见 `.cursor/rules/logging.mdc`。
