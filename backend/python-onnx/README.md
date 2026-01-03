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

## 模型文件

项目已包含所需的PP-OCRv5 ONNX模型文件，位于 `models/` 目录下：
- `models/PP-OCRv5_mobile_det-ONNX/inference.onnx` - 文本检测模型
- `models/PP-OCRv5_mobile_rec-ONNX/inference.onnx` - 文本识别模型
- `models/PP-LCNet_x1_0_doc_ori-ONNX/inference.onnx` - 文本方向分类模型

## 运行服务

### 开发模式

```bash
python run.py
```

服务将在 `http://localhost:8000` 启动。

### API接口

#### OCR 接口

- `POST /api/ocr/` - OCR识别
  - 参数：
    - `file`: 上传的图像或PDF文件
    - `det_db_thresh`: 检测阈值 (默认: 0.3)
    - `cls_thresh`: 分类阈值 (默认: 0.9)
    - `use_cls`: 是否使用方向分类 (默认: True)
    - `merge_overlaps`: 是否合并重叠框 (默认: False)
    - `overlap_threshold`: 重叠阈值 (默认: 0.9)

- `POST /api/ocr/draw` - 绘制OCR结果
  - 参数：
    - `file`: 上传的图像或PDF文件
    - `ocr_result`: OCR结果的JSON字符串
    - `drop_score`: 丢弃分数阈值 (默认: 0.0)
    - `max_pages`: 对于多页PDF，限制最多处理和返回的页面数 (默认: 2)

- `POST /api/ocr/ocr2text` - 提取纯文本
  - 参数：
    - `ocr_result`: OCR结果的JSON字符串

- `POST /api/ocr/load` - 加载OCR模型
- `POST /api/ocr/unload` - 卸载OCR模型
- `GET /api/ocr/model_status` - 获取OCR模型状态

#### PP-Structure 接口

- `POST /api/ppstructure/` - PP-Structure分析
  - 参数：
    - `file`: 上传的图像或PDF文件
    - `ocr_det_db_thresh`: OCR检测阈值 (默认: 0.3)
    - `unclip_ratio`: 文本框扩大比例 (默认: 2.0)
    - `merge_overlaps`: 是否合并重叠框 (默认: False)
    - `overlap_threshold`: 重叠阈值 (默认: 0.9)
    - `merge_layout`: 是否合并布局 (默认: False)
    - `layout_overlap_threshold`: 布局重叠阈值 (默认: 0.9)
    - `use_cls`: 是否使用方向分类 (默认: True)
    - `cls_thresh`: 分类阈值 (默认: 0.9)

- `POST /api/ppstructure/draw` - 绘制PP-Structure结果
  - 参数：
    - `file`: 上传的图像或PDF文件
    - `analysis_result`: 结构分析结果的JSON字符串
    - `page_number`: 对于单页PDF的可视化指定页码 (默认: 1)
    - `max_pages`: 对于多页PDF，限制最多处理和返回的页面数 (默认: 2)

- `POST /api/ppstructure/markdown` - 生成Markdown
  - 参数：
    - `file`: 上传的图像或PDF文件
    - `analysis_result`: 结构分析结果的JSON字符串

- `POST /api/ppstructure/load` - 加载PP-Structure模型
- `POST /api/ppstructure/unload` - 卸载PP-Structure模型
- `GET /api/ppstructure/model_status` - 获取PP-Structure模型状态

#### 通用接口

- `GET /api/health` - 健康检查
- `GET /api/models/list` - 列出可用模型
- `POST /api/models/download/{model_name}` - 下载模型
- `POST /api/models/batch-download` - 批量下载模型

### 响应格式

#### OCR识别响应
```json
{
  "results": [
    {
      "text": "识别的文本内容",
      "confidence": 0.95,
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
      "text_confidence": 0.95
    }
  ]
}
```

#### PDF文件OCR响应
```json
{
  "file_type": "pdf",
  "total_pages": 5,
  "results": [
    {
      "page": 1,
      "results": [
        {
          "text": "页面1的文本",
          "confidence": 0.95,
          "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
          "text_confidence": 0.95,
          "rotation": 0
        }
      ]
    }
  ]
}
```

#### 绘制结果响应 (PDF)
```json
{
  "file_type": "pdf",
  "total_pages": 5,
  "processed_pages": 2,
  "max_pages_limit": 2,
  "images": [
    {
      "page_number": 1,
      "data": "base64编码的PNG图片数据"
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

- 模型文件已包含在项目中，无需额外下载
- 如需更新模型，请参考 `references/scripts/` 目录下的转换脚本
## 许可证

本项目基于PaddlePaddle/PaddleOCR项目，遵循相应许可证。