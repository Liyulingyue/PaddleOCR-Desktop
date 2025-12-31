# PP-DocLayout ONNX Inference

这是一个独立的PP-DocLayout ONNX推理实现，用于文档布局检测。

## 功能

- 自动从 `inference.yml` 配置文件加载模型参数和标签列表
- 支持加载PP-DocLayout-L ONNX模型
- 实现图像预处理（resize、normalize）
- 执行ONNX推理
- 后处理输出为布局区域
- 可视化检测结果

## 配置加载

代码会自动从模型目录下的 `inference.yml` 文件中加载以下配置：

- **标签列表** (`label_list`): 23种布局类型
- **预处理参数**: 目标尺寸、均值、标准差
- **模型信息**: 模型名称、架构类型
- **检测阈值**: 默认检测阈值

## 支持的布局类型

从配置文件自动加载的23种布局类型：
- `paragraph_title`: 段落标题
- `image`: 图片
- `text`: 文本
- `number`: 数字
- `abstract`: 摘要
- `content`: 内容
- `figure_title`: 图标题
- `formula`: 公式
- `table`: 表格
- `table_title`: 表格标题
- `reference`: 参考文献
- `doc_title`: 文档标题
- `footnote`: 脚注
- `header`: 页眉
- `algorithm`: 算法
- `footer`: 页脚
- `seal`: 印章
- `chart_title`: 图表标题
- `chart`: 图表
- `formula_number`: 公式编号
- `header_image`: 页眉图片
- `footer_image`: 页脚图片
- `aside_text`: 旁注文本

## 标签到下游模型映射

下面列出 **PP-DocLayout** 输出标签及其在产线中的**默认下游处理**（实际行为可能受产线配置开关影响，如 `use_table_recognition` 等）：

- **paragraph_title**: 通用 OCR（标题识别）
- **image**: 保存为图片（可视化 / 导出）
- **text**: 通用 OCR
- **number**: 通用 OCR
- **abstract**: 通用 OCR
- **content**: 通用 OCR
- **figure_title**: 通用 OCR（图题文字）
- **formula** / **equation**: 公式识别子产线（需启用 `use_formula_recognition`，产出 LaTeX/公式文本）
- **table**: 表格识别子产线（`TableSystem`），可生成 HTML/XLSX，通常会结合 OCR 提取单元格文本
- **table_title**: 通用 OCR（表格标题）
- **reference**: 通用 OCR（参考文献区）
- **doc_title**: 通用 OCR（文档标题）
- **footnote**: 通用 OCR（页脚注）
- **header**: 通用 OCR（页眉）
- **algorithm**: 通用 OCR（算法块文字）
- **footer**: 通用 OCR（页脚）
- **seal**: 印章识别子产线（`SealRecognition`，需启用 `use_seal_recognition`）
- **chart_title**: 通用 OCR（图表标题）
- **chart**: 图表识别子产线（需启用 `use_chart_recognition`）；未启用时通常作为图片处理
- **formula_number**: 通用 OCR / 与公式识别相关（公式编号）
- **header_image**: 保存为图片
- **footer_image**: 保存为图片
- **aside_text**: 通用 OCR（旁注文本）

**实现位置与细节**：
- **通用 OCR 路由**：在 `ppstructure/predict_system.py` 的 `StructureSystem` 中实现（先对整张图做一次 `TextSystem` OCR，再用 layout bbox 过滤 OCR 结果以提高准确率）。
- **表格**：表格识别与导出由 `ppstructure/table/predict_table.py` 中的 `TableSystem` 处理；可选择是否用 OCR 结果填充单元格文本（配置项例如 `use_ocr_results_with_table_cells`）。
- **公式**：由公式识别子产线处理（见公式模块相关实现），产出 LaTeX/识别结果。
- **印章**：由 SealRecognition / 印章子产线处理（需要开启 `use_seal_recognition`）。
- **可视化/保存**：`ppstructure/predict_system.py` 中的 `save_structure_res` 会将 `figure`/`image` 区域保存为 JPEG；对于 `table`，若包含 HTML，会导出为 Excel。

**注意**：
- 标签名称以模型目录下的 `inference.yml` 中的 `label_list` 为准，不同模型（或字典）中标签命名可能有细微差别。
- 下游是否启用与产线参数相关（例如 `use_table_recognition`, `use_formula_recognition`, `use_seal_recognition`, `use_chart_recognition`）。

---

## 使用方法

### 命令行使用

```bash
# 使用虚拟环境Python
cd /path/to/PaddleOCR-Desktop/references
.venv/bin/python run_pp_doclayout.py <image_path> [output_visualization_path]
```

示例：
```bash
.venv/bin/python run_pp_doclayout.py test_document.png result.png
```

### Python API使用

```python
from AppDemo.pp_doclayout_onnx import PPDocLayoutONNX
import cv2

# 初始化检测器
detector = PPDocLayoutONNX()

# 加载图像
image = cv2.imread('test_document.png')

# 运行检测
regions = detector.detect(image, conf_threshold=0.3)

# 打印结果
for region in regions:
    print(f"{region['type']} (conf: {region['confidence']:.3f}) - bbox: {region['bbox']}")

# 可视化
vis_image = detector.visualize(image, regions, 'result.png')
```

## 输出格式

检测结果为区域列表，每个区域包含：
- `bbox`: [x1, y1, x2, y2] 边界框坐标
- `type`: 布局类型字符串
- `confidence`: 置信度分数 (0-1)

## 依赖

- onnxruntime
- opencv-python
- numpy

## 模型

使用PP-DocLayout-L ONNX模型，位于 `models/pp_structure_v3_onnx/PP-DocLayout-L/inference.onnx`

## 坐标转换说明

PP-DocLayout ONNX模型内部已经完成了坐标缩放处理，输出坐标直接在原始图像坐标系中。

1. **预处理**: 图像被拉伸到640×640，输入模型
2. **模型内部**: 模型使用scale_factor参数进行坐标缩放计算
3. **后处理**: 模型输出已经是原始图像坐标系中的坐标，无需额外转换

因此，后处理阶段不再需要手动进行坐标缩放。

## 注意事项

- 模型输入尺寸为640x640
- 默认置信度阈值为0.3，可根据需要调整
- 模型输出坐标直接在原始图像坐标系中，无需额外转换