# TODO - PaddleOCR-Desktop Rust Backend Alignment

## 目标
将 rust-onnx 后端（基于 oar-ocr）全面对齐 python-onnx 后端，支持完整功能特性。

## 约束
- Rust 后端使用 `oar-ocr` crate (v0.3.1) 处理所有 OCR/structure 操作
- oar-ocr 模型来自 GitHub releases (v0.3.0)，不依赖 ModelScope
- ModelManagementPage 展示 84+ 模型（来自 GitHub releases v0.3.0）
- 不修改前端
- 路由不能有尾部斜杠

---

## 已完成

### 构建 & 编译
- [x] 修复 `null::<()>` 语法错误 → `serde_json::Value::Null`
- [x] 修复 `LayoutElement.bounding_box` → `bbox` + `points`
- [x] 修复 `TableResult/FormulaResult.bbox.x0/y0/x1/y1` → `bbox.points`
- [x] 修复 `table.confidence()` 方法调用
- [x] 添加 `Response` 类型导入
- [x] 修复 `OARStructureBuilder` 链式调用所有权问题
- [x] 清理 unused variable warnings

### OCR 路由 (`/api/ocr`)
- [x] `/api/ocr` recognize — 解析 Form 参数，构建 model_key，支持 PDF 多页
- [x] `/api/ocr/draw` — 旋转处理，PDF 多页，base64 编码
- [x] `/api/ocr/ocr2text` — 结果转纯文本
- [x] `/api/ocr/options` — 返回所有可用模型
- [x] `/api/ocr/model_status`
- [x] `/api/ocr/load`
- [x] `/api/ocr/unload`
- [x] `/api/ocr/download_missing`
- [x] `OcrEngine` pipeline 缓存 (`Arc<Mutex<HashMap<String, Arc<OAROCR>>>>`)
- [x] `OAROCRBuilder` 链式构建
- [x] `model_key` 格式: `"det|rec|doc_cls|textline_cls"`
- [x] 添加 `default_dict()` 方法

### 模型注册 (`ModelRegistry`)
- [x] 扩展模型注册表从 3 个到 84+ 个模型
- [x] 辅助方法: `get_model_path()`, `model_exists()`, `default_dict_model()`
- [x] 辅助方法: `default_det/rec/doc_cls/textline_cls_model()`
- [x] 注册 `unimernet_tokenizer`, `uvdoc`, `table_structure_dict_ch`

### 公式识别 (`/api/formula/recognize`)
- [x] `/api/formula/recognize` — `FormulaRecognitionPredictor::builder()`
- [x] `/api/formula/recognize/model_options`
- [x] `/api/formula/recognize/load`
- [x] `/api/formula/recognize/unload`
- [x] `/api/formula/recognize/model_status`
- [x] `/api/formula/recognize/download_missing`

### UVDoc 文档纠偏 (`/api/uvdoc/unwarp`)
- [x] `/api/uvdoc/unwarp` — `DocumentRectificationPredictor`
- [x] `/api/uvdoc/unwarp/load`
- [x] `/api/uvdoc/unwarp/unload`
- [x] `/api/uvdoc/unwarp/model_status`
- [x] `/api/uvdoc/unwarp/download_missing`

### PP-Structure (`/api/ppstructure`)
- [x] `/api/ppstructure` analyze — `OARStructureBuilder` + `predict_image()`
- [x] `/api/ppstructure/draw` — PNG 输出
- [x] `/api/ppstructure/markdown` — 生成 Markdown
- [x] `/api/ppstructure/options`
- [x] `/api/ppstructure/load`
- [x] `/api/ppstructure/download_missing`
- [x] `/api/ppstructure/unload`
- [x] `/api/ppstructure/model_status`
- [x] 辅助函数: `build_structure_pipeline()`, `load_image_from_bytes()`, `draw_polygon()`, `draw_line()`

### 模型管理 (`/api/models`)
- [x] `/api/models/list`
- [x] `/api/models/download/{model_name}`
- [x] `/api/models/delete/{model_name}`
- [x] `/api/models/batch-download`
- [x] `/api/models/batch-delete`

### 其他
- [x] 添加 `pdf` crate (v0.10) 支持 PDF 处理
- [x] 路由注册到 `main.rs`
- [x] 修复 Rust 路由尾部斜杠问题

---

## 待完成

### 高优先级

#### 1. OCR 路由缺失 UVDoc 集成
- **问题**: Python `/api/ocr` 有 `use_uvdoc: bool` 和 `uvdoc_model` 参数，Rust 完全没用
- **oar-ocr 支持**: `OAROCRBuilder::with_document_image_rectification(model_path)` 将 UVDoc 集成到 OCR pipeline
- **需要修改**: `ocr.rs` 的 `recognize` 和 `load` 路由，解析 `use_uvdoc` 和 `uvdoc_model` 参数，条件构建时加入 rectification

#### 2. OCR 路由缺失印章检测模式
- **问题**: oar-ocr 支持 `text_type("seal")` 印章文本检测
- **需要**: 在 `recognize` 路由中添加 `text_type` 参数支持

