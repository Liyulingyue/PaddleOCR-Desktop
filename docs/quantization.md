# PaddleOCR-VL 模型量化流程

本项目依赖 [PaddlePaddle/PaddleOCR-VL](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.5) GGUF 格式模型。HuggingFace 上有两个仓库可选：直接下载已转换好的 [GGUF 仓库](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.5-GGUF)，或从原始模型仓库下载后自行转换。

以下步骤在 `models/` 工作目录中执行：

```bash
cd /path/to/PaddleOCR-Desktop/models
```

## 1. 环境准备

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .\.venv\\Scripts\\activate   # Windows

# 安装 huggingface_hub
pip install -U huggingface_hub

# （可选）使用国内镜像加速
export HF_ENDPOINT=https://hf-mirror.com
```

## 2. 获取模型文件

### 方案 A：直接从 GGUF 仓库下载（推荐）

```bash
# 主模型（FP16，936MB）
hf download PaddlePaddle/PaddleOCR-VL-1.5-GGUF \
    PaddleOCR-VL-1.5.gguf --local-dir .

# 视觉投影器 mmproj（FP16，882MB）
hf download PaddlePaddle/PaddleOCR-VL-1.5-GGUF \
    PaddleOCR-VL-1.5-mmproj.gguf --local-dir .

# Chat 模板
hf download PaddlePaddle/PaddleOCR-VL-1.5-GGUF \
    chat_template.jinja --local-dir .
```

### 方案 B：从原始模型仓库下载（用于 mmproj 转换）

mmproj 无法直接从 GGUF 仓库的 `.mmproj.gguf` 量化，需从原始模型转换：

```bash
# 下载原始模型（包含 mmproj 权重）
hf download PaddlePaddle/PaddleOCR-VL-1.5 \
    --local-dir ./PaddlePaddle/PaddleOCR-VL-1.5
```

转换所需的 Python 依赖在量化方式 B 的步骤中安装。

## 3. 编译 llama.cpp

```bash
cd $(dirname $(pwd))/third_party/llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j $(nproc)
```

## 4. 量化

### 量化方式 A：直接量化 GGUF 仓库的主模型

主模型下载自 GGUF 仓库，可直接量化：

```bash
cd /path/to/PaddleOCR-Desktop/models

# 量化主模型（Q4_K_M 约 236MB，推荐）
$(dirname $(pwd))/third_party/llama.cpp/build/bin/llama-quantize \
    ./PaddleOCR-VL-1.5.gguf \
    ./PaddleOCR-VL-1.5-Q4_K_M.gguf \
    Q4_K_M
```

### 量化方式 B：转换 + 量化 mmproj

`convert_hf_to_gguf.py` 支持 `--outtype` 参数，可在转换时直接量化，而非事后用 `llama-quantize`。适用于主模型和 mmproj。

> **说明**：`llama-quantize` 无法量化 clip 架构的 mmproj（会报 `unsupported model architecture: 'clip'`）。需使用 `convert_hf_to_gguf.py --mmproj --outtype` 在转换时直接量化。

将原始模型的 mmproj 转换为 GGUF，再量化：

```bash
cd /path/to/PaddleOCR-Desktop/models

# 安装转换依赖
pip install -r $(dirname $(pwd))/third_party/llama.cpp/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 

# 转换 + 量化 mmproj（Q8_0）
python $(dirname $(pwd))/third_party/llama.cpp/convert_hf_to_gguf.py \
    ./PaddlePaddle/PaddleOCR-VL-1.5 \
    --outfile ./PaddleOCR-VL-1.5-mmproj-q8_0.gguf \
    --outtype q8_0 \
    --mmproj

# 同理，主模型也可通过此方式量化（去掉 --mmproj）
python $(dirname $(pwd))/third_party/llama.cpp/convert_hf_to_gguf.py \
    ./PaddlePaddle/PaddleOCR-VL-1.5 \
    --outfile ./PaddleOCR-VL-1.5-q8_0.gguf \
    --outtype q8_0
