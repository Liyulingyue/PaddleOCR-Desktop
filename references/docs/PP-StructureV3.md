# PP-StructureV3 概览（简明参考） ✅

## 简介
PP-StructureV3 是 PaddlePaddle 提供的通用文档解析（document parsing / layout analysis）流水线，基于 Layout Parsing v1 演进，增强了版面检测、表格识别、公式识别、图表解析与阅读顺序恢复能力，支持将解析结果导出为 Markdown 并适配多种硬件与语言的服务化部署。适用于图片与 PDF 的复杂版面场景。 

---

## Pipeline 概览 🔧
PP-StructureV3 将任务拆分为若干模块 / 子流水线（可独立训练与推理）：
- 布局检测（Layout Detection）
- 通用 OCR 子流（Text detection/recognition）
- 文档图像预处理（可选）
- 表格识别子流 Table Recognition（可选）
- 印章/章识别（Seal Recognition，可选）
- 公式识别（Formula Recognition，可选）
- 图表解析（Chart Parsing，可选，如 PP-Chart2Table）

模块间通用流程：先做版面分割 -> 针对分区调用相应子模块（OCR/表格/公式/图表）-> 合并并恢复阅读顺序 -> 可选导出为 Markdown/结构化数据。

---

## 常用/核心模型（示例） 📦
文档中列出了大量备选模型，下面为在 PP-StructureV3 中常见的核心模型及官方推理/预训练模型示例链接：

- 文档方向分类：`PP-LCNet_x1_0_doc_ori`
  - 推理模型：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar
  - 预训练权重：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_pretrained_model/PP-LCNet_x1_0_doc_ori_pretrained.pdparams

- 文本纠偏（Rectification）：`UVDoc`
  - 推理模型：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/UVDoc_infer.tar

- 布局检测：`PP-DocLayout-L / -M / -S`（RT-DETR / PicoDet 等后端）
  - 推理模型（示例）：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout-L_infer.tar

- 表结构识别（Table Structure）：`SLANeXt_wired / SLANeXt_wireless`
  - 推理模型：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/SLANeXt_wired_infer.tar

- 表格单元检测：`RT-DETR-L_wired_table_cell_det`（示例）
  - 推理模型：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wired_table_cell_det_infer.tar

- 公式识别：`PP-FormulaNet-L`（文档中有详细说明与模型链接）

- 图表解析（Chart -> Table）：`PP-Chart2Table`
  - 推理模型：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-Chart2Table_infer.tar
  -（注：2025-06-27 有升级版本，旧版备份也在文档提供）

- OCR 基础模型：`PP-OCRv5` 系列（det/rec）
  - 示例推理模型：https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_det_infer.tar

> 注：完整模型清单与更多备选模型请参见官方教程页面（下方链接）。

---

## 如何获取 / 下载预训练与推理模型（快速指南） ⬇️
1. 官方文档里给出了每个模型的两个常见资源：Inference Model（用于部署的动转静打包好的推理包 .tar）和 Pretrained Model（训练时使用的 pdparams/检查点）。
2. 可使用 wget/curl 直接下载并解压（示例）：
   - Linux / WSL / Git Bash：
     - wget https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-Chart2Table_infer.tar && tar xf PP-Chart2Table_infer.tar
   - Windows PowerShell：
     - Invoke-WebRequest -Uri <URL> -OutFile PP-Chart2Table_infer.tar; tar -xf PP-Chart2Table_infer.tar
3. 使用 PaddleOCR / Paddlex 的 Pipeline 或 CLI：
   - 快速推理命令（会自动使用在线模型 / 本地模型）：
     - paddleocr pp_structurev3 -i <IMAGE_OR_PDF_URL_or_PATH> --use_doc_orientation_classify False --use_doc_unwarping False
   - Python API 示例：
     - from paddleocr import PPStructureV3
       pipeline = PPStructureV3()
       output = pipeline.predict("./pp_structure_v3_demo.png")
4. 若需要离线部署：请下载相应的 Inference Model（.tar），并按 README 或各模块 README 中说明替换模型路径（通常需要解 tar 后把模型目录路径传入 `--model_dir` 或 `*_model_dir` 参数）。

---

## 运行环境与注意事项 ⚠️
- 推荐：Paddle 3.0、PaddleOCR 3.0.0（文档中给出基准时使用的版本信息）。
- 部分硬件（NPU/XPU）或产线推理示例文档也有说明，可参照 docs 中 `other_devices_support` 章节。
- PP-StructureV3 包含许多可选模块，按需开启（例如图表/公式/表格模块会增加推理时间）。

---

## 快速参考链接 🔗
- PP-StructureV3 Tutorial（中文/英文文档）:
  - docs: references/repos/PaddleOCR/docs/version3.x/pipeline_usage/PP-StructureV3.md
  - 英文在线：https://paddlepaddle.github.io/PaddleOCR/latest/version3.x/pipeline_usage/PP-StructureV3.html
- Chart Parsing (PP-Chart2Table) Module: docs/version3.x/module_usage/chart_parsing.en.md
- 模型存储（示例）: https://paddle-model-ecology.bj.bcebos.com/paddlex/

---

如果你希望我把文档扩展为更详细的表格（列出所有模块和每个模型的完整下载链接、大小、性能指标），我可以继续把 `references/PP-StructureV3.md` 扩充为详尽的模型清单版。🎯
