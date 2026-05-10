# PaddleOCR-VL-1.5 + llama.cpp Implementation Plan

## 1. Architecture Overview

```
Frontend
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  Python FastAPI Backend (port ~8000)                     │
│  backend/python-onnx/app/                               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. LayoutDetection                                     │
│     - PP-DocLayout ONNX (existing)                     │
│       pp_doclayout_onnx.py                             │
│                                                          │
│  2. VLRecognition (llama-cpp-server backend)            │
│     - Crop layout regions → PNG base64                  │
│     - Build chat prompt                                 │
│     - POST /v1/chat/completions → llama-server URL     │
│     - Post-process: truncate / OTSL→HTML / LaTeX        │
│                                                          │
│  3. llama-manager client (LlamaManagerClient)            │
│     - Discovers server URL from Rust llama-manager      │
│     - Fallback: auto-start if not running              │
└──────────────────────────────────────────────────────────┘
    │
    │  HTTP (port 8081)
    ▼
┌──────────────────────────────────────────────────────────┐
│  Rust llama-manager (port 8081)                          │
│  backend/llama-manager/                     │
│                                                          │
│  - Manages llama-server subprocess lifecycle           │
│  - Auto-discovers GGUF models from models_dir         │
│  - HTTP API: /start, /stop, /status, /models         │
│  - Future: direct VLM inference via oar-ocr-vl candle  │
└──────────────────────────────────────────────────────────┘
    │
    │  spawn subprocess
    ▼
┌──────────────────────────────────────────────────────────┐
│  llama-server (port ~8080, dynamic)                     │
│  references/llama.cpp/build/bin/llama-server           │
│                                                          │
│  HTTP REST API (OpenAI-compatible):                     │
│  POST /v1/chat/completions                             │
│  - GGUF quantized LLM inference                       │
│  - Multimodal: --mmproj mmproj.gguf                  │
└──────────────────────────────────────────────────────────┘
```
Input Image
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  PaddleOCR-VL-1.5 Pipeline (Python/FastAPI)            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. DocPreprocessor (optional ONNX)                     │
│     - DocOrientationClassify (ONNX)                     │
│     - DocUnwarping (ONNX)                               │
│                                                          │
│  2. LayoutDetection                                     │
│     - PP-DocLayoutV2/V3 (ONNX, existing)               │
│       backend/python-onnx/pp_doclayout_onnx.py         │
│                                                          │
│  3. VLRecognition (llama.cpp backend)                   │
│     - Crop layout regions → base64 PNG                  │
│     - Build chat prompt with Jinja template             │
│     - POST /v1/chat/completions → llama-server         │
│       (OpenAI-compatible HTTP API)                      │
│     - Parse response text                               │
│       - Truncate repetitive content                     │
│       - OTSL → HTML (tables)                           │
│       - LaTeX formatting (formulas)                    │
└──────────────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  llama.cpp llama-server (separate process / binary)       │
│  references/llama.cpp/tools/server/                     │
│                                                          │
│  HTTP REST API (OpenAI-compatible):                     │
│  POST /v1/chat/completions                              │
│  - Receives base64 PNG image + text prompt              │
│  - GGUF quantized LLM inference (CPU/GPU)              │
│  - Returns generated text                               │
└──────────────────────────────────────────────────────────┘
```

## 2. Key Reference Files

### PaddleX GenAI Infrastructure (llama.cpp client side)
| File | Purpose |
|------|---------|
| `references/PaddleX/paddlex/inference/models/common/genai.py` | `GenAIClient`, `GenAIConfig`, `_AsyncThreadManager` (async HTTP via `openai.AsyncOpenAI`), `SERVER_BACKENDS` list including `"llama-cpp-server"` |
| `references/PaddleX/paddlex/inference/models/predictors/genai_client_predictor.py` | `GenAIClientPredictor` base class — wraps `GenAIClient`, validates backend in `SERVER_BACKENDS` |
| `references/PaddleX/paddlex/inference/models/doc_vlm/predictor.py` | `DocVLMGenAIClientPredictor` — **the most critical file** |
| `references/PaddleX/paddlex/inference/pipelines/paddleocr_vl/pipeline.py` | `_PaddleOCRVLPipeline` — orchestrates layout detection + VLM calls |
| `references/PaddleX/paddlex/inference/genai/chat_templates/PaddleOCR-VL-1.5-0.9B.jinja` | Jinja chat template for PaddleOCR-VL-1.5 |

### llama.cpp Server
| File | Purpose |
|------|---------|
| `references/llama.cpp/tools/server/` | `llama-server` binary — HTTP server with OpenAI-compatible API |
| `references/llama.cpp/gguf-py/` | Python GGUF bindings |

### DocLayout ONNX (already implemented)
| File | Purpose |
|------|---------|
| `backend/python-onnx/app/core/pp_onnx/pp_doclayout_onnx.py` | `PPDocLayoutONNX` — existing layout detection |
| `backend/python-onnx/app/core/pp_onnx/onnx_model_base.py` | `ONNXModelBase` base class |

## 3. Critical Implementation Details

### 3.1 llama.cpp Backend Specific Handling
From `references/PaddleX/paddlex/inference/models/doc_vlm/predictor.py:449-519`:

```python
# Image format: llama-cpp-server uses PNG, others use JPEG
if client.backend == "llama-cpp-server":
    image_format = "PNG"
