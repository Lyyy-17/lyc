# OceanRace — Agent / 协作说明

面向 **人类开发者** 与 **AI 助手（Cursor 等）**。在 Cursor 里做本仓库相关编程时，请 **@ `AGENTS.md`**（或 `@AGENTS`）将下列约定一并纳入上下文。

---

## AI 编程 Prompt（可 @ 引用）

**复制用摘要：**

1. **终端与可追踪输出**：一律用 `**utils.logger`**（`get_logger` + `setup_logging`），禁止用 `print` 作为正式运行日志。
2. **画图**：使用 `**utils.visualization_defaults`**（入口调用 `apply_matplotlib_defaults()`；按需引用 `DEFAULT_*` 常量或 `standard_savefig_kwargs()`），保持全仓库图表风格一致。
3. **代码结构**：**优先在现有目录与模块上扩展**（`src/<任务>/`、`scripts/`、`baseline/`），避免无故新增平行顶层包或散乱脚本。
4. **产出路径**：各任务的**模型 checkpoint、训练过程文件、中间图、临时指标**等，写入 `**outputs/` 下对应子目录**（见下文「outputs 目录约定」），勿往项目根目录或 `src/` 内硬编码散落大文件。
5. **配置单一来源**：**数据路径与预处理**以 `**configs/data_config.yaml`** 为准；**模型超参数**读 `**configs/<任务>/model.yaml`**；**训练参数**读 `**configs/<任务>/train.yaml`**；**要素基线**单独使用 `**configs/baseline/element_forecasting/*.yaml`**。代码中通过加载 YAML 或封装好的配置函数获取，避免魔法数与重复路径字符串。

更细的赛题与模块说明见根目录 `**README.md**`。

---

## 1. 日志（必须）

本项目统一使用 `**src/utils/logger.py**`。

- 模块内：`from utils.logger import get_logger` → `logger = get_logger(__name__)`。
- 可执行入口在解析参数后、业务逻辑前：`setup_logging()`；建议文件日志：`outputs/logs/run.log`（路径需存在则先创建父目录）。
- 环境变量：`OCEAN_LOG_LEVEL`（默认 `INFO`）。
- 进度条与日志并存：`from utils.logger import tqdm, tqdm_logging`，`with tqdm_logging():` 内使用 `tqdm(...)`。

详见 `**src/utils/README.md**`。Cursor 另见 `**.cursor/rules/logging.mdc**`。

---

## 2. 可视化（画图）

- 使用 `**src/utils/visualization_defaults.py**`：
  - 绘图前（或模块首次画图前）调用 `**apply_matplotlib_defaults()**`；
  - 保存图片时用 `**standard_savefig_kwargs()**` 与项目 DPI/背景一致；
  - 仅需个别常量时：`from utils.visualization_defaults import DEFAULT_FIGSIZE, DEFAULT_CMAP, ...`。
- 图表文件同样落入 `**outputs/` 对应子目录**（如 `outputs/element_forecasting/figures/`），**最终**对外展示可再整理到 `**outputs/final_results/<任务>/`**。

详见 `**src/utils/README.md**` 中可视化小节。

---

## 3. `outputs/` 目录约定（中间产物）

`outputs/` 默认 **gitignore**（`**outputs/final_results/`** 例外，见 `.gitignore`）。建议按任务分子目录，便于多人协作与清理：


| 路径                                      | 用途                                          |
| --------------------------------------- | ------------------------------------------- |
| `outputs/logs/`                         | 运行日志（可选，与 `setup_logging(log_file=...)` 对应） |
| `outputs/eddy_detection/`               | 涡旋任务：checkpoint、中间结果、临时图等                   |
| `outputs/element_forecasting/`          | 要素预报主任务（非基线）中间产物                            |
| `outputs/anomaly_detection/`            | 异常检测任务中间产物                                  |
| `outputs/baseline/element_forecasting/` | 要素 **基线** 训练中间产物（与主任务分开）                    |
| `outputs/final_results/<任务>/`           | **最终**对外汇报：最佳指标、定稿图表等（可提交）                  |


`**models/`**：从 `outputs/` 中挑选的**最佳权重**副本，便于版本管理与提交（见根 `README.md`）。

---

## 4. 配置（`configs/`）


| 配置                                          | 内容                                                      |
| ------------------------------------------- | ------------------------------------------------------- |
| `**configs/data_config.yaml`**              | 数据根路径、`raw`/`processed`、`splits`、划分比例、artifacts、标准化回写等  |
| `**configs/<任务>/model.yaml**`               | 该任务**模型结构/超参数**                                         |
| `**configs/<任务>/train.yaml`**               | 该任务**训练过程参数**（epoch、batch、lr、device、num_workers 等）      |
| `**configs/baseline/element_forecasting/`** | **仅**要素 ConvLSTM 基线，与 `src/element_forecasting` 主模型配置分离 |


新增或修改训练/评估代码时：**从上述文件读取**，缺省值与路径应与 YAML 一致；必要时在 argparse 中仅作为覆盖项。说明见 `**configs/README.md`**。

---

## 5. 目录与职责（结构）


| 区域             | 说明                                                               |
| -------------- | ---------------------------------------------------------------- |
| `**src/**`     | 可 import 包：`data_preprocessing`、三任务包、`baseline`、`utils`。业务逻辑放这里。 |
| `**scripts/**` | 命令行入口；说明见 `**scripts/README.md**`。                               |
| `**configs/**` | 见上节与 `**configs/README.md**`。                                    |
| `**data/**`    | `raw` / `processed` 大文件通常不提交。                                    |


**原则**：在**原有包结构**上增量开发；新增文件放入对应任务目录或 `utils/`。

---

## 6. 运行与环境

- 虚拟环境：`python3 -m venv .venv`，`pip install -r requirements.txt`；无 `python` 时用 `**python3`**。
- 需 `PYTHONPATH=src` 时以脚本或文档为准。
- 要素基线：`python3 scripts/run_element_baseline_train.py`。

---

## 7. Git 与协作

- 勿提交：`.venv/`、大体积 `data/`（按 `.gitignore`）、`outputs/` 下除 `final_results/` 规则外的中间文件。
- 可提交：`configs/`、`outputs/final_results/` 中定稿结果、`models/` 中选定小权重（若体积可接受）。
- 建议使用分支；提交信息标明任务模块与改动类型。

---

## 8. 测试与文档

- 新增公共 API 更新对应 `**README.md**`。

---

## 9. AI 助手行为建议

- 编码前优先 **@ `AGENTS.md`** 与本任务目录下的 `**README.md**`。
- 用户仅要求解释、不改仓库时，保持 **Ask** 模式。
- 实现新脚本时默认带 `**setup_logging()`**、配置从 `**configs/**` 读取、产出写入 `**outputs/<任务>/**`。

---

## 10. 文档索引


| 文档                           | 内容         |
| ---------------------------- | ---------- |
| `README.md`                  | 项目总览、产出目录  |
| `scripts/README.md`          | 脚本与流程      |
| `configs/README.md`          | 配置文件布局     |
| `src/utils/README.md`        | logger、可视化 |
| `docs/赛题A09_面向海洋环境智能分析系统.md` | 赛题要求       |