```

## 5. 全部量化类型

| 类型 | 描述 |
|------|------|
| **Q8_0** | 8位量化，几乎无损，体积约为FP16的50% |
| **Q6_K** | 6位量化，质量损失极低 |
| **Q5_K_M** | 5位中质量，约70%压缩率 |
| **Q5_K_S** | 5位小体积 |
| **Q4_K_M** | 4位中质量，**推荐**，约75%压缩率 |
| **Q4_K_S** | 4位小体积 |
| **Q4_K** | Q4_K_M 的别名 |
| **Q3_K_M** | 3位中质量，约80%压缩率 |
| **Q3_K_S** | 3位小体积 |
| **Q3_K_L** | 3位大体积 |
| **Q3_K** | Q3_K_M 的别名 |
| **Q2_K** | 2位量化，体积最小但质量损失明显 |
| **Q2_K_S** | Q2_K 的小体积变体 |
| **IQ4_XS** | 4.25 bpw 非线性量化 |
| **IQ4_NL** | 4.50 bpw 非线性量化 |
| **IQ3_XXS** | 3.06 bpw 量化 |
| **IQ3_S** | 3.44 bpw 量化 |
| **IQ3_M** | 3.66 bpw 量化混合 |
| **IQ3_XS** | 3.3 bpw 量化 |
| **IQ2_XXS** | 2.06 bpw 量化 |
| **IQ2_XS** | 2.31 bpw 量化 |
| **IQ2_S** | 2.5 bpw 量化 |
| **IQ2_M** | 2.7 bpw 量化 |
| **IQ1_S** | 1.56 bpw 量化 |
| **IQ1_M** | 1.75 bpw 量化 |
| **Q4_0** | 传统4位量化 |
| **Q4_1** | 传统4位量化（改进版） |
| **Q5_0** | 传统5位量化 |
| **Q5_1** | 传统5位量化（改进版） |
| **Q1_0** | 1.125 bpw 量化 |
| **F16** | 半精度浮点，无量化 |
| **BF16** | BFloat16，无量化 |
| **F32** | 单精度浮点，无量化 |

> bpw = bits per weight（每权重位数）

### Importance Matrix 量化（更高质量，可选）

```bash
# 生成重要性矩阵（需要校准数据）
$(dirname $(pwd))/third_party/llama.cpp/build/bin/llama-imatrix \
    -m ./PaddleOCR-VL-1.5.gguf \
    -f ./calibration.txt \
    --output ./imatrix.dat

# 使用 imatrix 量化
$(dirname $(pwd))/third_party/llama.cpp/build/bin/llama-quantize \
    -m ./PaddleOCR-VL-1.5.gguf \
    ./PaddleOCR-VL-1.5-Q4_K_M.gguf \
    Q4_K_M \
    --imatrix ./imatrix.dat
```

`calibration.txt` 应包含与 OCR 场景相似的文本样本，每行一条。

## 6. 模型目录结构

```
/path/to/PaddleOCR-Desktop/models/
├── .venv/                                  # 虚拟环境
├── PaddleOCR-VL-1.5-Q4_K_M.gguf       # 主模型（量化后）
├── PaddleOCR-VL-1.5.gguf              # 主模型（原始FP16，可删除）
├── PaddleOCR-VL-1.5-mmproj-q8_0.gguf # 视觉投影器（Q8_0 量化）
├── PaddlePaddle/PaddleOCR-VL-1.5/    # 原始模型目录（方案B，可删除）
└── chat_template.jinja                 # Chat 模板
```

llama-manager 默认扫描 `~/.local/share/PaddleOCR-Desktop/models/llama/`，如需使用其他目录，设置 `MODELS_DIR` 环境变量指向此工作目录。

### 清理中间文件

量化完成后，可删除不再需要的中间文件以节省空间：

```bash
# 删除原始模型目录（方案B下载的原始权重）
rm -rf ./PaddlePaddle/PaddleOCR-VL-1.5

# 删除原始 GGUF 文件（保留量化版本）
rm ./PaddleOCR-VL-1.5.gguf
```

## 7. 验证模型

```bash
cd /path/to/PaddleOCR-Desktop/models

# 测试加载
$(dirname $(pwd))/third_party/llama.cpp/build/bin/llama-cli \
    -m ./PaddleOCR-VL-1.5-Q4_K_M.gguf \
    --mmproj ./PaddleOCR-VL-1.5-mmproj-q8_0.gguf \
    --chat-template-file ./chat_template.jinja \
    -p "hello"
```

## 8. 在 llama-manager 中使用

> 设置 `MODELS_DIR` 为工作目录后，模型会被自动发现。

```bash
# 设置模型目录（可选）
export MODELS_DIR=/path/to/PaddleOCR-Desktop/models

# 查看已发现的模型
curl http://localhost:8081/models

# 启动服务（chat template 需通过 additional_args 传入）
curl -X POST http://localhost:8081/start \
    -H "Content-Type: application/json" \
    -d '{
        "model_name": "PaddleOCR-VL-1.5-GGUF",
        "additional_args": ["--chat-template-file", "./chat_template.jinja"]
    }'
```
