"""
在项目根目录一键启动 Web：FastAPI 后端 +（默认同时）Vite 前端开发服。

用法（均在仓库根目录执行）::

    python scripts/07_web_run.py
    python scripts/07_web_run.py --backend-only
    python scripts/07_web_run.py --frontend-only
    python scripts/07_web_run.py --backend-port 8000 --frontend-port 5173

依赖：后端需已安装 ``src/web/backend/requirements.txt``；前端需在 ``src/web/frontend`` 下执行过 ``npm install``。
"""
from __future__ import annotations

import argparse
import atexit
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "web" / "frontend"

_procs: list[tuple[str, subprocess.Popen]] = []


def _terminate_all() -> None:
    for _name, p in _procs:
        if p.poll() is None:
            p.terminate()
    for _name, p in _procs:
        if p.poll() is None:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


def _register_cleanup() -> None:
    atexit.register(_terminate_all)

    def _handle_sig(_sig: int, _frame: object) -> None:
        _terminate_all()
        sys.exit(130)

    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _handle_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_sig)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="启动 OceanRace Web 后端与/或前端开发服")
    p.add_argument("--backend-host", default="127.0.0.1", help="uvicorn 监听地址")
    p.add_argument("--backend-port", type=int, default=8000, help="uvicorn 端口")
    p.add_argument("--frontend-host", default="127.0.0.1", help="Vite dev 监听地址")
    p.add_argument("--frontend-port", type=int, default=5173, help="Vite dev 端口")
    p.add_argument(
        "--no-reload",
        action="store_true",
        help="关闭 uvicorn --reload（默认开启，便于改后端代码热重载）",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--backend-only",
        action="store_true",
        help="仅启动 FastAPI",
    )
    mode.add_argument(
        "--frontend-only",
        action="store_true",
        help="仅启动 Vite（需自行已启动后端）",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    _register_cleanup()

    if not FRONTEND.is_dir():
        print(f"[07_web_run] 未找到前端目录: {FRONTEND}", file=sys.stderr)
        return 1

    run_backend = not args.frontend_only
    run_frontend = not args.backend_only

    if run_backend:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "src.web.backend.app.main:app",
            "--host",
            args.backend_host,
            "--port",
            str(args.backend_port),
        ]
        if not args.no_reload:
            cmd.append("--reload")
        print(
            f"[07_web_run] 后端: {' '.join(cmd)}  (cwd={ROOT})",
            flush=True,
        )
        _procs.append(
            (
                "backend",
                subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    env={**os.environ},
                ),
            )
        )

    if run_frontend:
        npm = shutil.which("npm")
        if not npm:
            print("[07_web_run] 未找到 npm，请先安装 Node.js。", file=sys.stderr)
            _terminate_all()
            return 1
        fcmd = [
            npm,
            "run",
            "dev",
            "--",
            "--host",
            args.frontend_host,
            "--port",
            str(args.frontend_port),
        ]
        print(
            f"[07_web_run] 前端: {' '.join(fcmd)}  (cwd={FRONTEND})",
            flush=True,
        )
        _procs.append(
            (
                "frontend",
                subprocess.Popen(
                    fcmd,
                    cwd=str(FRONTEND),
                    env={**os.environ},
                ),
            )
        )

    if not _procs:
        return 0

    print(
        "[07_web_run] 已启动；Ctrl+C 结束本脚本会尝试结束子进程。"
        + (f" 后端 API: http://{args.backend_host}:{args.backend_port}/docs" if run_backend else "")
        + (
            f"  前端: http://{args.frontend_host}:{args.frontend_port}/"
            if run_frontend
            else ""
        ),
        flush=True,
    )

    try:
        while True:
            for name, proc in _procs:
                code = proc.poll()
                if code is not None:
                    print(f"[07_web_run] 子进程退出 ({name}) code={code}", flush=True)
                    return int(code if code is not None else 1)
            time.sleep(0.4)
    except KeyboardInterrupt:
        print("\n[07_web_run] KeyboardInterrupt，正在结束子进程…", flush=True)
        _terminate_all()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
