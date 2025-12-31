"""
PP-StructureV3 Pipeline

完整的PP-StructureV3文档结构分析流水线，整合布局检测和OCR识别，
提供端到端的文档解析功能。
"""

from typing import List, Dict, Any, Tuple, Optional, Union
from pathlib import Path
import cv2
import numpy as np

from ..pp_onnx.pp_doclayout_onnx import PPDocLayoutONNX
from .pp_ocrv5_pipeline import PPOCRv5Pipeline


class PPStructureV3Pipeline:
    """
    PP-StructureV3 完整文档结构分析流水线

    整合文档布局检测和OCR识别，提供端到端的文档解析功能。
    支持动态加载和卸载模型以节省内存。
    """

    def __init__(
        self,
        layout_model_path: str,
        ocr_det_model_path: str,
        ocr_rec_model_path: str,
        ocr_cls_model_path: Optional[str] = None,
        ocr_rec_char_dict_path: Optional[str] = None,
        use_gpu: bool = False,
        gpu_id: int = 0,
        layout_config: Optional[Dict[str, Any]] = None,
        ocr_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化PP-StructureV3流水线

        Args:
            layout_model_path: 布局检测模型路径
            ocr_det_model_path: OCR检测模型路径
            ocr_rec_model_path: OCR识别模型路径
            ocr_cls_model_path: OCR分类模型路径（可选）
            ocr_rec_char_dict_path: OCR识别模型字符字典路径
            use_gpu: 是否使用GPU
            gpu_id: GPU设备ID
            layout_config: 布局检测模型配置
            ocr_config: OCR模型配置
        """
        # 保存配置
        self.layout_model_path = layout_model_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.layout_config = layout_config or {}

        # 创建OCR流水线实例
        self.ocr_pipeline = PPOCRv5Pipeline(
            det_model_path=ocr_det_model_path,
            rec_model_path=ocr_rec_model_path,
            cls_model_path=ocr_cls_model_path,
            rec_char_dict_path=ocr_rec_char_dict_path,
            use_gpu=use_gpu,
            gpu_id=gpu_id,
            **(ocr_config or {})
        )

        # 模型实例
        self.layout_model = None
        self._loaded = False

    def load(self) -> bool:
        """
        加载所有文档结构分析模型

        Returns:
            bool: 加载是否成功
        """
        try:
            if self._loaded:
                return True

            # 初始化布局检测模型
            self.layout_model = PPDocLayoutONNX(
                model_path=self.layout_model_path,
                use_gpu=self.use_gpu,
                gpu_id=self.gpu_id,
                **self.layout_config
            )

            # 加载OCR流水线
            if not self.ocr_pipeline.load():
                raise RuntimeError("Failed to load OCR pipeline")

            self._loaded = True
            return True
        except Exception as e:
            print(f"Failed to load PP-StructureV3 models: {e}")
            self.unload()  # 清理部分加载的模型
            return False

    def unload(self) -> bool:
        """
        卸载所有文档结构分析模型以释放内存

        Returns:
            bool: 卸载是否成功
        """
        try:
            # 卸载布局模型
            if self.layout_model is not None:
                del self.layout_model
                self.layout_model = None

            # 卸载OCR流水线
            self.ocr_pipeline.unload()

            self._loaded = False
            return True
        except Exception as e:
            print(f"Failed to unload PP-StructureV3 models: {e}")
            return False

    def is_loaded(self) -> bool:
        """
        检查模型是否已加载

        Returns:
            bool: 模型是否已加载
        """
        return self._loaded and self.ocr_pipeline.is_loaded()

    def analyze_structure(
        self,
        image: Union[str, np.ndarray],
        layout_conf_threshold: float = 0.5,
        layout_iou_threshold: float = 0.5,
        ocr_conf_threshold: float = 0.5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行完整的文档结构分析

        Args:
            image: 输入图像路径或numpy数组
            layout_conf_threshold: 布局检测置信度阈值
            layout_iou_threshold: 布局检测IOU阈值
            ocr_conf_threshold: OCR置信度阈值
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self._loaded:
            raise RuntimeError("Models not loaded. Call load() first.")

        # 预处理图像
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Failed to load image from {image}")

        # 步骤1: 布局检测
        layout_regions = self.layout_model.detect(
            image,
            conf_threshold=layout_conf_threshold
        )

        results = {
            'image_shape': image.shape,
            'layout_regions': layout_regions,
            'text_regions': [],
            'table_regions': [],
            'formula_regions': [],
            'figure_regions': []
        }

        # 步骤2: 对每个区域进行相应处理
        for region in layout_regions:
            region_type = region.get('type', '')
            bbox = region.get('bbox', [])

            if not bbox or len(bbox) != 4:
                continue

            x1, y1, x2, y2 = bbox
            cropped = image[y1:y2, x1:x2]

            if region_type in ['text', 'title', 'list']:
                # OCR处理
                ocr_result = self._process_ocr_region(cropped, ocr_conf_threshold)
                if ocr_result:
                    text_region = {
                        'bbox': bbox,
                        'type': region_type,
                        'confidence': region.get('confidence', 0.0),
                        'text': ocr_result.get('text', ''),
                        'text_confidence': ocr_result.get('confidence', 0.0)
                    }
                    results['text_regions'].append(text_region)

            elif region_type == 'table':
                # 表格处理
                table_result = self._process_table_region(cropped)
                if table_result:
                    table_region = {
                        'bbox': bbox,
                        'type': 'table',
                        'confidence': region.get('confidence', 0.0),
                        'table_html': table_result.get('html', ''),
                        'table_data': table_result.get('data', [])
                    }
                    results['table_regions'].append(table_region)

            elif region_type == 'formula':
                # 公式处理
                formula_result = self._process_formula_region(cropped)
                if formula_result:
                    formula_region = {
                        'bbox': bbox,
                        'type': 'formula',
                        'confidence': region.get('confidence', 0.0),
                        'formula_latex': formula_result.get('latex', ''),
                        'formula_text': formula_result.get('text', '')
                    }
                    results['formula_regions'].append(formula_region)

            elif region_type == 'figure':
                # 图片区域
                figure_region = {
                    'bbox': bbox,
                    'type': 'figure',
                    'confidence': region.get('confidence', 0.0)
                }
                results['figure_regions'].append(figure_region)

        return results

    def _process_ocr_region(self, image: np.ndarray, conf_threshold: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        处理OCR区域

        Args:
            image: 裁剪的图像区域
            conf_threshold: 置信度阈值

        Returns:
            Optional[Dict[str, Any]]: OCR结果
        """
        try:
            # 使用OCR流水线进行完整的OCR处理
            ocr_results = self.ocr_pipeline.ocr(image, det=True, rec=True, cls=True)

            if not ocr_results:
                return None

            # 过滤低置信度的结果
            valid_results = [r for r in ocr_results if r.get('text_confidence', 0) >= conf_threshold]

            if not valid_results:
                return None

            # 合并所有文本
            text_lines = [r['text'] for r in valid_results]
            avg_confidence = sum(r['text_confidence'] for r in valid_results) / len(valid_results)

            return {
                'text': ' '.join(text_lines),
                'confidence': avg_confidence
            }

        except Exception as e:
            print(f"OCR processing error: {e}")
            return None

    def _process_table_region(self, image: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        处理表格区域

        Args:
            image: 裁剪的图像区域

        Returns:
            Optional[Dict[str, Any]]: 表格结果
        """
        # TODO: 实现表格识别
        # 目前返回占位符
        return {
            'html': '<table><tr><td>表格识别待实现</td></tr></table>',
            'data': [['表格识别待实现']]
        }

    def _process_formula_region(self, image: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        处理公式区域

        Args:
            image: 裁剪的图像区域

        Returns:
            Optional[Dict[str, Any]]: 公式结果
        """
        # TODO: 实现公式识别
        # 目前返回占位符
        return {
            'latex': 'E = mc^{2}',
            'text': 'E = mc^2'
        }

    def visualize(self, image: np.ndarray, regions: List[Dict[str, Any]]) -> np.ndarray:
        """
        可视化文档结构分析结果

        Args:
            image: 原始图像
            regions: 布局区域列表

        Returns:
            np.ndarray: 可视化后的图像
        """
        # 使用布局模型的可视化
        return self.layout_model.visualize(image, regions)