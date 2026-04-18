# `src/utils` 说明

公共工具模块，供训练、评估或其它 `src` 包内代码引用。命令行入口不放在仓库根目录 `scripts/`，而是在各模块内通过 `python -m` 调用。

## 环境

- 在项目**根目录**执行下文命令。
- 需将 `src` 加入 Python 路径，否则找不到 `utils`、`data_preprocessing` 等包。

**PowerShell（Windows）：**

```powershell
$env:PYTHONPATH = "src"
```

**bash：**

```bash
export PYTHONPATH=src
```

依赖见项目根目录 `requirements.txt`；可视化需要已安装 `matplotlib`。

---

## `logger.py`：统一日志

训练、预处理脚本、各 `src` 包内模块应使用同一套日志（格式、级别、可选文件落盘），便于排查问题与复现实验。

### 约定

- **模块内**：`from utils.logger import get_logger`，再 `log = get_logger(__name__)`，使用 `log.info` / `log.warning` / `log.debug` / `log.exception` 等。
- **不要用 `print` 作为正式运行日志**；临时调试可用 `print`，合并前建议改为 `log.debug` 或删除。
- **可执行入口**（`scripts/*.py` 或 `python -m utils.xxx` 的 `main()`）：在解析完参数后、业务逻辑**之前**调用一次 `setup_logging()`（见下节「入口模板」）。
- **级别**：默认 `INFO`。未向 `setup_logging(level=...)` 传参时，可用环境变量 **`OCEAN_LOG_LEVEL`** 设为 `DEBUG` / `INFO` / `WARNING` / `ERROR`。
- **纯库代码、且需避免导入 `utils` 包时**（例如减轻 import 副作用）：可使用标准库 `logging.getLogger(__name__)`；只要进程里某处调过 `setup_logging()`，子 logger 会继承根 logger 的 handler 与格式。

### `setup_logging` 参数摘要

| 参数 | 说明 |
|------|------|
| `level` | 如 `"DEBUG"`、`logging.INFO`；`None` 时用 `OCEAN_LOG_LEVEL`，再默认 `INFO` |
| `log_file` | 可选，额外写入该路径（UTF-8），父目录不存在会自动创建 |
| `force` | `True` 时清空已有根 handler 再配置（测试或二次指定文件时用） |

测试里需要干净状态时，可 `from utils.logger import reset_logging` 在 teardown 中调用。

### 入口模板（`scripts` 或 `if __name__ == "__main__"`）

脚本需先把 `src` 加入 `sys.path`（本仓库脚本已统一处理），再导入 logger：

```python
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from utils.logger import get_logger, setup_logging  # noqa: E402

_log = get_logger(__name__)


def main() -> None:
    ap = argparse.ArgumentParser(description="...")
    # ap.add_argument(...)
    args = ap.parse_args()
    setup_logging()  # 若有需要: setup_logging(level="DEBUG", log_file=ROOT / "outputs/logs/run.log")
    _log.info("start")
    # ...


if __name__ == "__main__":
    main()
```

`scripts/02_preprocess_*.py`、`scripts/sync_data_config.py` 等可执行入口同样在 `parse_args()` 之后调用 `setup_logging()`。

### 模块内记录信息（推荐写法）

使用 **惰性参数**，避免 `%` 或 `f-string` 在不需要输出时仍做昂贵格式化：

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("epoch %s loss=%.4f", epoch, loss)
logger.warning("skipped %s: %s", path, reason)
```

异常用 `logger.exception("...")` 会自动带上栈（等价于 `error(..., exc_info=True)`）。

### 进度条（tqdm）

与日志同时使用时，用 **`tqdm_logging()`** 包住「含 tqdm 与 logger 」的代码块，避免日志冲乱进度条；`tqdm` 请从本模块导入（已配置与 `logging_redirect_tqdm` 协同）。

```python
from utils.logger import get_logger, tqdm, tqdm_logging

logger = get_logger(__name__)
with tqdm_logging():
    for p in tqdm(paths, desc="files"):
        logger.debug("processing %s", p)
```

### 机器可读输出（JSON 等）

若脚本的**主产物**需要原样写到 **stdout**（便于 `|` 管道、`jq` 解析），**不要用 `logger.info` 打印整段 JSON**（会带时间戳与级别前缀）。做法是：**正文用 `sys.stdout.write(text + "\n")` 并 `flush`**，仅用 logger 打辅助说明（例如「已写入某文件」）。

项目级说明另见仓库根目录 **`AGENTS.md`** 与 **`.cursor/rules/logging.mdc`**；根目录 **`scripts/README.md`** 中有面向脚本的简短说明。

---

## `dataset_utils.py`：划分清单、norm JSON、张量标准化

预处理在 `data/processed/splits/` 写出 **划分 manifest**（`*.json`），在 `data/processed/normalization/` 写出 **`*_norm.json`**（各变量 `mean` / `std`）。各任务模块的 `dataset.py` 需要统一解析路径与做 \((x-\mu)/\sigma\) 时，应使用本模块，避免重复实现。

### API 摘要

| 函数 | 作用 |
|------|------|
| `project_root()` | 返回项目根目录 `Path`（含 `data/`、`src/`），用于拼接默认 `processed` / `splits` 路径 |
| `load_paths_from_manifest(manifest_path, split, root)` | 读划分 JSON，取键 `split`（`"train"` / `"val"` / `"test"`）下的路径列表，与 `root` 拼成 `list[Path]`；无该键则 `KeyError` |
| `load_norm_stats(path)` | 读 `*_norm.json`，解析 `variables` 中各变量的 `mean`、`std`，返回 `dict[str, (float, float)]` |
| `standardize_tensor(t, key, norm)` | 对 `torch.Tensor` 做 `(t - mean) / std`；`norm` 为 `None` 或缺少 `key` 时**原样返回** `t` |

### 约定

- **划分 JSON** 结构需含 `train` / `val` / `test` 等键，值为相对项目根的 POSIX 路径字符串（与 `splitter.write_split_manifest` 一致）。
- **norm JSON** 需含顶层 `variables`，其下每个变量有 `mean`、`std`（与 `splitter.write_standardization_json` 一致）。
- 依赖 **`torch`**；仅在构建 `Dataset` 或训练代码路径中导入即可。

### 示例：在自定义 `Dataset` 中使用

```python
from pathlib import Path

