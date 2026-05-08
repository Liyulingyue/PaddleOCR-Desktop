# TODO - Python-ONNX 后端功能增强

## 待完成

### 1. 印章文本检测模式
- **oar-ocr 支持**: `text_type("seal")` 印章文本检测
- **Rust 后端**: 已在 `/api/ocr` 路由中实现，通过 `text_type` Form 参数控制（传 "seal" 启用）
- **需要**: 在 Python 后端 `/api/ocr` 路由中添加 `text_type` 参数支持
- **影响**: 支持检测图片中的印章/圆形文本区域（而非仅通用文本检测）

### 2. 词级边界框支持
- **oar-ocr 支持**: `return_word_box(true)` 返回词级边界框
- **Rust 后端**: 已在 `/api/ocr` 路由中实现，通过 `return_word_box` Form 参数控制
- **需要**: 在 Python 后端 `/api/ocr` 路由中添加 `return_word_box` 参数支持
- **影响**: 前端可选择是否返回词级（word-level）边界框，而非仅行级（line-level）边界框

### 3. 批处理参数支持
- **oar-ocr 支持**: `image_batch_size()`, `region_batch_size()` 批处理控制
- **Rust 后端**: 已在 `/api/ocr` 路由中实现，通过 `image_batch_size` 和 `region_batch_size` Form 参数控制
- **需要**: 在 Python 后端 OCR/Structure 路由中添加相应参数
- **影响**: 控制 ONNX 推理时的批处理大小，可能提升性能
