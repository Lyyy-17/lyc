# 要素预报基线（ConvLSTM）

基于 **ConvLSTM** 编码历史时空帧，1×1 卷积解码为未来 `forecast_len` 帧（多变量通道与输入一致）。

## 配置

基线与主任务 `src/element_forecasting` 的配置分离，见 `configs/baseline/element_forecasting/model.yaml` 与 `train.yaml`。也可用 `--model-config` / `--train-config` 指定路径。

## 依赖

- 已运行 `scripts/02_preprocess.py`，且含 **split + stats**（`data/processed/splits/element_forecasting.json` 与 `normalization/element_forecasting_norm.json`）。
- 单日 NetCDF 时间维长度需 **≥ input_len + forecast_len**（默认 12+12）。

## 运行

在项目根目录：

```powershell
python scripts/04_train_forecast.py --epochs 5 --batch-size 2
```

使用 `utils.logger` 打日志；无 norm 文件时会 warning 并以原始数值训练。

### 极少样本冒烟（不依赖真实预处理）

用于验证 **Dataset → DataLoader → 模型 → 反向传播** 能否跑通：在 `outputs/smoke_element_baseline/`（已 `.gitignore`）写入合成 `fake_clean.nc`、划分与 norm，再调用训练入口。

```powershell
python scripts/smoke_element_forecast.py
```

训练入口支持 **`--manifest`** 覆盖默认 `data/processed/splits/element_forecasting.json`，便于指向上述冒烟文件。

## 模块

| 文件 | 说明 |
|------|------|
| `convlstm.py` | `ConvLSTMCell`、`ConvLSTMEncoder` |
| `model.py` | `ElementForecastConvLSTMBaseline` |
| `sequence_dataset.py` | `ElementForecastSequenceDataset`（滑窗样本） |
| `train.py` | 训练入口 |
