"""utils.logger：setup_logging、get_logger、文件落盘、reset_logging。"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from utils.logger import get_logger, reset_logging, setup_logging


@pytest.fixture(autouse=True)
def _reset_logger_state() -> None:
    """每个用例前后清理全局 logging 状态，避免影响其它测试。"""
    reset_logging()
    yield
    reset_logging()


def test_setup_and_get_logger_emits() -> None:
    setup_logging(level="INFO", force=True)
    log = get_logger("test_logger_smoke")
    log.info("hello %s", "world")
    # 不应抛错；根 logger 应有 handler
    root = logging.getLogger()
    assert len(root.handlers) >= 1


def test_log_file_plain_text(tmp_path: Path) -> None:
    log_path = tmp_path / "run.log"
    setup_logging(level="DEBUG", log_file=log_path, force=True)
    log = get_logger("file_test")
    log.warning("warn_line")
    assert log_path.is_file()
    text = log_path.read_text(encoding="utf-8")
    assert "warn_line" in text
    assert "file_test" in text
    # 文件 handler 使用无 ANSI 的 Formatter，不应含 ESC
    assert "\033[" not in text


def test_force_reconfigure(tmp_path: Path) -> None:
    setup_logging(level="WARNING", force=True)
    log = get_logger("lvl")
    log.info("hidden")  # 低于 WARNING，不应出现在 root 的有效输出里（取决于 handler）
    setup_logging(level="DEBUG", log_file=tmp_path / "a.log", force=True)
    log2 = get_logger("lvl2")
    log2.debug("visible_debug")
    assert (tmp_path / "a.log").read_text(encoding="utf-8").count("visible_debug") >= 1


def test_ocean_log_level_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OCEAN_LOG_LEVEL", "ERROR")
    setup_logging(level=None, force=True)
    log = get_logger("envlvl")
    log.warning("should_not_in_root_effective")  # ERROR 以下可能被过滤
    root = logging.getLogger()
    # 根级别应为 ERROR
    assert root.level == logging.ERROR