import torch
from torch.utils.data import Dataset

from data_preprocessing.io import open_nc
from utils.dataset_utils import (
    load_norm_stats,
    load_paths_from_manifest,
    project_root,
    standardize_tensor,
)


class MyDataset(Dataset):
    def __init__(
        self,
        split: str = "train",
        norm_stats_path: str | Path | None = None,
    ):
        root = project_root()
        self._norm = load_norm_stats(Path(norm_stats_path)) if norm_stats_path else None
        man = root / "data/processed/splits/eddy.json"
        self.paths = load_paths_from_manifest(man, split, root)

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int) -> dict:
        path = self.paths[idx]
        ds = open_nc(path)
        try:
            t = torch.from_numpy(ds["adt"].values.astype("float32"))
            return {"adt": standardize_tensor(t, "adt", self._norm)}
        finally:
            ds.close()
```

也可从包根与其它工具一并导入：

```python
from utils import project_root, load_paths_from_manifest, load_norm_stats, standardize_tensor
```

---

## `visualization_defaults.py`：可视化标准

与具体业务图（训练曲线、混淆矩阵、格点场等）**解耦**，集中约定**图幅、导出 DPI、字号、色图、线宽、网格、背景色**，避免各处写死魔法数。

### 常量摘要

| 类别 | 名称 | 说明 |
|------|------|------|
| 图幅 / 导出 | `DEFAULT_FIGSIZE` | 默认 `(10.0, 6.0)` 英寸 |
| | `DEFAULT_DPI_DISPLAY` | 屏幕/内联显示 DPI，默认 `150` |
| | `DEFAULT_DPI_SAVE` | 保存 PNG 推荐 DPI，默认 `300` |
| | `DEFAULT_DPI` | 与 `DEFAULT_DPI_SAVE` 相同（兼容旧名） |
| 色图 | `DEFAULT_CMAP` / `DEFAULT_CMAP_SEQUENTIAL` | 顺序量默认 `viridis` |
| | `DEFAULT_CMAP_DIVERGING` | 有正有负或差分场默认 `RdBu_r` |
| | `DEFAULT_COLOR_CYCLE` | 多曲线分类色列表 |
| 字号 | `DEFAULT_FONT_SIZE`、`TITLE_FONT_SIZE`、`AXIS_LABEL_FONT_SIZE`、`TICK_FONT_SIZE`、`LEGEND_FONT_SIZE` | 与 `apply_matplotlib_defaults` 写入的 rc 一致 |
| 线 / 点 | `DEFAULT_LINEWIDTH`、`DEFAULT_MARKERSIZE` | 默认线宽与散点标记大小 |
| 外观 | `DEFAULT_GRID_COLOR`、`DEFAULT_AXES_FACECOLOR`、`DEFAULT_FIGURE_FACECOLOR` | 网格色与轴/图背景 |

### 函数

| 名称 | 说明 |
|------|------|
| `apply_matplotlib_defaults()` | 将上述约定写入 `matplotlib.rcParams`（进程内全局；建议在入口调一次） |
| `standard_savefig_kwargs()` | 返回 `fig.savefig(**kwargs)` 推荐参数（`dpi`、`bbox_inches`、`facecolor`） |
| `slice_plot_kwargs()` | 返回 `{"figsize", "dpi", "cmap"}`，供二维格点场单帧封装用 |

### 示例 A：入口统一风格后作图

```python
import matplotlib.pyplot as plt
from utils.visualization_defaults import apply_matplotlib_defaults, standard_savefig_kwargs

apply_matplotlib_defaults()
fig, ax = plt.subplots()
ax.plot([0, 1], [0, 1])
fig.savefig("curve.png", **standard_savefig_kwargs())
plt.close(fig)
```

### 示例 B：只取个别常量（不调 `apply_*`）

```python
import matplotlib.pyplot as plt
from utils.visualization_defaults import DEFAULT_FIGSIZE, DEFAULT_DPI, DEFAULT_CMAP_DIVERGING

fig, ax = plt.subplots(figsize=DEFAULT_FIGSIZE)
im = ax.imshow(data, cmap=DEFAULT_CMAP_DIVERGING)
fig.savefig("field.png", dpi=DEFAULT_DPI, bbox_inches="tight")
plt.close(fig)
```

### 示例 C：`slice_plot_kwargs()` 字典

```python
from utils.visualization_defaults import slice_plot_kwargs

kw = slice_plot_kwargs()
# kw["figsize"], kw["dpi"], kw["cmap"] —— 给需要统一图幅/色图的自定义封装用
```

---

## 其它说明

**任务指标**在各模型子模块的 `evaluator` 中实现，不放在 `utils`。