else:
    image_format = "JPEG"

# max_tokens parameter name differs
if client.backend in ["mlx-vlm-server", "llama-cpp-server"]:
    max_tokens_name = "max_tokens"
else:
    max_tokens_name = "max_completion_tokens"

# skip_special_tokens support
if client.backend in ("fastdeploy-server", "vllm-server", "sglang-server",
                      "mlx-vlm-server", "llama-cpp-server"):
    kwargs["extra_body"]["skip_special_tokens"] = skip_special_tokens

# repetition_penalty goes to extra_body
if repetition_penalty is not None:
    kwargs["extra_body"]["repetition_penalty"] = repetition_penalty
```

### 3.2 Chat Template
`PaddleOCR-VL-1.5-0.9B.jinja` uses special tokens:
- `<|begin_of_sentence|>` — BOS token
- `<|IMAGE_START|><|IMAGE_PLACEHOLDER|><|IMAGE_END|>` — image placeholder
- `</s>` — EOS token
- Format: `User: <|IMAGE|> <text>\nAssistant:\n<response></s>`

### 3.3 VLM Prompts by Layout Type
From `pipeline.py:309-358`:
| Layout Label | Prompt |
|---|---|
| text, paragraph, etc. | `"OCR:"` |
| table | `"Table Recognition:"` |
| chart | `"Chart Recognition:"` |
| formula | `"Formula Recognition:"` |
| spotting | `"Spotting:"` |
| seal | `"Seal Recognition:"` |

### 3.4 Response Post-processing
From `pipeline.py:440-471`:
1. Truncate repetitive content (`truncate_repetitive_content`, min_count=50/5000)
2. Convert OTSL → HTML for tables (`convert_otsl_to_html`)
3. Convert LaTeX delimiters: `\\(` → ` $ `, `\\[` → ` $$ `
4. Post-process spotting results

## 4. Implementation Steps

### Phase 1: Backend Infrastructure
1. **Create `app/core/pp_vl/genai_client.py`**
   - `GenAIConfig` dataclass with `backend="llama-cpp-server"`, `server_url`, `max_concurrency`
   - `GenAIClient` class wrapping `openai.AsyncOpenAI`
   - `_AsyncThreadManager` for async HTTP from sync context
   - `SERVER_BACKENDS = ["llama-cpp-server", ...]`

2. **Create `app/core/pp_vl/vlm_predictor.py`**
   - `DocVLMGenAIClientPredictor` class
   - `process()` method: encode image → PNG base64 → HTTP POST → parse text
   - Implement all llama-cpp-server-specific parameter handling
   - Batching support via `DocVLMBatchSampler`

### Phase 2: Layout + VLM Pipeline
3. **Create `app/core/pp_vl/pipeline.py`**
   - `PaddleOCRVLPipeline` class
   - Orchestrate: layout detection → crop regions → batch by pixel resolution → VLM call → post-process
   - Copy prompt logic from `references/PaddleX/.../pipeline.py:get_layout_parsing_results()`
   - Implement repetitive content truncation, OTSL→HTML, LaTeX formatting

4. **Integrate existing `PPDocLayoutONNX`** for layout detection

### Phase 3: API Layer
5. **Create `app/router/ppocr_vl.py`**
   - FastAPI router with `/api/ppocr_vl/predict` endpoint
   - Accept image path/URL/numpy array
   - Return structured results with layout + text

6. **Update `app/main.py`**
   - Add `ppocr_vl_router`

### Phase 4: Configuration
7. **Update `app/config.py`**
   - Add `PaddleOCR-VL-1.5-0.9B` model registry entry (HuggingFace/ModelScope)
   - Add `pp_ocr_vl` pipeline config
   - Add model options for layout detection models

8. **Add chat template**
   - Copy `PaddleOCR-VL-1.5-0.9B.jinja` to `app/core/pp_vl/chat_templates/`

### Phase 5: llama.cpp Server Integration
9. **Launcher/manager for llama-server**
   - Option A: User launches `llama-server` separately (like PaddleX design)
   - Option B: Integrated subprocess launcher within Python
   - Key: `--host`, `--port`, `--model`, `--mmproj` (multimodal projector) flags

## 5. Important Considerations

### llama.cpp Multimodal Support (官方验证通过)
- PaddlePaddle 官方在 HuggingFace 提供了预转换好的 GGUF 模型
  - `PaddlePaddle/PaddleOCR-VL-1.5-GGUF`
    - `PaddleOCR-VL-1.5-GGUF.gguf` — LLM主干
    - `PaddleOCR-VL-1.5-GGUF-mmproj.gguf` — Siglip视觉投影层
- llama.cpp `llama-server` 通过 `--mmproj` 加载多模态
- 启动命令（官方文档）：
  ```bash
  ./llama-server \
    -m PaddleOCR-VL-1.5-GGUF.gguf \
    --mmproj PaddleOCR-VL-1.5-GGUF-mmproj.gguf \
    --host 127.0.0.1 --port 8080 -fa
  ```

### llama-manager 的角色
- 已在 Rust 中实现 `llama-manager`（独立项目 `llama-manager/`）
- 与 rust-onnx、python-onnx 并列的后端项目
- 管理 llama-server 子进程生命周期（启动/停止/健康检查）
- 自动扫描 GGUF 模型目录
- HTTP API 给 Python 后端使用
- 预留未来直接 VLM 推理接口（基于 oar-ocr-vl 的 candle 实现）

### Async Architecture
The `GenAIClient` uses `openai.AsyncOpenAI` with an async thread manager (`_AsyncThreadManager`) to bridge sync code → async HTTP. This is critical because FastAPI/Starlette handlers are async, but the `openai` client is async-native.

### PaddleOCR-VL-1.5 Specific
- Entity: `"PaddleOCR-VL-1.5"`
- Default `max_new_tokens`: 4096 (from `PADDLEOCR_VL_MAX_NEW_TOKENS`)
- `PADDLEOCR_VL_GENAI_CLIENT_BATCH_SIZE`: used for VLM batching
- The model supports `min_pixels` / `max_pixels` for dynamic image resolution

## 6. File Structure (Implemented)

```
backend/python-onnx/app/
├── core/
│   └── pp_vl/
│       ├── __init__.py
│       ├── genai_client.py           # GenAIClient, GenAIConfig, AsyncThreadManager
│       ├── vlm_predictor.py          # DocVLMGenAIClientPredictor
│       ├── pipeline.py               # PaddleOCRVLPipeline
│       ├── batch_sampler.py          # DocVLMBatchSampler
│       ├── llama_manager_client.py   # LlamaManagerClient (Python side)
│       └── utils/
│           ├── __init__.py
│           ├── postprocess.py        # truncate, OTSL→HTML, LaTeX
│           └── crop.py              # crop, merge_blocks
├── router/
│   └── ppocr_vl.py                  # FastAPI router (uses llama-manager)
├── config.py                        # added pp_ocr_vl pipeline
└── main.py                         # registered /api/ppocr_vl

backend/rust-onnx/
    ├── Cargo.toml                  # members: ocr-lib, ocr-server
    ├── ocr-lib/
    └── ocr-server/

backend/llama-manager/              # llama-server lifecycle manager
    ├── Cargo.toml
    ├── build.rs                    # detects third_party/llama.cpp build
    └── src/
        ├── lib.rs
        ├── main.rs
        ├── server.rs               # llama-server subprocess management
        ├── routes.rs               # HTTP API routes
        ├── models.rs               # GGUF model discovery
        └── error.rs                # error types
    └── third_party/
        └── llama.cpp/              # git submodule (ggml-org/llama.cpp)

third_party/
└── llama.cpp/                     # git submodule, shared across backends

frontend/src/
├── pages/
│   └── PaddleOCRVLPage.tsx         # VLM page (new)
└── App.tsx                         # added /ppocr-vl route
```

## 7. 待补充信息 (请补充以下内容)

### 7.1 llama-server 编译
llama.cpp 已作为 git submodule 集成在 `third_party/llama.cpp`。
首次设置需执行 submodule init + cmake 编译，详见 7.4 节。

### 7.2 GGUF 模型信息
需要补充到 `config.py` 的 `MODEL_REGISTRY`：
```python
"PaddleOCR-VL-1.5-GGUF": {
    "modelscope_id": "PaddlePaddle/PaddleOCR-VL-1.5-GGUF",
    "local_path": "models/PaddleOCR-VL-1.5-GGUF",
    "label": "PaddleOCR-VL-1.5 GGUF",
    "description": "...",
}
```
需确认 HuggingFace 官方地址或 ModelScope 地址：
- HuggingFace: `PaddlePaddle/PaddleOCR-VL-1.5-GGUF`
  - 包含: `PaddleOCR-VL-1.5-GGUF.gguf` (LLM主干) + `PaddleOCR-VL-1.5-GGUF-mmproj.gguf` (视觉投影)

### 7.3 模型本地目录结构
```
models/llama/
└── PaddleOCR-VL-1.5-GGUF/   (llama-manager 自动扫描此目录)
    ├── PaddleOCR-VL-1.5-GGUF.gguf
    └── PaddleOCR-VL-1.5-GGUF-mmproj.gguf
```

### 7.4 llama-manager 启动方式

#### 首次设置

```bash
# 初始化 git submodule（llama.cpp）
git submodule update --init --recursive

# 编译 llama-server（第三方库）
cd third_party/llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --target llama-server
```

#### 编译 & 运行

```bash
cd backend/llama-manager
cargo build --release

# 启动
./target/release/llama-manager

# 或指定配置
MODELS_DIR=/path/to/models LLAMA_MANAGER_PORT=8081 ./llama-manager
```

#### llama-manager 架构

- `build.rs` — 检测 `third_party/llama.cpp/build/` 中的 llama-server
- `src/server.rs` — 查找顺序: `LLAMA_SERVER_PATH` env > `LLAMA_MANAGER_LLAMA_SERVER_PATH` > submodule build > 常见路径
- `third_party/llama.cpp` 位于项目根目录，供所有后端共享
