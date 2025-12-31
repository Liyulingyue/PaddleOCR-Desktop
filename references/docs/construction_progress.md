# PP-Structure-V3 ONNX实现施工进展

## 项目概述
本项目旨在实现PP-Structure-V3文档解析流水线的ONNX版本，包括模型转换、推理框架搭建和完整流水线集成。

## 已完成工作

### 1. 模型转换 ✅
- 使用paddlex将PP-StructureV3模型批量转换为ONNX格式
- 脚本：`scripts/convert_pp_structure_v3_to_onnx.sh`
- 输出：`models/pp_structure_v3_onnx/` 目录下多个模型的inference.onnx文件
- 日志：`paddle2onnx_conversion_results.csv`

### 2. 项目框架搭建 ✅
- 创建AppDemo包结构
- 入口脚本：`run_pp_structure_onnx.py`
- 主流水线：`AppDemo/pipeline.py`
- 工具函数：`AppDemo/utils.py`
- 依赖管理：`requirements_onnx.txt`
- 文档：`README_ONNX.md`

### 3. 部分组件实现 ✅
- 模型加载逻辑
- 流水线框架结构
- 结果输出格式（JSON/Markdown）

## 流水线组件状态

| 组件 | 模型 | 转换状态 | 推理实现 | 预处理 | 后处理 | 集成状态 |
|------|------|----------|----------|--------|--------|----------|
| 文档方向分类 | PP-LCNet_x1_0_doc_ori | ✅ | ❌ | ❌ | ❌ | ❌ |
| 文档纠偏 | UVDoc | ✅ | ❌ | ❌ | ❌ | ❌ |
| 布局检测 | PP-DocLayout-L | ✅ | ❌ | ❌ | ❌ | ❌ |
| 布局检测 | PP-DocLayout-M | ✅ | ❌ | ❌ | ❌ | ❌ |
| 布局检测 | PP-DocLayout-L | ✅ | ✅ (框架+调试) | ✅ | ❌ | ✅ |
| OCR检测 | PP-OCRv5_det | ✅ | ✅ (框架) | ✅ | ❌ | ✅ |
| OCR识别 | PP-OCRv5_rec | ✅ | ✅ (框架) | ✅ | ❌ | ✅ |
| OCR分类 | PP-OCRv5_cls | ❌ | ❌ | ❌ | ❌ | ❌ |
| 表格识别 | SLANeXt_wired | ✅ | ❌ | ❌ | ❌ | ❌ |
| 表格识别 | SLANeXt_wireless | ✅ | ❌ | ❌ | ❌ | ❌ |
| 表格单元检测 | RT-DETR-L_wired | ✅ | ❌ | ❌ | ❌ | ❌ |
| 表格单元检测 | RT-DETR-L_wireless | ✅ | ❌ | ❌ | ❌ | ❌ |
| 公式识别 | PP-FormulaNet-L | ✅ | ❌ | ❌ | ❌ | ❌ |
| 公式识别 | PP-FormulaNet-S | ✅ | ❌ | ❌ | ❌ | ❌ |
| 公式识别 | PP-FormulaNet_plus-M | ✅ | ❌ | ❌ | ❌ | ❌ |
| 公式识别 | PP-FormulaNet_plus-L | ✅ | ❌ | ❌ | ❌ | ❌ |
| 图表解析 | PP-Chart2Table | ✅ | ❌ | ❌ | ❌ | ❌ |
| 文档块布局 | PP-DocBlockLayout | ✅ | ❌ | ❌ | ❌ | ❌ |
| 增强布局 | PP-DocLayout_plus-L | ✅ | ❌ | ❌ | ❌ | ❌ |
| OCR移动端检测 | PP-OCRv5_mobile_det | ✅ | ❌ | ❌ | ❌ | ❌ |
| OCR移动端识别 | PP-OCRv5_mobile_rec | ✅ | ❌ | ❌ | ❌ | ❌ |
| 轻量布局检测 | PicoDet_layout_1x | ✅ | ❌ | ❌ | ❌ | ❌ |
| 轻量布局检测 | PicoDet_layout_1x_table | ✅ | ❌ | ❌ | ❌ | ❌ |
| 布局检测3类 | PicoDet-S_layout_3cls | ✅ | ❌ | ❌ | ❌ | ❌ |
| 布局检测17类 | PicoDet-S_layout_17cls | ✅ | ❌ | ❌ | ❌ | ❌ |

**图例：**
- ✅ 已完成
- ❌ 未完成/占位符

## 缺少的工作

### 1. 推理实现 (高优先级)
- 为每个ONNX模型实现具体的推理代码
- 包括输入预处理和输出后处理
- 需要参考原始Paddle模型的输入输出格式

### 2. 预处理模块 (高优先级)
- 图像缩放、归一化
- 不同模型的特定预处理（如PP-OCRv5的文本行处理）
- 动态输入尺寸处理

### 3. 后处理模块 (高优先级)
- 检测框解析
- 置信度过滤
- 结果格式化

### 4. 流水线集成 (中优先级)
- 组件间数据流
- 错误处理
- 性能优化

### 5. 测试和验证 (中优先级)
- 单元测试
- 与原始Paddle版本结果对比
- 性能基准测试

### 6. 文档和示例 (低优先级)
- 详细API文档
- 使用示例
- 故障排除指南

## 下一步计划
1. 实现布局检测的完整推理流程
2. 实现OCR检测和识别的推理
3. 逐步添加其他组件
4. 集成完整流水线
5. 性能测试和优化

## 技术债务
- 当前代码包含大量占位符，需要逐步替换为实际实现
- 缺少详细的错误处理和日志
- 模型配置硬编码，需要更灵活的配置系统