#### 3. UVDoc `/unwarp` 响应格式对齐
- **问题**: Python 返回 `StreamingResponse` (PNG bytes + headers)，Rust 返回 JSON + base64
- **需要**: 确认前端实际期望的格式

### 中优先级

#### 4. PP-Structure `/analyze` 完整字段对齐
- **问题**: `analyze` 返回的 JSON 字段可能与 Python 格式不完全一致
- **需要**: 对比 Python `ppstructure.py` 的返回格式，逐字段对齐
- **参考**: `StructureResult` 包含 `layout_elements`, `tables`, `formulas`, `text_regions`, `orientation_angle`, `region_blocks`, `rectified_img`

#### 5. PP-Structure `/draw` 完整实现
- **问题**: 当前 draw 只画了 bbox 框，未绘制表格/公式的详细内容
- **需要**: 根据 Python 的 `draw` 逻辑，完整实现表格/公式区域的绘制

#### 6. PP-Structure `/markdown` 增强
- **问题**: 当前 markdown 生成逻辑较简单
- **需要**: 对比 Python 实现，增强表格 LaTeX → HTML 转换、公式渲染等

#### 7. formula 路由响应格式对齐
- **需要**: 对比 Python `formula.py` 的返回格式

### 低优先级

#### 8. 批处理参数支持
- **oar-ocr 支持**: `image_batch_size()`, `region_batch_size()` 批处理控制
- **需要**: 在 OCR/Structure 路由中添加相应参数

#### 9. 词级边界框
- **oar-ocr 支持**: `return_word_box(true)` 返回词级边界框
- **需要**: 在 OCR 路由中暴露此功能

#### 10. 检测/识别阈值参数
- **oar-ocr 支持**: `TextDetectionConfig`, `TextRecognitionConfig` 可配置阈值
- **需要**: 在路由中添加 `det_db_thresh`, `rec_thresh` 等参数

#### 11. 端到端测试
- **需要**: 启动 rust-onnx 服务，测试所有路由与 Python 后端的一致性

---

## 关键上下文

### oar-ocr 导出 (v0.3.1)
```rust
use oar_ocr::prelude::*;
```
- `OAROCR`, `OAROCRBuilder`, `OAROCRResult`, `OARStructure`, `OARStructureBuilder`, `TextRegion`
- Predictors: `FormulaRecognitionPredictor`, `DocumentRectificationPredictor`, `DocumentOrientationPredictor`, `LayoutDetectionPredictor`

### OAROCRBuilder 链
```rust
OAROCRBuilder::new(det_path, rec_path, dict_path)
    .with_document_image_orientation_classification(doc_cls_path)
    .with_text_line_orientation_classification(textline_cls_path)
    .with_document_image_rectification(uvdoc_path)  // <-- 缺失！
    .text_type("seal")                              // <-- 缺失！
    .return_word_box(true)                          // <-- 缺失！
    .image_batch_size(4)
    .region_batch_size(32)
    .build()
```

### model_key 格式
```
"pp-ocrv5_mobile_det|pp-ocrv5_mobile_rec|pp-lcnet_x1_0_doc_ori|pp-lcnet_x1_0_textline_ori"
```

### OARStructureBuilder 完整链
```rust
OARStructureBuilder::new(&layout_path)
    .with_ocr(&det_path, &rec_path, &dict_path)
    .with_document_orientation(&doc_cls_path)
    .with_text_line_orientation(&textline_cls_path)
    .with_table_classification(&table_cls_path)
    .with_table_cell_detection(&cell_det_path, "wired")
    .with_table_cell_detection(&cell_det_path, "wireless")
    .with_table_structure_recognition(&struct_rec_path, "wireless")
    .with_table_structure_recognition(&struct_rec_path, "wired")
    .table_structure_dict_path(&dict_path)
    .with_formula_recognition(&formula_path, &tokenizer_path, "pp_formulanet")
    .with_document_rectification(&uvdoc_path)
    .build()
```

### 文档
- oar-ocr examples: `C:\Users\85243\.cargo\registry\src\index.crates.io-1949cf8c6b5b557f\oar-ocr-0.3.1\examples\`
- Python 参考: `F:\PythonCodes\PaddleOCR-Desktop\backend\python-onnx\app\router\`

---

## 相关文件
- `backend/rust-onnx/ocr-lib/src/engine.rs` — OcrEngine
- `backend/rust-onnx/ocr-lib/src/registry.rs` — 模型注册表 (84+)
- `backend/rust-onnx/ocr-server/src/routes/ocr.rs` — OCR 路由
- `backend/rust-onnx/ocr-server/src/routes/formula.rs` — 公式识别路由
- `backend/rust-onnx/ocr-server/src/routes/uvdoc.rs` — UVDoc 路由
- `backend/rust-onnx/ocr-server/src/routes/ppstructure.rs` — PP-Structure 路由
- `backend/rust-onnx/ocr-server/src/main.rs` — 路由注册
- `backend/python-onnx/app/router/ppocr.py` — Python OCR 参考
- `backend/python-onnx/app/router/ppstructure.py` — Python PP-Structure 参考
- `backend/python-onnx/app/router/formula.py` — Python 公式识别参考
- `backend/python-onnx/app/router/uvdoc.py` — Python UVDoc 参考
