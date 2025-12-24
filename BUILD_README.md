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

- `POST /api/ocr` - OCR 识别
- `POST /api/ocr/draw` - 绘制识别结果
- `POST /api/ocr/ocr2text` - 提取纯文本

## 许可证

MIT License