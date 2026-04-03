import os
import sys
import torch
import numpy as np
import matplotlib.pyplot as plt

try:
    import gradio as gr
except ImportError:
    print("Please install gradio: pip install gradio>=3.0")
    sys.exit(1)

# 将 src 目录加入模块搜索路径，确保可以导入相关模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from element_forecasting.predictor import ElementForecastPredictor
from element_forecasting.dataset import ElementForecastWindowDataset
from utils.visualization_defaults import apply_matplotlib_defaults

def element_forecasting_logic(model_path, data_path, start_idx):
    """
    接收模型路径、数据路径和数据窗口的起始索引，执行加载与推理，返回 Gradio 图表。
    """
    if not os.path.exists(model_path):
        return plt.figure(), f"Error: 模型路径 {model_path} 不存在"
    if not os.path.exists(data_path):
        return plt.figure(), f"Error: 数据路径 {data_path} 不存在"
    
    try:
        # 1. 设置本项目通用的高水平可视化画图默认风格
        apply_matplotlib_defaults()
        
        # 修复 Matplotlib 图片中的中文显示问题 (方块/乱码)
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC', 'Arial Unicode MS', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False

        # 2. 构建 Dataset 从 .nc 文件读取连续的步数
        dataset = ElementForecastWindowDataset(
            data_file=data_path,
            input_steps=12,
            output_steps=12,
            split=None  # 不自动切分集
        )

        # 3. 获取特定的一个数据切片窗口并整理为推理适用的 (1, input_steps, Channels, H, W)
        idx = int(start_idx)
        if idx < 0 or idx >= len(dataset):
            return plt.figure(), f"Error: 起始步 {idx} 超出数据集范围 (0 to {len(dataset)-1})"

        sample = dataset[idx]
        x_tensor = sample["x"].unsqueeze(0)  

        # 4. 加载 ElementForecastPredictor 推理预测器
        device = "cuda" if torch.cuda.is_available() else "cpu"
        predictor = ElementForecastPredictor(checkpoint_path=model_path, device=device)

        # 5. 调用 predict() 执行推理
        # denormalize=True 意味着自动尝试根据 normalization json 反归一化为真实物理值
        result = predictor.predict(x_tensor, denormalize=True, return_cpu=True)
        pred_tensor = result["pred"]
        var_names = result.get("var_names", ["SST", "SSS", "SSU", "SSV"])

        # 6. 使用 Matplotlib 进行可视化展示 (展示预测结果中的第1步各物理通道)
        fig, axs = plt.subplots(2, 2, figsize=(10, 8))
        axs = axs.flatten()
        
        # 维度还原: [batch=0, step=0, variable, H, W]
        first_step_pred = pred_tensor[0, 0].numpy()
        
        for i in range(min(4, first_step_pred.shape[0])):
            ax = axs[i]
            im = ax.imshow(first_step_pred[i], cmap="viridis", origin="lower")
            ax.set_title(f"预测第 1 步: {var_names[i]}")
            fig.colorbar(im, ax=ax)
        
        plt.tight_layout()
        
        return fig, "预测成功！上方展示本次序列输入后，模型对第1步(Step 1)四要素的联合预测结果。"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return plt.figure(), f"Error: 发生异常 {str(e)}"

def create_gui():
    with gr.Blocks(title="OceanRace 智能海洋分析系统 UI") as app:
        gr.Markdown("# 🌊 OceanRace 面向海洋环境智能分析系统")
        gr.Markdown("包含三大核心模块：海洋要素短临预报、海洋中尺度涡旋检测、极端异常事件检测")
        
        with gr.Tab("要素预测 (Element Forecasting)"):
            with gr.Row():
                with gr.Column():
                    model_input = gr.Textbox(value="models/forecast_model.pt", label="模型路径 (Checkpoint)")
                    data_input = gr.Textbox(value="data/processed/element_forecasting/示例数据.nc", label="测试输入数据序列路径 (.nc)")
                    idx_input = gr.Number(value=0, label="时间序列切片起始步 (Index)", precision=0)
                    predict_btn = gr.Button("加载数据并生成预测", variant="primary")
                with gr.Column():
                    status_output = gr.Textbox(label="运行状态", interactive=False)
                    plot_output = gr.Plot(label="要素场预测可视化 (首步)")
            
            predict_btn.click(
                fn=element_forecasting_logic,
                inputs=[model_input, data_input, idx_input],
                outputs=[plot_output, status_output]
            )
            
        with gr.Tab("涡旋检测 (Eddy Detection)"):
            gr.Markdown("### 🌀 涡旋识别功能建设中 ... 该界面保留为入口空位")
            gr.Textbox(value="待接入 Eddy 分支逻辑...", label="备用占位框", interactive=False)
            gr.Button("运行涡旋检测 (暂不支持)")
            
        with gr.Tab("异常检测 (Anomaly Detection)"):
            gr.Markdown("### ⚠️ 极端异常事件检测功能建设中 ... 该界面保留为入口空位")
            gr.Textbox(value="待接入 Anomaly 分支逻辑...", label="备用占位框", interactive=False)
            gr.Button("运行异常检测 (暂不支持)")
            
    return app

if __name__ == "__main__":
    app = create_gui()
    # server_name 设为 0.0.0.0 支持网络访问或 Docker 映射
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
