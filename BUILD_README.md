# PaddleOCR Desktop

基于 Tauri + React + FastAPI 的桌面 OCR 应用

## 功能特性

- 🖼️ 支持图片 OCR 识别
- 📄 支持 PDF 文件多页识别
- 🎨 可视化识别结果
- 📝 纯文本提取
- 🖥️ 现代化的桌面界面

## 技术栈

- **前端**: React + TypeScript + Vite + Tauri
- **后端**: Python + FastAPI + PaddleOCR
- **打包**: PyInstaller + Tauri

## 构建状态 ✅

构建已成功完成！生成了以下文件：

- **可执行文件**: `frontend\src-tauri\target\release\app.exe`
- **MSI安装包**: `frontend\src-tauri\target\release\bundle\msi\PaddleOCR Desktop_1.0.0_x64_en-US.msi`
- **后端可执行文件**: `backend\python-onnx\dist\paddleocr_backend.exe`

**重要说明**: 构建脚本会自动将后端exe复制到Tauri目录，并通过Rust命令管理后端进程生命周期。现在支持随机端口分配，避免端口冲突！✅

### 模型包分发 📦

为了减小主程序包体积，**模型文件已从主程序包中分离**，作为独立的资源包分发：

#### 构建模型包
```bash
# 构建独立的模型包
.\scripts\build_models_package.ps1

# 或指定输出路径
.\scripts\build_models_package.ps1 -OutputPath "C:\path\to\models-package.zip"
```

#### 模型包使用方式
1. **解压模型包** 到任意目录
2. **设置环境变量**：
   ```cmd
   set PPOCR_MODELS_DIR=C:\path\to\extracted\models
   ```
3. **或将 `models` 文件夹** 放在可执行文件同级目录

#### 模型包内容
- 包含所有OCR和文档结构分析模型
- 约 200-300MB 大小
- 支持独立更新和分发

### 新的架构优势

#### **智能端口管理**
- **随机端口选择**: 后端随机选择1024-65535范围内的可用端口
- **Rust进程管理**: Tauri直接启动后端进程并捕获端口输出
- **无缝通信**: 前端通过Tauri命令获取端口，无需端口扫描

#### **进程生命周期**
```
应用启动 → Tauri启动后端 → 捕获PORT输出 → 前端连接 → 应用运行
     ↓
应用关闭 → Tauri终止后端进程 → 清理资源
```

#### **容错机制**
- 主方案: Tauri命令启动后端
- 降级方案: 端口扫描发现现有后端
- 兜底方案: 默认端口8000

## 运行应用程序

### 方式1: 直接运行可执行文件
```bash
# 运行桌面应用
frontend\src-tauri\target\release\app.exe
```

### 方式2: 安装MSI包
双击 `PaddleOCR Desktop_1.0.0_x64_en-US.msi` 进行安装，然后从开始菜单运行。

### 方式3: 开发模式
```bash
# 启动后端
cd backend/python-onnx && python run.py

# 启动前端
cd ../../frontend && npm run tauri dev
```

## 快速开始

### 1. 安装依赖

```bash
# 前端依赖
cd frontend
npm install

# 后端依赖
cd ../backend/python-onnx
pip install -r requirements.txt
```

### 2. 开发模式

```bash
# 启动后端 (在新终端)
cd backend/python-onnx
python run.py

# 启动前端 (新终端)
cd frontend
npm run tauri dev
```

### 3. 构建发布版本

运行构建脚本：

```powershell
# Windows
.\scripts\build.ps1

# 或者手动执行：
# 1. 构建前端
cd frontend; npm run build

# 2. 构建后端
cd ../backend/python-onnx
pyinstaller --clean paddleocr_backend.spec

# 3. 构建 Tauri 应用
cd ../../frontend
npx tauri build
```

## 项目结构

