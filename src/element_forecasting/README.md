# 要素预测模块 (Element Forecasting)

当前模块为纯深度学习方案，主模型名称保留为 HybridElementForecastModel（兼容既有调用），实际预测路径仅使用 Transformer 分支。

## 模型结构

1. 时空双轨 Transformer
   - 空间分支：对每个时刻做 patch embedding 后进行空间注意力编码。
   - 时间分支：将空间 token 重排后沿时间轴做 Transformer 编码。
   - 时间分支采用 BlockResidualTransformerEncoder，在每层 Attention 和 MLP 前注入 block-level residual context。

2. 输出
   - pred：最终预测结果。
   - pred_transformer：Transformer 分支预测结果（当前与 pred 一致）。
   - 推理器默认可做反标准化，恢复到物理量纲（可关闭）。

3. 周期性时间编码（已升级）
   - 支持多周期、多谐波时间特征，不再仅限 24 小时单周期。
   - 通过 model.yaml 配置：
     - periodic_periods：周期列表（例如 24、12、168）。
     - periodic_harmonics：每个周期的谐波阶数。
   - 编码后由线性层映射到 d_model，并叠加到 temporal token。

## 数据模式

1. 单文件数据源
   - 要素预测统一使用单个合并文件：data/processed/element_forecasting/all_clean_merged.nc。
   - 旧的 manifest 多文件/跨文件拼接逻辑已移除。

2. 滑窗采样
   - 采用 input_steps -> output_steps 的时间窗口。
   - 使用 window_stride 控制窗口步长。

3. 训练/验证/测试切分
   - 在单文件时间窗口序列上按比例切分 train/val/test。
   - 比例由 train.yaml 中 train_ratio、val_ratio、test_ratio 控制。

4. 变量配置
   - 输入变量与输出变量使用同一组 var_names（如 sst/sss/ssu/ssv）。
   - 通道数由 var_names 自动推断。

## 训练策略

1. 支持 AMP、梯度累积、多进程 DataLoader。
2. 支持 spatial_downsample 以降低空间 token 数和显存压力。
3. 当前损失为主损失 + Transformer 辅助损失（masked_mse 组合），未启用 FFT 频域损失。
4. 训练入口：scripts/04_train_forecast.py（默认走主模型；--baseline 走旧基线）。

## 关键配置

1. 模型配置：configs/element_forecasting/model.yaml
   - d_model, nhead, num_layers, block_size, dropout, spatial_downsample
   - periodic_periods, periodic_harmonics

2. 训练配置：configs/element_forecasting/train.yaml
   - data_file, norm_stats_path
   - window_stride, train_ratio, val_ratio, test_ratio
   - epochs, batch_size, lr, num_workers, device, amp, grad_accum_steps
