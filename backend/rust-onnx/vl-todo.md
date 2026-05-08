# TODO - PaddleOCR-VL / oar-ocr-vl 集成

## 目标
在 rust-onnx 后端中集成 oar-ocr-vl，支持 Vision-Language OCR 模型（PaddleOCR-VL、UniRec、HunyuanOCR、DocParser）。

## 约束
- 使用 `oar-ocr-vl` crate（非 `oar-ocr`），基于 Candle 推理
- 模型从 Hugging Face 下载
- 不修改前端

---

## 待完成

### 1. 添加 oar-ocr-vl 依赖
- **Cargo.toml**: 添加 `oar-ocr-vl = "0.6"`，可选 `features = ["cuda"]`
- **可选**: 添加 `hf-download` 工具用于下载模型

### 2. 模型下载支持
- **oar-ocr-vl 模型**（来自 Hugging Face）:
  - `PaddlePaddle/PaddleOCR-VL` — 0.9B, 109语言
  - `PaddlePaddle/PaddleOCR-VL-1.5` — 更新的 VL 模型，支持 text spotting + seal
  - `Topdu/UniRec-0.1B` — 轻量级统一识别
  - `tencent/HunyuanOCR` — 1B, prompt 驱动
  - `pp-doclayoutv3.onnx` — layout 检测（ONNX，DocParser 配合使用）
- **ModelManagementPage**: 添加 VL 模型下载/删除支持

### 3. 路由设计
- `/api/vl/ocr` — PaddleOCR-VL / UniRec OCR
- `/api/vl/table` — 表格结构识别
- `/api/vl/formula` — 公式识别（LaTeX）
- `/api/vl/chart` — 图表理解
- `/api/vl/spotting` — 文本定位+识别
- `/api/vl/seal` — 印章识别
- `/api/vl/parse` — DocParser 统一解析（layout + VL 后端）
- `/api/vl/draw` — 绘制结果
- `/api/vl/markdown` — 生成 Markdown
- `/api/vl/options` — 可用模型列表
- `/api/vl/load` — 加载模型
- `/api/vl/unload` — 卸载模型
- `/api/vl/model_status` — 模型状态
- `/api/vl/download_missing` — 下载缺失模型

### 4. 与现有路由的差异
- VL 模型基于 Candle（非 ONNX/ort）
- 推理结果格式与现有 `/api/ocr` 不同（VL 直接输出文本/LaTeX/HTML）
- HunyuanOCR 支持 prompt 驱动，需暴露 prompt 参数
- DocParser 结合 layout 检测 + VL 后端

### 5. 响应格式对齐
- 尽可能对齐 Python 后端格式
- 考虑 VL 的优势：更强的一致性（端到端识别）、多语言支持

---

## 关键 API

### PaddleOCR-VL
```rust
use oar_ocr_vl::{PaddleOcrVl, PaddleOcrVlTask};
let vl = PaddleOcrVl::from_dir("PaddleOCR-VL", device)?;
let result = vl.generate(image, PaddleOcrVlTask::Ocr, 256)?;
```

### UniRec
```rust
use oar_ocr_vl::UniRec;
let model = UniRec::from_dir("models/unirec-0.1b", device)?;
let result = model.generate(image, 512)?;
```

### DocParser
```rust
use oar_ocr_vl::{DocParser, DocParserConfig, UniRec, PaddleOcrVl};
let parser = DocParser::with_config(&unirec, DocParserConfig::default());
let result = parser.parse(&layout, image)?;
println!("{}", result.to_markdown());
```

### HunyuanOCR
```rust
use oar_ocr_vl::HunyuanOcr;
let model = HunyuanOcr::from_dir("HunyuanOCR", device)?;
let text = model.generate(image, prompt, 1024)?;
```

---

## 参考
- oar-ocr-vl docs: https://github.com/GreatV/oar-ocr/blob/main/docs/usage.md
- Hugging Face: PaddlePaddle/PaddleOCR-VL, Topdu/UniRec-0.1B, tencent/HunyuanOCR
