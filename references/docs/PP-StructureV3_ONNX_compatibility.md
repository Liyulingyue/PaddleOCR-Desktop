# PP-StructureV3 模型 ONNX 转换兼容性清单 ✅

## 兼容性表（仅限 PP-StructureV3 流水线模块）

| 模块 | 典型模型（示例） | 推理模型可得 | ONNX 支持（建议） | 备注 / 建议 |
|---|---|:---:|:---:|---|
| 文档方向分类 | `PP-LCNet_x1_0_doc_ori` | ✅ | ✅（可直接转） | 小型分类网络，转换稳定，建议验证精度。 |
| 文档纠偏（图像纠正） | `UVDoc` | ✅ | ✅（需验证输入/动态 shape） | 主要是几何变换网络，建议用动态 shape 并验证像素级输出/效果。 |
| 布局检测（Layout） | `PP-DocLayout-L / M / S`（RT-DETR / PicoDet 后端） | ✅ | ✅（已多次成功） | RT-DETR / PicoDet 在社区与文档中有成功转换案例，注意后处理输出格式。 |
| PicoDet 版面变体 | `PicoDet_layout_*` | ✅ | ✅ | 轻量且适合 ONNXRuntime，注意类别/后处理一致性。 |
| OCR 子流（Text det/rec/cls） | `PP-OCRv5`（det / rec / cls） | ✅ | ✅（强烈建议动态 shape） | OCR 类模型通常可转，需对识别结果做语义级验证（如文本编辑距离）。 |
| 表格单元检测 | `RT-DETR-L_table_cell_det` | ✅ | ✅ | 单元检测可转，后续的表格合并/结构化需验证。 |
| 表格结构识别 | `SLANeXt_wired / SLANeXt_wireless` | ✅ | ✅（需验证） | 结构化输出（cells->structure）需做语义一致性验证。 |
| 公式识别 | `PP-FormulaNet-*` | ✅ | ✅（需验证） | 模型有推理包，建议逐个转并对公式解析结果做语义比对。 |
| 图表解析（Chart2Table） | `PP-Chart2Table` | ✅ | 需验证（建议先尝试） | 多步骤/多输出（检测->表格解析），转换后重点验证表格语义与单元边界。 |