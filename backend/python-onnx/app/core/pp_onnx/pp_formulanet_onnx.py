"""
PP-FormulaNet 公式识别 ONNX 推理实现

模型架构: PPHGNetV2 encoder + mBART decoder
功能: 将公式图像转换为 LaTeX 字符串

参考:
- ppocr/modeling/heads/rec_ppformulanet_head.py (PPFormulaNet_Head)
- ppocr/postprocess/rec_postprocess.py (UniMERNetDecode)
- ppocr/data/imaug/unimernet_aug.py (UniMERNetImgDecode, UniMERNetTestTransform)
- configs/rec/PP-FormulaNet/PP-FormulaNet-S.yaml
"""

import cv2
import numpy as np
import re
import yaml
from pathlib import Path
from typing import List, Optional, Tuple

from .preprocess import preprocess_formula_unimernet
from .onnx_model_base import ONNXModelBase


class UniMERNetTokenizer:
    """
    UniMERNet/HuggingFace tokenizer 封装
    参考自 ppocr/postprocess/rec_postprocess.py:UniMERNetDecode
    """

    BOS_TOKEN_ID = 0
    EOS_TOKEN_ID = 2
    PAD_TOKEN_ID = 1
    UNK_TOKEN_ID = 3

    def __init__(self, tokenizer_dir: str):
        from tokenizers import Tokenizer as TokenizerFast

        tokenizer_file = Path(tokenizer_dir) / "tokenizer.json"
        if not tokenizer_file.exists():
            raise FileNotFoundError(f"Tokenizer file not found at {tokenizer_file}")

        self.tokenizer = TokenizerFast.from_file(str(tokenizer_file))
        self.bos_token_id = self.BOS_TOKEN_ID
        self.eos_token_id = self.EOS_TOKEN_ID
        self.pad_token_id = self.PAD_TOKEN_ID
        self.unk_token_id = self.UNK_TOKEN_ID

    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """将 token IDs 解码为字符串"""
        return self.tokenizer.decode(token_ids, skip_special_tokens=skip_special_tokens)

    def id_to_token(self, token_id: int) -> Optional[str]:
        """根据 ID 获取 token"""
        return self.tokenizer.id_to_token(token_id)


class FormulaPostprocess:
    """
    公式识别后处理器
    参考自 ppocr/postprocess/rec_postprocess.py:UniMERNetDecode
    """

    def __init__(self, tokenizer_dir: str, is_infer: bool = True):
        self.tokenizer = UniMERNetTokenizer(tokenizer_dir)
        self.is_infer = is_infer

    def normalize_infer(self, s: str) -> str:
        """推理时的 LaTeX 规范化"""
        text_reg = r"(\\(operatorname|mathrm|text|mathbf)\s?\*? {.*?})"
        letter = "[a-zA-Z]"
        noletter = r"[\W_^\d]"
        names = []

        for x in re.findall(text_reg, s):
            pattern = r"(\\[a-zA-Z]+)\s(?=\w)|\\[a-zA-Z]+\s(?=})"
            matches = re.findall(pattern, x[0])
            for m in matches:
                if (
                    m not in ["\\operatorname", "\\mathrm", "\\text", "\\mathbf"]
                    and m.strip() != ""
                ):
                    s = s.replace(m, m + "XXXXXXX")
                    s = s.replace(" ", "")
                    names.append(s)

        if len(names) > 0:
            s = re.sub(text_reg, lambda match: str(names.pop(0)), s)

        news = s
        while True:
            s = news
            news = re.sub(r"(?!\\ )(%s)\s+?(%s)" % (noletter, noletter), r"\1\2", s)
            news = re.sub(r"(?!\\ )(%s)\s+?(%s)" % (noletter, letter), r"\1\2", news)
            news = re.sub(r"(%s)\s+?(%s)" % (letter, noletter), r"\1\2", news)
            if news == s:
                break
        return s.replace("XXXXXXX", " ")

    def remove_chinese_text_wrapping(self, formula: str) -> str:
        """移除中文文本包装"""
        pattern = re.compile(r"\\text\s*{\s*([^}]*?[\u4e00-\u9fff]+[^}]*?)\s*}")
        replaced = pattern.sub(lambda m: m.group(1), formula)
        return replaced.replace('"', "")

    def post_process(self, text: str) -> str:
        """后处理：修复文本并规范化"""
        try:
            from ftfy import fix_text
        except ImportError:
            fix_text = lambda x: x

        if self.is_infer:
            text = self.remove_chinese_text_wrapping(text)
            text = fix_text(text)
            text = self.normalize_infer(text)
        else:
            text = fix_text(text)
        return text

    def token2str(self, token_ids: List[int]) -> List[str]:
        """将 token IDs 转换为字符串"""
        generated_text = []
        tok_id = np.array(token_ids)

        end_idx = np.argwhere(tok_id == self.tokenizer.eos_token_id)
        if len(end_idx) > 0:
            end_idx = int(end_idx[0][0])
            tok_id = tok_id[: end_idx + 1]

        decoded = self.tokenizer.decode(tok_id.tolist(), skip_special_tokens=True)
        generated_text.append(decoded)

        generated_text = [self.post_process(text) for text in generated_text]
        return generated_text

    def decode(self, token_ids: List[int]) -> str:
        """解码 token IDs 为 LaTeX 字符串"""
        results = self.token2str(token_ids)
        return results[0] if results else ""