```
PaddleOCR-Desktop/
├── frontend/                 # React 前端
│   ├── src/
│   ├── src-tauri/           # Tauri 配置和 Rust 代码
│   └── build/               # 构建输出
├── backend/                  # Python 后端
│   └── python-onnx/
│       ├── app/             # FastAPI 应用
│       ├── models/          # OCR 模型
│       └── dist/            # PyInstaller 输出
├── scripts/                  # 构建脚本
│   └── build.ps1            # Windows 构建脚本
└── BUILD_README.md          # 构建说明
```

## API 接口

### OCR 接口

#### `POST /api/ocr/` - OCR 识别
执行 OCR 识别，支持图像和 PDF 文件。

**参数 (FormData):**
- `file` (File): 上传的图像文件或 PDF 文件
- `det_db_thresh` (float, 可选): 检测阈值，默认 0.3
- `cls_thresh` (float, 可选): 分类阈值，默认 0.9
- `use_cls` (bool, 可选): 是否使用方向分类，默认 true
- `merge_overlaps` (bool, 可选): 是否合并重叠框，默认 false
- `overlap_threshold` (float, 可选): 重叠阈值，默认 0.9

**响应格式 (JSON):**
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

对于 PDF 文件，响应格式为：
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

#### `POST /api/ocr/draw` - 绘制 OCR 结果
在图像上绘制 OCR 识别结果的边界框。

**参数 (FormData):**
- `file` (File): 上传的图像文件或 PDF 文件
- `ocr_result` (str): OCR 结果的 JSON 字符串
- `drop_score` (float, 可选): 丢弃分数阈值，默认 0.0
- `max_pages` (int, 可选): 对于多页 PDF，限制最多处理和返回的页面数，默认 2

**响应格式:**
- 对于单页图像：返回 PNG 图片流
- 对于 PDF 文件：返回 JSON 格式的图片列表

