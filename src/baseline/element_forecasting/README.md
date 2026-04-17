# 要素预报基线（ConvLSTM）

基于 **ConvLSTM** 编码历史时空帧，1×1 卷积解码为未来 `forecast_len` 帧（多变量通道与输入一致）。

## 配置

基线与主任务 `src/element_forecasting` 的配置分离，见 `configs/baseline/element_forecasting/model.yaml` 与 `train.yaml`。也可用 `--model-config` / `--train-config` 指定路径。

## 依赖

- 已运行 `scripts/02_preprocess_element.py`，且含 **split + stats**（`data/processed/splits/element_forecasting.json` 与 `normalization/element_forecasting_norm.json`）。
- 单日 NetCDF 时间维长度需 **≥ input_len + forecast_len**（默认 12+12）。

## 运行

在项目根目录：

```powershell
python scripts/04_train_forecast.py --epochs 5 --batch-size 2
```

使用 `utils.logger` 打日志；无 norm 文件时会 warning 并以原始数值训练。

训练入口支持 **`--manifest`** / **`--norm`** 覆盖默认划分与标准化 JSON。

## 模块

| 文件 | 说明 |
|------|------|
| `convlstm.py` | `ConvLSTMCell`、`ConvLSTMEncoder` |
| `model.py` | `ElementForecastConvLSTMBaseline` |
| `sequence_dataset.py` | `ElementForecastSequenceDataset`（滑窗样本） |
| `train.py` | 训练入口 |
