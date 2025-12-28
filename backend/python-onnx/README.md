# PaddleOCR Python ONNX Backend

这是一个基于ONNX Runtime的PaddleOCR后端服务，提供REST API接口用于图像和PDF的OCR识别。

## 功能特性

- 🖼️ 支持图像OCR识别
- 📄 支持PDF文件多页识别
- 🔍 基于PP-OCRv5模型
- 🚀 ONNX Runtime加速推理
- 🌐 FastAPI REST API接口

## 环境要求

- Python >= 3.8
- ONNX Runtime
- OpenCV
- NumPy
- Pillow

## 安装依赖

```bash
pip install -r requirements.txt
```

## 下载模型

在使用服务之前，需要先下载PP-OCRv5模型文件：

```bash
python download_models.py
```

此脚本会从OnnxOCR项目的GitHub仓库下载以下模型文件：
- `models/ppocrv5/det/det.onnx` - 文本检测模型
- `models/ppocrv5/rec/rec.onnx` - 文本识别模型
- `models/ppocrv5/cls/cls.onnx` - 文本方向分类模型
- `models/ppocrv5/ppocrv5_dict.txt` - 字符字典文件

## 运行服务

### 开发模式

```bash
python run.py
```

服务将在 `http://localhost:8000` 启动。

### API接口

- `GET /api/health` - 健康检查
- `POST /api/ocr/` - OCR识别
  - 参数：
    - `file`: 上传的图像或PDF文件
    - `det_db_thresh`: 检测阈值 (默认: 0.3)
    - `cls_thresh`: 分类阈值 (默认: 0.9)
    - `use_cls`: 是否使用方向分类 (默认: True)

### 响应格式

```json
{
  "results": [
    {
      "text": "识别的文本内容",
      "confidence": 0.95,
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    }
  ]
}
```

## 模型配置

可以通过环境变量 `PPOCR_MODELS_DIR` 指定自定义模型目录：

```bash
export PPOCR_MODELS_DIR=/path/to/models
python run.py
```

## 注意事项

- 首次运行前务必先执行 `python download_models.py` 下载模型
- 模型文件较大，请确保网络连接稳定
## 许可证

本项目基于PaddlePaddle/PaddleOCR项目，遵循相应许可证。