class PPFormulaNetONNX(ONNXModelBase):
    """
    PP-FormulaNet 公式识别 ONNX 推理类

    模型: PPHGNetV2 encoder + mBART decoder
    输入: (1, 1, H, W) 归一化后的灰度图像 (H/W 由 inference.yml 定义, 384 或 768)
    输出: LaTeX token IDs (单次前向传播)

    注意: ONNX 导出的模型为单次推理，直接输出 token IDs 序列。
    """

    def __init__(
        self,
        model_path: str = None,
        use_gpu: bool = False,
        gpu_id: int = 0,
        tokenizer_dir: str = None,
        max_new_tokens: int = 1024
    ):
        """
        初始化 PP-FormulaNet ONNX 模型

        Args:
            model_path: ONNX模型目录或文件路径。如果为目录，需要包含 inference.onnx 和 inference.yml
            use_gpu: 是否使用GPU
            gpu_id: GPU设备ID
            tokenizer_dir: unimernet_tokenizer 目录路径，默认从 model_path/unimernet_tokenizer 加载
            max_new_tokens: 最大生成的 token 数量
        """
        if model_path is None:
            raise ValueError("model_path is required for PPFormulaNetONNX")

        model_dir = Path(model_path)
        onnx_file = model_dir / "inference.onnx"
        if not onnx_file.exists():
            raise FileNotFoundError(f"ONNX model not found at {onnx_file}")

        super().__init__(str(onnx_file), use_gpu=use_gpu, gpu_id=gpu_id)
        self._model_path = str(model_dir)

        self.tokenizer_dir = tokenizer_dir or str(model_dir / "unimernet_tokenizer")
        if not Path(self.tokenizer_dir).exists():
            raise FileNotFoundError(f"Tokenizer not found at {self.tokenizer_dir}")

        self.postprocess = FormulaPostprocess(self.tokenizer_dir, is_infer=True)
        self.input_size = 384
        self.max_new_tokens = max_new_tokens

        yml_path = model_dir / "inference.yml"
        if yml_path.exists():
            try:
                with open(yml_path, "r", encoding="utf-8") as f:
                    yml = yaml.safe_load(f)
                ops = yml.get("PreProcess", {}).get("transform_ops", [])
                for op in ops:
                    if "UniMERNetImgDecode" in op:
                        size_list = op["UniMERNetImgDecode"].get("input_size", [384, 384])
                        self.input_size = size_list[0]
                        break
                for op in ops:
                    if "UniMERNetLabelEncode" in op:
                        self.max_new_tokens = op["UniMERNetLabelEncode"].get("max_seq_len", max_new_tokens)
                        break
            except Exception:
                pass

    def predict(self, img: np.ndarray) -> Tuple[List[int], float]:
        """
        预测公式 LaTeX

        Args:
            img: 输入图像 BGR格式 (H, W, 3)

        Returns:
            token_ids: LaTeX token IDs
            elapsed_time: 推理耗时（秒）
        """
        import time
        start_time = time.time()

        tensor = preprocess_formula_unimernet(img, input_size=self.input_size)

        input_names = [inp.name for inp in self.session.get_inputs()]
        output_names = [out.name for out in self.session.get_outputs()]

        if len(input_names) == 1:
            outputs = self.session.run(output_names, {input_names[0]: tensor})
            token_ids = outputs[0][0].tolist()
        else:
            token_ids = self._autoregressive_decode(tensor, input_names, output_names)

        elapsed_time = time.time() - start_time

        return token_ids, elapsed_time

    def _autoregressive_decode(
        self,
        image_tensor: np.ndarray,
        input_names: List[str],
        output_names: List[str]
    ) -> List[int]:
        """
        Autoregressive 解码（用于多输入模型）
        每次前向传播生成一个 token

        Args:
            image_tensor: (1, 1, H, W) 预处理后的图像
            input_names: 模型输入名称列表
            output_names: 模型输出名称列表

        Returns:
            token_ids: 生成的 token IDs 列表
        """
        bos_token_id = 0
        eos_token_id = 2
        max_len = self.max_new_tokens

        token_ids = [bos_token_id]

        for step in range(max_len):
            decoder_input = np.array([[token_ids[-1]]], dtype=np.int64)

            try:
                feed_dict = {
                    input_names[0]: image_tensor,
                    input_names[1]: decoder_input
                }
                outputs = self.session.run(output_names, feed_dict)
            except Exception:
                break

            logits = outputs[0]
            next_token_id = int(logits.argmax())

            if next_token_id == eos_token_id:
                break

            token_ids.append(next_token_id)

        return token_ids

    def predict_latex(self, img: np.ndarray) -> Tuple[str, float]:
        """
        预测公式并返回 LaTeX 字符串

        Args:
            img: 输入图像 BGR格式 (H, W, 3)

        Returns:
            latex: LaTeX 公式字符串
            elapsed_time: 推理耗时（秒）
        """
        token_ids, elapsed = self.predict(img)
        latex = self.postprocess.decode(token_ids)
        return latex, elapsed