PDF 响应格式：
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
    },
    {
      "page_number": 2,
      "data": "base64编码的PNG图片数据"
    }
  ]
}
```

#### `POST /api/ocr/ocr2text` - 提取纯文本
从 OCR 结果中提取纯文本内容。

**参数 (FormData):**
- `ocr_result` (str): OCR 结果的 JSON 字符串

**响应格式 (JSON):**
```json
{
  "text": "提取的纯文本内容"
}
```

#### `POST /api/ocr/load` - 加载 OCR 模型
加载 OCR 模型到内存。

**响应格式 (JSON):**
```json
{
  "status": "success",
  "message": "OCR模型加载成功"
}
```

#### `POST /api/ocr/unload` - 卸载 OCR 模型
从内存中卸载 OCR 模型。

**响应格式 (JSON):**
```json
{
  "status": "success",
  "message": "OCR模型卸载成功"
}
```

#### `GET /api/ocr/model_status` - 获取 OCR 模型状态
获取当前 OCR 模型的加载状态。

**响应格式 (JSON):**
```json
{
  "loaded": true,
  "model_info": {
    "det_model": "PP-OCRv5_mobile_det",
    "rec_model": "PP-OCRv5_mobile_rec",
    "cls_model": "PP-OCRv5_mobile_cls"
  }
}
```

### PP-Structure 接口

#### `POST /api/ppstructure/` - PP-Structure 分析
执行文档结构分析，支持图像和 PDF 文件。

**参数 (FormData):**
- `file` (File): 上传的图像文件或 PDF 文件
- `ocr_det_db_thresh` (float, 可选): OCR 检测阈值，默认 0.3
- `unclip_ratio` (float, 可选): 文本框扩大比例，默认 2.0
- `merge_overlaps` (bool, 可选): 是否合并重叠框，默认 false
- `overlap_threshold` (float, 可选): 重叠阈值，默认 0.9
- `merge_layout` (bool, 可选): 是否合并布局，默认 false
- `layout_overlap_threshold` (float, 可选): 布局重叠阈值，默认 0.9
- `use_cls` (bool, 可选): 是否使用方向分类，默认 true
- `cls_thresh` (float, 可选): 分类阈值，默认 0.9

**响应格式 (JSON):**
```json
{
  "layout_regions": [
    {
      "type": "text",
      "bbox": [x1, y1, x2, y2],
      "text": "识别的文本内容",
      "confidence": 0.95
    }
  ],
  "rotation": 0
}
```

对于 PDF 文件，响应格式为：
```json
{
  "file_type": "pdf",
  "total_pages": 3,
  "pages": [
    {
      "page_number": 1,
      "layout_regions": [
        {
          "type": "text",
          "bbox": [x1, y1, x2, y2],
          "text": "页面1的文本",
          "confidence": 0.95
        }
      ],
      "rotation": 0
    }
  ]
}
```

#### `POST /api/ppstructure/draw` - 绘制 PP-Structure 结果
在图像上绘制文档结构分析结果的可视化。

**参数 (FormData):**
- `file` (File): 上传的图像文件或 PDF 文件
- `analysis_result` (str): 结构分析结果的 JSON 字符串
- `page_number` (int, 可选): 对于单页 PDF 的可视化指定页码，默认 1
- `max_pages` (int, 可选): 对于多页 PDF，限制最多处理和返回的页面数，默认 2

**响应格式:**
- 对于单页图像：返回 PNG 图片流
- 对于 PDF 文件：返回 JSON 格式的图片列表

PDF 响应格式：
```json
{
  "file_type": "pdf",
  "total_pages": 3,
  "processed_pages": 2,
  "max_pages_limit": 2,
  "images": [
    {
      "page_number": 1,
      "data": "base64编码的PNG图片数据"
    },
    {
      "page_number": 2,
      "data": "base64编码的PNG图片数据"
    }
  ]
}
```

#### `POST /api/ppstructure/markdown` - 生成 Markdown
从结构分析结果生成 Markdown 格式的文档。

**参数 (FormData):**
- `file` (File): 上传的图像文件或 PDF 文件
- `analysis_result` (str): 结构分析结果的 JSON 字符串

**响应格式 (JSON):**
```json
{
  "markdown": "# 文档标题\n\n文档内容...",
  "images": [
    {
      "filename": "table_1.png",
      "data": "base64编码的图片数据"
    }
  ]
}
```

#### `POST /api/ppstructure/load` - 加载 PP-Structure 模型
加载 PP-Structure 模型到内存。

**响应格式 (JSON):**
```json
{
  "status": "success",
  "message": "PP-Structure模型加载成功"
}
```

#### `POST /api/ppstructure/unload` - 卸载 PP-Structure 模型
从内存中卸载 PP-Structure 模型。

**响应格式 (JSON):**
```json
{
  "status": "success",
  "message": "PP-Structure模型卸载成功"
}
```

#### `GET /api/ppstructure/model_status` - 获取 PP-Structure 模型状态
获取当前 PP-Structure 模型的加载状态。

**响应格式 (JSON):**
```json
{
  "loaded": true,
  "model_info": {
    "layout_model": "PP-DocLayout-L",
    "table_model": "SLANeXt_wired"
  }
}
```

### 通用接口

#### `GET /api/health` - 健康检查
检查后端服务是否正常运行。

**响应格式 (JSON):**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

#### `GET /api/models/list` - 列出可用模型
获取所有可用的模型列表。

**响应格式 (JSON):**
```json
{
  "models": [
    {
      "name": "PP-OCRv5_mobile_det",
      "type": "det",
      "size": "4.2MB",
      "downloaded": true
    }
  ]
}
```

#### `POST /api/models/download/{model_name}` - 下载模型
下载指定的模型文件。

**响应格式 (JSON):**
```json
{
  "status": "success",
  "message": "模型下载完成"
}
```

#### `POST /api/models/batch-download` - 批量下载模型
批量下载多个模型文件。

**参数 (JSON):**
```json
{
  "models": ["model1", "model2"]
}
```

**响应格式 (JSON):**
```json
{
  "status": "success",
  "message": "批量下载完成"
}
```

## 许可证

MIT License