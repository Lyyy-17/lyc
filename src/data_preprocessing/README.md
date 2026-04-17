# `src/data_preprocessing` 说明

本包实现：**清洗**（`cleaner.py`）、**整合**（`merger.py`）、**划分与训练集标准化**（`splitter.py`）、**I/O**（`io.py`）、**校验**（`validator.py`）、**配置回写**（`config_sync.py`）、**任务流水线**（[`task_pipelines.py`](task_pipelines.py)）及并行 worker（`preprocess_workers.py`）。命令行入口为项目根目录 [`scripts/02_preprocess_eddy.py`](../../scripts/02_preprocess_eddy.py) / [`02_preprocess_element.py`](../../scripts/02_preprocess_element.py) / [`02_preprocess_anomaly.py`](../../scripts/02_preprocess_anomaly.py)，以及 [`sync_data_config.py`](../../scripts/sync_data_config.py)、[`validate_processed.py`](../../scripts/validate_processed.py)。

运行脚本或导入本包前，在项目根目录将 `src` 加入 `PYTHONPATH`（PowerShell：`$env:PYTHONPATH = "src"`）。日志约定见 [`../utils/README.md`](../utils/README.md)。

更细的 **原始 NetCDF 维度与文件名** 见 [`../../data/raw/README.md`](../../data/raw/README.md)。

---

## 1. 三任务目录约定（`data/raw` → `data/processed`）

路径根均相对于**项目根目录**；与 [`configs/data_config.yaml`](../../configs/data_config.yaml) 中 `paths.raw` / `paths.processed` 一一对应（默认如下）。

| 任务（预处理脚本） | 配置键 `paths.raw.*` / `paths.processed.*` | splitter 内部任务名 | 原始数据形态 | 清洗后产出 |
|----------------------|--------------------------------------------|----------------------|--------------|------------|
| `eddy` | `eddy` → `eddy_detection/` | `eddy` | `*.nc` 平铺在 `data/raw/eddy_detection/` | `data/processed/eddy_detection/*_clean.nc` |
| `element` | `element_forecasting` → `element_forecasting/` | `element_forecasting` | `YYYYMMDD.nc` 在 `data/raw/element_forecasting/` | `data/processed/element_forecasting/*_clean.nc` |
| `anomaly` | `anomaly` → `anomaly_detection/` | `anomaly_detection` | 按年子目录 `YYYY/`，内含 `data_stream-oper_stepType-instant.nc` 与 `data_stream-wave_stepType-instant.nc` | 每年目录下 `oper_clean.nc` 与 `wave_clean.nc`（`data/processed/anomaly_detection/YYYY/`） |

**划分与标准化产物（三任务共用父目录）：**

- `paths.splits`（默认 `data/processed/splits/`）：`eddy.json`、`element_forecasting.json`、`anomaly_detection.json`（内容为相对项目根的 POSIX 路径列表：`train` / `val` / `test`）。
- `paths.normalization`（默认 `data/processed/normalization/`）：`*_norm.json`（训练集上估计的各变量 `mean` / `std`）。

变量名、坐标名等细节以 `cleaner.py` 与 [`data/raw/README.md`](../../data/raw/README.md) 为准。

---

## 2. 与 `configs/data_config.yaml` 的对应关系

| 配置块 | 作用 |
|--------|------|
| `project.root` | 一般为 `.`；脚本以项目根为基准解析相对路径。 |
| `paths.raw` / `paths.processed` | 三任务 raw、processed 子目录；**必须与磁盘实际目录一致**，否则预处理脚本找不到输入或写错位置。 |
| `paths.splits` / `paths.normalization` | 划分清单与标准化 JSON 的输出目录；`splitter` / `validator` / `config_sync` 均读此处。 |
| `split.train_ratio` / `val_ratio` / `test_ratio` / `seed` | `run_split_for_task` 使用的比例与随机种子（三者之和应为 1）。 |
| `fill.eddy_float` / `fill.element` | 涡旋、要素浮点哨兵值，清洗时转为 NaN 并写 `*_valid`。异常任务风/浪用 NaN 掩膜，哨兵见 `cleaner` 内逻辑。 |
| `output.compression` / `output.complevel` | 写出 NetCDF 时压缩；`complevel` 由 worker 传入（默认 4）。 |
| `batch.max_files_eddy` / `max_files_element` / `max_files_anomaly_years` | 未传 `--limit` 时作为清洗数量上限；`null` 表示不限制。若命令行传了 `--limit`，以命令行为准。 |
| `artifacts.*` / `standardization.*` | 各任务流水线在写出 `normalization/*_norm.json` 后，由 `config_sync.merge_pipeline_artifacts_into_config` **回写**到本 YAML（清单路径、样本数、各变量 mean/std 等）。 |

仅同步配置、不跑清洗时：

```powershell
python scripts/sync_data_config.py
```

---

## 3. 命令行典型用法

均在**项目根目录**执行；脚本会把 `src` 加入 `sys.path`。更全的示例见 [`../../scripts/README.md`](../../scripts/README.md)。

| 场景 | 命令示例 |
|------|----------|
| 涡旋 raw → 可训练 | `python scripts/02_preprocess_eddy.py -j 4 --validate` |
| 要素 raw → 可训练（含 merge 出 `all_clean_merged.nc`） | `python scripts/02_preprocess_element.py -j 4 --validate` |
| 异常 raw → 可训练 | `python scripts/02_preprocess_anomaly.py -j 4 --validate` |
| 仅回写 `data_config.yaml` | `python scripts/sync_data_config.py` |
| 三任务 manifest + 抽检 | `python scripts/validate_processed.py --validate-limit 50` |

**说明：** 标准化统计会读对应任务的 `splits/*.json` 中 `train` 路径；流水线结束时会调用 `merge_pipeline_artifacts_into_config` 更新 `data_config.yaml`。

---

## 4. 源码模块一览

| 模块 | 职责 |
|------|------|
| `cleaner.py` | 单数据集清洗；`load_config` 读 YAML。 |
| `io.py` | `open_nc`；Windows 中文路径容错。 |
| `merger.py` | 将某任务清洗后文件按时间维拼接合并。 |
| `splitter.py` | 列举 processed 样本、划分、`compute_train_standardization`、写 manifest 与 norm JSON。 |
| `validator.py` | 清洗结果与划分清单质量检查。 |
| `config_sync.py` | 将磁盘上的 splits / normalization 摘要合并回 `data_config.yaml`。 |
| `preprocess_workers.py` | 供多进程调用的单文件/单年清洗函数。 |
| `task_pipelines.py` | 三任务「raw → clean →（可选 merge/标签）→ split → stats」编排。 |
| `meta4_eddy_labels.py` | 涡旋：对每个 `*_clean.nc` 调用 `02c`+`02h` 生成 `*_label_meta4_mask_bg0.nc`。 |

---

## 5. 回归测试

在项目根目录执行 `pytest`（需安装 `pytest`，见根目录 `requirements.txt`）。`tests/` 对 `cleaner`、`io`、`splitter`、`validator` 使用迷你 NetCDF 与临时目录做回归；修改上述模块后建议跑一遍。

```powershell
python -m pytest tests -q
```
