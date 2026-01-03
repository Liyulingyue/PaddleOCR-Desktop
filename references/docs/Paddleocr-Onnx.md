# PaddleOCR + ONNX（简明指南） ✅

## 简介
PaddleOCR 支持将 PaddlePaddle 的静态图推理模型转换为 ONNX 格式，方便使用 ONNX Runtime、OpenVINO 等推理后端做跨平台与加速部署。常用场景包括离线部署、使用非-Paddle 推理引擎、以及对推理性能/兼容性做二次优化。

---

## 何时使用 ONNX
- 希望在不安装完整 Paddle 运行时的环境中部署推理。 
- 使用 ONNXRuntime 或厂商加速库（例如 TensorRT、OpenVINO）做优化与加速。
- 需要将 Paddle 模型交付到其他平台或语言生态。

---

## 环境准备
- Python (建议 3.8+)
- pip install paddle2onnx onnx onnxruntime
  - 可选：`onnxruntime-gpu` 或其他 provider 的运行时
- 若使用 PaddleX CLI 的 paddle2onnx 插件：`paddlex --install paddle2onnx`

---

## 导出流程（推荐步骤） 🔧
1. 获取或导出 Paddle 静态图（Inference）模型：
   - 官方推理包可从 model zoo 下载（示例：`PP-OCRv3_mobile_det_infer.tar` 等）；或使用 `tools/export_model.py` 将训练权重导出为推理模型。

2. 使用 `paddle2onnx` 将静态图模型转换为 ONNX：

示例（Det / Rec / Cls）：

```
paddle2onnx --model_dir ./inference/PP-OCRv5_mobile_det_infer \
  --model_filename inference.pdmodel \
  --params_filename inference.pdiparams \
  --save_file ./inference/det_onnx/model.onnx \
  --opset_version 11 \
  --enable_onnx_checker True
```

- 常用 opset 版本：推荐 11；Paddle2ONNX 支持 opset 7~19，若转换失败会尝试更高版本。
- 对 OCR 类模型建议使用动态 shape（Paddle2ONNX 新版本已默认支持动态 shape）。
- 可使用 `paddlex --paddle2onnx` 作为另一种转换方式（PaddleX 插件）。

---

## 常见注意事项 / 限制 ⚠️
- 必须使用静态图（inference）模型作为输入；动态图需先导出为 inference 模型。
- OCR 模型需要启用动态 shape，否则可能出现数值差异或无法适配变化输入尺寸。
- 目前部分模型仍不支持导出为 ONNX（例如：NRTR、SAR、RARE、SRN，视具体文档更新为准）。
- 转换时建议开启 `--enable_onnx_checker True` 以进行 ONNX 校验。
- 若需要修改输入 shape：可使用 `python -m paddle2onnx.optimize --input_shape_dict "{'x': [-1,3,-1,-1]}"` 进行调整。
- 可使用 onnxslim 等工具做进一步瘦身优化。

---

## 使用 ONNXRuntime 推理（示例）
- 使用 PaddleOCR 的脚本（已集成对 ONNX 的支持）：

CPU / GPU 推理示例：

```
python tools/infer/predict_system.py --use_gpu=False --use_onnx=True \
  --det_model_dir=./inference/det_onnx/model.onnx \
  --rec_model_dir=./inference/rec_onnx/model.onnx \
  --cls_model_dir=./inference/cls_onnx/model.onnx \
  --image_dir=./docs/infer_deploy/images/lite_demo.png
```

或单模块推理（det/rec/cls）：
```
python tools/infer/predict_det.py --use_onnx=True --det_model_dir=./inference/det_onnx/model.onnx --image_dir=...
```

- 可通过 `--onnx_providers`、`--onnx_sess_options` 传递给 onnxruntime（参考 `tools/infer/utility.py` 中的实现）。

---

## 测试与验证
- 仓内有测试脚本（`test_tipc`）用于 Paddle2ONNX 的转换与推理回归测试；参考 `test_tipc/docs/test_paddle2onnx.md`。
- 转换后请使用 `--enable_onnx_checker True` 和模型自检脚本/单测做精度对比。

---

## 调优建议与工具
- 使用 `onnxslim` 或其他 ONNX 优化工具做模型瘦身（减少内存与加速推理）。
- 通过 ONNXRuntime 的 providers（CUDA/DirectML/ACL/EP）选择合适的后端加速。
- 对热点算子或不支持算子，考虑使用 PaddleInference 或手工替换算子实现。

---

## 参考链接 🔗
- 官方 Paddle2ONNX 仓库：https://github.com/PaddlePaddle/Paddle2ONNX
- 仓内文档：
  - docs/version3.x/deployment/obtaining_onnx_models.md（如何获取/转换）
  - docs/version2.x/legacy/paddle2onnx.md（详细转换与推理示例）
  - test_tipc/docs/test_paddle2onnx.md（转换/推理测试脚本）

---

如果你需要，我可以：
- 把 `references/Paddleocr-Onnx.md` 扩展为包含“每个常用模型的具体 paddle2onnx 转换命令表（含 opset、可选 optimize 命令）”；
- 或生成一个 Windows/PowerShell 的批量下载并转换脚本（供离线部署使用）。

请选择下一步，我会继续完善。🎯