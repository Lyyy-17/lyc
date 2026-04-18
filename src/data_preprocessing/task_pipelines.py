"""Task-oriented preprocess pipelines: raw -> train-ready artifacts."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from data_preprocessing.cleaner import load_config
from data_preprocessing.config_sync import merge_pipeline_artifacts_into_config
from data_preprocessing.merger import run_merge_for_task
from data_preprocessing.preprocess_workers import (
    clean_anomaly_year_one,
    clean_eddy_one,
    clean_element_one,
)
from data_preprocessing.meta4_eddy_labels import run_meta4_mask_bg0_for_clean_files
from data_preprocessing.splitter import (
    TASK_ANOMALY,
    TASK_EDDY,
    TASK_ELEMENT,
    run_split_for_task,
    run_standardization_for_task,
)
from data_preprocessing.validator import validate_manifest_and_samples
from utils.logger import get_logger, tqdm, tqdm_logging

logger = get_logger(__name__)


@dataclass
class PipelineOptions:
    config_path: Path
    root: Path
    limit: int | None = None
    workers: int = 1
    validate: bool = False
    validate_limit: int | None = None


def _run_clean_jobs(
    jobs: list[str],
    *,
    workers: int,
    desc: str,
    unit: str,
    worker_fn: Callable[..., list[str] | str],
    worker_args: tuple,
) -> None:
    with tqdm_logging():
        if workers <= 1:
            for item in tqdm(jobs, desc=desc, unit=unit):
                out = worker_fn(item, *worker_args)
                if isinstance(out, list):
                    for line in out:
                        logger.info("%s", line)
                else:
                    logger.info("%s", out)
            return

        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(worker_fn, item, *worker_args) for item in jobs]
            for fut in tqdm(as_completed(futs), total=len(futs), desc=desc, unit=unit):
                out = fut.result()
                if isinstance(out, list):
                    for line in out:
                        logger.info("%s", line)
                else:
                    logger.info("%s", out)


def _finalize_task(task: str, cfg: dict, root: Path, *, validate: bool, validate_limit: int | None) -> None:
    run_split_for_task(task, cfg, root)
    run_standardization_for_task(task, cfg, root)
    merge_pipeline_artifacts_into_config(root / "configs/data_config.yaml", root)
    if validate:
        validate_manifest_and_samples(cfg, root, check_splits=True, sample_limit=validate_limit)


def run_element_raw_to_train_ready(options: PipelineOptions, *, merge_clean_files: bool = True) -> None:
    cfg = load_config(options.config_path)
    root_s = str(options.root)
    raw = options.root / cfg["paths"]["raw"]["element_forecasting"]
    files = sorted(raw.glob("*.nc"))
    if options.limit is not None:
        files = files[: options.limit]
    comp = int(cfg.get("output", {}).get("complevel", 4))
    jobs = [str(p) for p in files]

    logger.info("element preprocess start: files=%s workers=%s", len(jobs), max(1, int(options.workers)))
    _run_clean_jobs(
        jobs,
        workers=max(1, int(options.workers)),
        desc="element 清洗",
        unit="file",
        worker_fn=clean_element_one,
        worker_args=(root_s, cfg, comp),
    )

    if merge_clean_files:
        outs = run_merge_for_task(TASK_ELEMENT, cfg, options.root, limit=options.limit)
        for p in outs:
            logger.info("element merged: %s", p.relative_to(options.root))

    _finalize_task(
        TASK_ELEMENT,
        cfg,
        options.root,
        validate=options.validate,
        validate_limit=options.validate_limit,
    )


def run_anomaly_raw_to_train_ready(options: PipelineOptions, *, merge_clean_files: bool = False) -> None:
    cfg = load_config(options.config_path)
    root_s = str(options.root)
    raw = options.root / cfg["paths"]["raw"]["anomaly"]
    years = sorted([d for d in raw.iterdir() if d.is_dir()])
    if options.limit is not None:
        years = years[: options.limit]
    comp = int(cfg.get("output", {}).get("complevel", 4))
    jobs = [str(d) for d in years]

    logger.info("anomaly preprocess start: years=%s workers=%s", len(jobs), max(1, int(options.workers)))
    _run_clean_jobs(
        jobs,
        workers=max(1, int(options.workers)),
        desc="anomaly 清洗",
        unit="year",
        worker_fn=clean_anomaly_year_one,
        worker_args=(root_s, cfg, comp),
    )

    if merge_clean_files:
        outs = run_merge_for_task(TASK_ANOMALY, cfg, options.root, limit=options.limit)
        for p in outs:
            logger.info("anomaly merged: %s", p.relative_to(options.root))

    _finalize_task(
        TASK_ANOMALY,
        cfg,
        options.root,
        validate=options.validate,
        validate_limit=options.validate_limit,
    )


def run_eddy_raw_to_train_ready(
    options: PipelineOptions,
    *,
    build_labels: bool = True,
    pet_src: Path | None = None,
    meta4_overwrite: bool = False,
    merge_clean_files: bool = False,
) -> None:
    cfg = load_config(options.config_path)
    root_s = str(options.root)
    raw = options.root / cfg["paths"]["raw"]["eddy"]
    files = sorted(raw.glob("*.nc"))
    if options.limit is not None:
        files = files[: options.limit]
    comp = int(cfg.get("output", {}).get("complevel", 4))
    jobs = [str(p) for p in files]

    logger.info("eddy preprocess start: files=%s workers=%s", len(jobs), max(1, int(options.workers)))
    _run_clean_jobs(
        jobs,
        workers=max(1, int(options.workers)),
        desc="eddy 清洗",
        unit="file",
        worker_fn=clean_eddy_one,
        worker_args=(root_s, cfg, comp),
    )

    if build_labels:
        n = run_meta4_mask_bg0_for_clean_files(
            cfg,
            options.root,
            pet_src=pet_src,
            overwrite=meta4_overwrite,
        )
        logger.info("eddy META4 labels generated for %s clean file(s)", n)

    if merge_clean_files:
        outs = run_merge_for_task(TASK_EDDY, cfg, options.root, limit=options.limit)
        for p in outs:
            logger.info("eddy merged: %s", p.relative_to(options.root))

    _finalize_task(
        TASK_EDDY,
        cfg,
        options.root,
        validate=options.validate,
        validate_limit=options.validate_limit,
    )

