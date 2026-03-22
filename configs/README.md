# 配置说明

| 路径 | 说明 |
|------|------|
| `data_config.yaml` | 数据路径、划分、预处理 artifacts（见仓库根 README） |
| `eddy_detection/` | **涡旋识别主模型** `model.yaml` / `train.yaml` |
| `element_forecasting/` | **要素预报主模型**（非基线） |
| `anomaly_detection/` | **异常检测主模型** |
| `baseline/element_forecasting/` | **要素预报基线**（ConvLSTM），与主模型配置分离 |

基线训练入口：`scripts/run_element_baseline_train.py` → 读取 `baseline/element_forecasting/*.yaml`。
