# PP-ONNX Convert

这个目录用于将 PaddlePaddle 模型转换为 ONNX 格式，以便在其他框架中使用。

## 目录结构

```
pp_onnx_convert/
├── README.md              # 本说明文件
├── .gitignore            # Git 忽略文件
├── requirements.txt      # Python 依赖包
├── convert_to_onnx.sh    # 单个模型转换脚本
├── batch_convert.sh      # 批量转换脚本
├── models_tar/           # 原始模型 tar 文件
├── models_pp/            # 解压后的 Paddle 模型
└── models_onnx/          # 转换后的 ONNX 模型
```

## 使用方法

### 环境准备

首次运行前需要安装系统依赖：
```bash
sudo apt update && sudo apt install -y python3-dev
```

### 单个模型转换

```bash
./convert_to_onnx.sh <模型目录> <输出目录>
```

例如：
```bash
./convert_to_onnx.sh models_pp/PP-OCRv5_server_det_infer models_onnx/PP-OCRv5_server_det_infer
```

### 批量转换

```bash
./batch_convert.sh
```

这会将 `models_pp/` 中的所有模型转换为 ONNX 格式，并保存在 `models_onnx/` 中。

## 依赖包

- paddlex: 用于模型转换
- onnxruntime: ONNX 运行时
- opencv-python: 图像处理
- numpy: 数值计算
- pillow: 图像处理

脚本会自动创建虚拟环境并安装所需依赖。

## 注意事项

- 首次运行时会下载并安装依赖，可能需要一些时间
- 转换后的模型保存在 `models_onnx/` 目录中
- 如果转换失败，请检查模型目录是否正确