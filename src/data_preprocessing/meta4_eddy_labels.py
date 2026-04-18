"""META4 像素级标签：对每个 `*_clean.nc` 调用 `02c` + `02h` 生成 `*_label_meta4_mask_bg0.nc`。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from data_preprocessing.splitter import list_processed_eddy
from utils.logger import get_logger

logger = get_logger(__name__)


def _default_pet_src(root: Path) -> Path:
    candidates = [
        root / "py-eddy-tracker-master" / "py-eddy-tracker-master" / "src",
        root / "py-eddy-tracker-master" / "src",
        root.parent / "py-eddy-tracker-master" / "py-eddy-tracker-master" / "src",
        root.parent / "py-eddy-tracker-master" / "src",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def run_meta4_mask_bg0_for_clean_files(
    cfg: Mapping[str, Any],
    root: Path,
    *,
    pet_src: Path | None = None,
    overwrite: bool = False,
) -> int:
    """对 `list_processed_eddy` 中每个 clean 文件生成 META4 标签并修复背景为 0。

    产出：
    - ``labels/<stem>_label_meta4.nc``（中间文件，含完整 META4 变量）
    - ``labels/<stem>_label_meta4_mask_bg0.nc``（训练用，仅 ``eddy_mask``，背景为 0）
    """
    root = root.resolve()
    scripts_dir = root / "scripts"
    c_script = scripts_dir / "02c_generate_meta4_labels.py"
    h_script = scripts_dir / "02h_fix_meta4_mask_background.py"
    if not c_script.is_file():
        raise FileNotFoundError(f"missing {c_script}")
    if not h_script.is_file():
        raise FileNotFoundError(f"missing {h_script}")

    pet = pet_src if pet_src is not None else _default_pet_src(root)
    processed = list_processed_eddy(cfg, root)
    labels_dir = root / cfg["paths"]["processed"]["eddy"] / "labels"
    labels_dir.mkdir(parents=True, exist_ok=True)

    n = 0
    for clean_path in processed:
        stem = clean_path.name.replace("_clean.nc", "")
        meta4_nc = labels_dir / f"{stem}_label_meta4.nc"
        bg0_nc = labels_dir / f"{stem}_label_meta4_mask_bg0.nc"

        cmd_c = [
            sys.executable,
            str(c_script),
            "--clean-nc",
            str(clean_path),
            "--out-nc",
            str(meta4_nc),
            "--pet-src",
            str(pet),
        ]
        if overwrite:
            cmd_c.append("--overwrite")
        logger.info("META4 02c: %s", " ".join(cmd_c))
        subprocess.run(cmd_c, cwd=str(root), check=True)

        cmd_h = [
            sys.executable,
            str(h_script),
            "--input-nc",
            str(meta4_nc),
            "--output-nc",
            str(bg0_nc),
        ]
        if overwrite:
            cmd_h.append("--overwrite")
        logger.info("META4 02h: %s", " ".join(cmd_h))
        subprocess.run(cmd_h, cwd=str(root), check=True)
        n += 1

    return n
