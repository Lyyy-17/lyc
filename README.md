ocean_ai_system/               # 项目根目录
├── README.md                  # 项目说明文档
├── requirements.txt           # Python依赖包列表
├── configs/                   # 配置文件目录
│   ├── data_config.yaml       # 数据路径、物理阈值等配置
│   ├── model_config.yaml      # 各模型超参数配置
│   └── train_config.yaml      # 训练参数配置
├── data/                      # 数据目录（通常不提交，在.gitignore中忽略）
│   ├── raw/                   # 原始NetCDF数据
│   ├── processed/             # 清洗处理后的数据
│   ├── interim/               # 中间数据（如标准化后的数据）
│   └── dataset.py             # 数据加载与Dataset类定义
├── src/                       # 核心源代码
│   ├── data_preprocessing/    # 【模块1】数据预处理
│   │   ├── __init__.py
│   │   ├── cleaner.py         # 核心清洗类（分块处理、异常标记、标准化）
│   │   ├── validator.py       # 数据质量验证与可视化
│   │   └── splitter.py        # 划分训练集、验证集、测试集
│   ├── eddy_detection/        # 【模块2】中尺度涡旋识别
│   │   ├── __init__.py
│   │   ├── model.py           # 检测模型定义（如YOLO, U-Net）
│   │   ├── trainer.py         # 模型训练与验证循环
│   │   ├── predictor.py       # 单张/批量图片推理
│   │   └── evaluator.py       # 评估指标计算（准确率、IoU等）
│   ├── element_forecasting/ # 【模块3】水文要素预测
│   │   ├── __init__.py
│   │   ├── model.py           # 时序预测模型（如LSTM, Transformer, TCN）
│   │   ├── trainer.py
│   │   ├── predictor.py       # 未来72小时预测
│   │   └── evaluator.py       # 计算均方误差等指标
│   ├── anomaly_detection/     # 【模块4】风-浪异常识别
│   │   ├── __init__.py
│   │   ├── model.py           # 异常检测模型（如自编码器、One-Class SVM）
│   │   ├── trainer.py
│   │   ├── detector.py        # 异常信号检测与台风关联
│   │   └── evaluator.py       # 异常识别准确率评估
│   ├── utils/                 # 公共工具函数
│   │   ├── __init__.py
│   │   ├── logger.py          # 日志记录
│   │   ├── visualizer.py      # 绘图函数（涡旋、预测曲线、异常图）
│   │   └── metrics.py         # 公共评估指标计算
│   └── pipeline.py            # 主流程：串联各模块的完整分析管道
├── models/                    # 保存训练好的模型权重
│   ├── eddy_model.pth
│   ├── forecast_model.pth
│   └── anomaly_model.pth
├── outputs/                   # 运行结果输出
│   ├── eddy_maps/             # 涡旋识别结果图
│   ├── forecast_curves/       # 要素预测曲线图
│   ├── anomaly_reports/       # 异常预警报告
│   └── final_results/         # 最终整合结果
├── scripts/                   # 可执行脚本
│   ├── 01_preprocess_data.py  # 步骤1：数据预处理
│   ├── 02_train_eddy.py       # 步骤2：训练涡旋识别模型
│   ├── 03_train_forecast.py   # 步骤3：训练要素预测模型
│   ├── 04_train_anomaly.py    # 步骤4：训练异常检测模型
│   ├── 05_run_pipeline.py     # 步骤5：运行完整系统
│   └── 06_generate_report.py  # 步骤6：生成评估报告
├── tests/                     # 单元测试
│   ├── test_preprocessing.py
│   ├── test_models.py
│   └── test_pipeline.py
└── docs/                      # 项目文档
    ├── system_architecture.md # 系统架构说明
    ├── api_reference.md       # API接口说明
    └── user_manual.md         # 用户使用手册
