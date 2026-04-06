# 配置说明

**原则**：数据路径与预处理参数来自 **`data_config.yaml`**；各任务的**模型超参数**与**训练参数**分别从对应目录的 **`model.yaml`**、**`train.yaml`** 读取（代码中加载，避免硬编码）。AI 协作约定见根目录 **`AGENTS.md`**。

**不再使用 `*.yaml.example`**：模板与正式配置合一，直接修改并提交各任务目录下的 `model.yaml`、`train.yaml`。个人敏感覆盖请使用环境变量或根目录约定的 **`configs/*.secret`**（勿把密钥写入仓库内的 yaml）。

| 路径 | 说明 |
|------|------|
| `data_config.yaml` | 数据路径、划分、预处理 artifacts、与 `scripts/02_preprocess.py` 一致 |
| `eddy_detection/` | **涡旋识别主模型** `model.yaml` / `train.yaml` |
| `element_forecasting/` | **要素预报主模型**（非基线），见该目录 [`README.md`](element_forecasting/README.md) |
| `anomaly_detection/` | **异常检测主模型** |
| `baseline/element_forecasting/` | **要素预报基线**（ConvLSTM），与主模型配置分离 |
| `baseline/anomaly_detection/` | **异常检测基线**（轻量双分支 AE），与主模型配置分离 |

基线训练入口：

- `scripts/test_element/run_element_baseline_train.py` → 读取 `configs/baseline/element_forecasting/*.yaml`
- `scripts/05_train_anomaly.py --baseline` → 读取 `configs/baseline/anomaly_detection/*.yaml`

---

## `data_config.yaml` 新增可选项（merge）

当使用 `python scripts/02_preprocess.py --steps merge` 时，可在 `data_config.yaml` 中通过以下可选字段自定义整合产物目录：

```yaml
merge:
	output_dirs:
		eddy: outputs/eddy_detection/merged_chunks
		element_forecasting: outputs/element_forecasting/merged_chunks
		anomaly_detection: outputs/anomaly_detection/merged_chunks
```

- 不配置时使用上述默认目录。
- `--merge-files-per-output` 为命令行参数，用于控制每个输出大文件包含的小文件数。
