"""
PP-StructureV3 Pipeline

完整的PP-StructureV3文档结构分析流水线，整合布局检测和OCR识别，
提供端到端的文档解析功能。
"""

from typing import List, Dict, Any, Tuple, Optional, Union
from pathlib import Path
import cv2
import numpy as np
import base64

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
        layout_model_path: Optional[str] = None,
        ocr_det_model_path: Optional[str] = None,
        ocr_rec_model_path: Optional[str] = None,
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
            layout_model_path: 布局检测模型路径（可选，使用config默认值）
            ocr_det_model_path: OCR检测模型路径（可选，使用config默认值）
            ocr_rec_model_path: OCR识别模型路径（可选，使用config默认值）
            ocr_cls_model_path: OCR分类模型路径（可选，使用config默认值）
            ocr_rec_char_dict_path: OCR识别模型字符字典路径
            use_gpu: 是否使用GPU
            gpu_id: GPU设备ID
            layout_config: 布局检测模型配置
            ocr_config: OCR模型配置
        """
        # 如果没有提供模型路径，使用配置文件中的默认路径
        config_available = True
        if (layout_model_path is None or ocr_det_model_path is None or 
            ocr_rec_model_path is None or ocr_cls_model_path is None):
            try:
                from ...config import get_pipeline_models
                pipeline_models = get_pipeline_models("pp_structure_v3")
                if pipeline_models:
                    layout_model_path = layout_model_path or pipeline_models.get('layout_det')
                    ocr_det_model_path = ocr_det_model_path or pipeline_models.get('ocr_det')
                    ocr_rec_model_path = ocr_rec_model_path or pipeline_models.get('ocr_rec')
                    ocr_cls_model_path = ocr_cls_model_path or pipeline_models.get('doc_cls')
                else:
                    config_available = False
            except ImportError:
                config_available = False
                print("Warning: Could not import config, using None for model paths")
        
        # 验证必需的模型路径
        missing_required = []
        if not layout_model_path:
            missing_required.append("layout_model_path")
        if not ocr_det_model_path:
            missing_required.append("ocr_det_model_path") 
        if not ocr_rec_model_path:
            missing_required.append("ocr_rec_model_path")
            
        if missing_required:
            if config_available:
                raise ValueError(f"Required model paths not found in config: {', '.join(missing_required)}")
            else:
                raise ValueError(f"Required model paths must be provided when config is unavailable: {', '.join(missing_required)}")
        
        self.layout_model_path = layout_model_path
        self.ocr_det_model_path = ocr_det_model_path
        self.ocr_rec_model_path = ocr_rec_model_path
        self.ocr_cls_model_path = ocr_cls_model_path
        self.ocr_rec_char_dict_path = ocr_rec_char_dict_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.layout_config = layout_config
        self.ocr_config = ocr_config
        # 保存配置
        self.layout_model_path = layout_model_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.layout_config = layout_config or {}

        # 创建OCR流水线实例
        # 注意：这里复用了完整的PPOCRv5Pipeline，主要目的是获取其方向检测模型(cls_model)
        # 这种设计基于以下考虑：
        # 1. 效率：避免重复创建和加载方向检测模型，节省内存和初始化时间
        # 2. 一致性：确保PPStructure和OCR使用相同的方向检测逻辑和模型
        # 3. 简化：PPStructureV3Pipeline无需关心方向检测模型的创建细节
        # 
        # 然而，这种耦合并非必需。理论上，可以将方向检测模型从PPOCRv5Pipeline中拆分出来，
        # 作为独立的组件，这样PPStructureV3Pipeline可以更灵活地控制模型生命周期，
        # 例如只在需要时加载方向检测模型，或者使用不同的方向检测实现。
        self.ocr_pipeline = PPOCRv5Pipeline(
            det_model_path=ocr_det_model_path,
            rec_model_path=ocr_rec_model_path,
            cls_model_path=ocr_cls_model_path,
            use_gpu=use_gpu,
            gpu_id=gpu_id
        )

        # 模型实例
        self.layout_model = None
        self._loaded = False

    def load(self) -> tuple[bool, str]:
        """
        加载所有文档结构分析模型

        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            if self._loaded:
                return True, ""

            # 检查模型路径是否存在
            from pathlib import Path
            
            missing_models = []
            if self.layout_model_path and not Path(self.layout_model_path).exists():
                missing_models.append(f"Layout model: {self.layout_model_path}")
            
            # 检查OCR流水线的模型路径
            if hasattr(self.ocr_pipeline, 'det_model_path') and self.ocr_pipeline.det_model_path and not Path(self.ocr_pipeline.det_model_path).exists():
                missing_models.append(f"OCR Detection model: {self.ocr_pipeline.det_model_path}")
            if hasattr(self.ocr_pipeline, 'rec_model_path') and self.ocr_pipeline.rec_model_path and not Path(self.ocr_pipeline.rec_model_path).exists():
                missing_models.append(f"OCR Recognition model: {self.ocr_pipeline.rec_model_path}")
            if hasattr(self.ocr_pipeline, 'cls_model_path') and self.ocr_pipeline.cls_model_path and not Path(self.ocr_pipeline.cls_model_path).exists():
                missing_models.append(f"OCR Classification model: {self.ocr_pipeline.cls_model_path}")
            
            if missing_models:
                error_msg = "模型文件缺失！请前往模型管理页面下载以下模型：\n"
                for missing in missing_models:
                    error_msg += f"  - {missing}\n"
                error_msg += "\n需要下载的模型：PP-DocLayout-L, PP-OCRv5_mobile_det, PP-OCRv5_mobile_rec, PP-LCNet_x1_0_textline_ori"
                print("Error: " + error_msg)
                return False, error_msg

            # 初始化布局检测模型
            self.layout_model = PPDocLayoutONNX(
                model_path=self.layout_model_path,
                use_gpu=self.use_gpu,
                gpu_id=self.gpu_id,
                **self.layout_config
            )

            # 加载OCR流水线
            success, error_msg = self.ocr_pipeline.load()
            if not success:
                raise RuntimeError(f"Failed to load OCR pipeline: {error_msg}")

            self._loaded = True
            return True, ""
        except Exception as e:
            error_msg = f"加载PP-StructureV3模型失败: {e}"
            print(f"Failed to load PP-StructureV3 models: {e}")
            self.unload()  # 清理部分加载的模型
            return False, error_msg

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

    @staticmethod
    def calculate_overlap_ratio(box1: List[float], box2: List[float]) -> float:
        """Calculate overlap ratio as intersection / min(area1, area2)."""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Calculate intersection
        x1_inter = max(x1_1, x1_2)
        y1_inter = max(y1_1, y1_2)
        x2_inter = min(x2_1, x2_2)
        y2_inter = min(y2_1, y2_2)
        
        # Check if there's no intersection
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0
        
        # Calculate areas
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # Calculate overlap ratio: intersection / min(area1, area2)
        min_area = min(area1, area2)
        if min_area == 0:
            return 0.0
            
        return inter_area / min_area

    @staticmethod
    def merge_boxes(box1: List[float], box2: List[float]) -> List[float]:
        """Merge two bounding boxes by taking the union."""
        x1 = min(box1[0], box2[0])
        y1 = min(box1[1], box2[1])
        x2 = max(box1[2], box2[2])
        y2 = max(box1[3], box2[3])
        return [x1, y1, x2, y2]

    def merge_layout_regions(self, layout_regions: List[Dict], overlap_threshold: float = 0.5) -> List[Dict]:
        """
        Merge overlapping layout detection regions with the same label.
        
        Args:
            layout_regions: List of layout regions with bbox and type information
            overlap_threshold: Overlap threshold for merging (intersection / min(area1, area2))
            
        Returns:
            List of merged layout regions
        """
        if not layout_regions:
            return layout_regions
        
        # Sort regions by confidence (highest first)
        sorted_regions = sorted(layout_regions, key=lambda x: x.get('confidence', 0), reverse=True)
        merged_regions = []
        
        for region in sorted_regions:
            current_bbox = region.get('bbox', [])
            current_type = region.get('type', '')
            should_merge = False
            
            # Check against already merged regions with same type
            for i, merged_region in enumerate(merged_regions):
                merged_bbox = merged_region.get('bbox', [])
                merged_type = merged_region.get('type', '')
                
                # Only merge if types are the same
                if current_type == merged_type:
                    overlap_ratio = self.calculate_overlap_ratio(current_bbox, merged_bbox)
                    
                    if overlap_ratio >= overlap_threshold:
                        # Merge the boxes
                        new_bbox = self.merge_boxes(current_bbox, merged_bbox)
                        
                        # Update merged region
                        # Keep the one with higher confidence
                        if region.get('confidence', 0) > merged_region.get('confidence', 0):
                            merged_region['confidence'] = region.get('confidence', 0)
                        
                        # Update bbox
                        merged_region['bbox'] = new_bbox
                        
                        should_merge = True
                        break
            
            # If not merged with any existing region, add as new
            if not should_merge:
                merged_regions.append(region.copy())
        
        return merged_regions

    def analyze_structure(
        self,
        image: Union[str, np.ndarray],
        layout_conf_threshold: float = 0.5,
        layout_iou_threshold: float = 0.5,
        ocr_conf_threshold: float = 0.5,
        unclip_ratio: float = 1.1,
        use_cls: bool = True,
        cls_thresh: float = 0.9,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行完整的文档结构分析

        Args:
            image: 输入图像路径或numpy数组
            layout_conf_threshold: 布局检测置信度阈值
            layout_iou_threshold: 布局检测IOU阈值
            ocr_conf_threshold: OCR置信度阈值
            unclip_ratio: 裁剪区域扩大倍数，默认1.1倍，用于包含更多上下文
            use_cls: 是否启用文档方向检测
            cls_thresh: 方向检测置信度阈值
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self._loaded:
            print("Models not loaded, auto-loading...")
            success, error_msg = self.load()
            if not success:
                raise RuntimeError(f"Failed to auto-load models: {error_msg}")

        # 预处理图像
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Failed to load image from {image}")

        # 步骤0: 文档方向检测（可选）
        # 注意：这里复用了PPOCRv5Pipeline中已创建的方向检测模型(cls_model)
        # 这种设计基于效率考虑，避免重复加载相同的方向检测模型
        # 但实际上，方向检测模型可以从PPOCRv5Pipeline中拆分出来，
        # 作为独立的组件，这样PPStructureV3Pipeline可以更灵活地控制模型生命周期
        angle = 0
        rotation_confidence = 1.0
        if use_cls:
            cls_result = self.ocr_pipeline.cls_model.classify(image)
            if cls_result['confidence'] >= cls_thresh:
                angle = int(cls_result['angle'])
                rotation_confidence = cls_result['confidence']
            else:
                # 置信度低，假设不需要旋转
                angle = 0
                rotation_confidence = 1.0
        else:
            # 跳过分类，假设不需要旋转
            angle = 0
            rotation_confidence = 1.0

        # 步骤1: 根据检测到的角度旋转图像
        if angle == 90:
            rotated_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif angle == 180:
            rotated_image = cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            rotated_image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        else:
            rotated_image = image.copy()

        # # 创建输出目录用于保存裁剪的图像片段
        # import os
        # from datetime import datetime
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # output_dir = f"debug_crops_{timestamp}"
        # os.makedirs(output_dir, exist_ok=True)
        # print(f"Saving cropped regions to: {output_dir}")

        # region_counter = 0

        # 步骤2: 布局检测
        layout_regions = self.layout_model.detect(
            rotated_image,
            conf_threshold=layout_conf_threshold
        )

        # 可选：合并重叠的布局区域（仅当类型相同时）
        merge_layout = kwargs.get('merge_layout', False)
        layout_overlap_threshold = kwargs.get('layout_overlap_threshold', 0.5)
        if merge_layout and layout_regions:
            layout_regions = self.merge_layout_regions(layout_regions, layout_overlap_threshold)

        results = {
            'image_shape': image.shape,
            'rotated_image_shape': rotated_image.shape,
            'rotation': angle,
            'rotation_confidence': rotation_confidence,
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

            # 应用unclip_ratio扩大裁剪区域 (默认1.1倍)
            unclip_ratio = kwargs.get('unclip_ratio', 1.1)
            if unclip_ratio > 1.0:
                # Convert bbox to polygon points (clockwise order)
                box_points = np.array([
                    [x1, y1],  # top-left
                    [x2, y1],  # top-right
                    [x2, y2],  # bottom-right
                    [x1, y2]   # bottom-left
                ], dtype=np.float32)

                # Apply unclip expansion
                expanded_points = self._unclip_polygon(box_points, unclip_ratio)

                # Get bounding box of expanded polygon
                crop_x1 = max(0, int(np.min(expanded_points[:, 0])))
                crop_y1 = max(0, int(np.min(expanded_points[:, 1])))
                crop_x2 = min(rotated_image.shape[1], int(np.max(expanded_points[:, 0])))
                crop_y2 = min(rotated_image.shape[0], int(np.max(expanded_points[:, 1])))

                print(f"Unclip applied: {bbox} -> polygon expansion -> [{crop_x1}, {crop_y1}, {crop_x2}, {crop_y2}] (ratio: {unclip_ratio})")
            else:
                crop_x1, crop_y1, crop_x2, crop_y2 = x1, y1, x2, y2

            cropped = rotated_image[crop_y1:crop_y2, crop_x1:crop_x2]

            # # 保存裁剪的图像片段用于调试
            # region_counter += 1
            # crop_filename = f"{output_dir}/region_{region_counter:03d}_{region_type}_orig_{x1}_{y1}_{x2}_{y2}_crop_{crop_x1}_{crop_y1}_{crop_x2}_{crop_y2}.png"
            # cv2.imwrite(crop_filename, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
            # print(f"Saved crop: {crop_filename} (size: {cropped.shape[1]}x{cropped.shape[0]})")

            if region_type in ['text', 'paragraph_title', 'figure_title', 'table_title', 'doc_title', 'chart_title', 'list']:
                # OCR处理
                ocr_result = self._process_ocr_region(cropped, ocr_conf_threshold, **kwargs)
                if ocr_result:
                    text_region = {
                        'bbox': bbox,
                        'type': region_type,  # 保持原始类型
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

            elif region_type == 'figure' or region_type == 'image':
                # 图片区域
                figure_region = {
                    'bbox': bbox,
                    'type': 'figure',  # 统一为figure类型
                    'confidence': region.get('confidence', 0.0)
                }
                results['figure_regions'].append(figure_region)

        # print(f"Analysis complete. Saved {region_counter} cropped regions to {output_dir}")
        # results['debug_info'] = {
        #     'crop_output_dir': output_dir,
        #     'total_crops_saved': region_counter
        # }

        return results

    def _process_ocr_region(self, image: np.ndarray, conf_threshold: float = 0.5, **kwargs) -> Optional[Dict[str, Any]]:
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
            # 文档结构分析优化：不开启方向检测，默认开启形态学膨胀
            ocr_results = self.ocr_pipeline.ocr(
                image, 
                conf_threshold=conf_threshold,
                use_cls=False,      # 文档分析默认不开启方向检测
                cls_thresh=0.9,     # 方向检测阈值（不开启时不生效）
                use_close=True,     # 默认开启形态学膨胀
                merge_overlaps=kwargs.get('merge_overlaps', False),
                overlap_threshold=kwargs.get('overlap_threshold', 0.9)
            )

            if not ocr_results:
                return None

            # 过滤低置信度的结果
            valid_results = [r for r in ocr_results if r.get('confidence', 0) >= conf_threshold]

            if not valid_results:
                return None

            # 合并所有文本
            text_lines = [r['text'] for r in valid_results]
            avg_confidence = sum(r['confidence'] for r in valid_results) / len(valid_results)

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

    def result_to_markdown(self, image: np.ndarray, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        将文档分析结果转换为接近源文档结构的 Markdown 文档。
        返回markdown内容和图片文件列表。

        Args:
            image: 原始图像（numpy array）
            analysis_result: analyze_structure返回的完整结果字典

        Returns:
            Dict[str, Any]: 包含 'markdown' 和 'images' 键的字典
        """
        # 根据旋转信息处理图像
        rotation = analysis_result.get('rotation', 0)
        if rotation == 90:
            working_image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rotation == 180:
            working_image = cv2.rotate(image, cv2.ROTATE_180)
        elif rotation == 270:
            working_image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        else:
            working_image = image.copy()
        
        print(f"result_to_markdown called with image shape: {image.shape}")
        if rotation != 0:
            print(f"Using rotated image with shape: {working_image.shape} (rotation: {rotation}°)")
        print(f"analysis_result keys: {list(analysis_result.keys())}")

        markdown_parts = []
        images = []  # 存储图片数据

        # 获取所有区域，按阅读顺序排序
        all_regions = []
        all_regions.extend(analysis_result.get('text_regions', []))
        all_regions.extend(analysis_result.get('table_regions', []))
        all_regions.extend(analysis_result.get('formula_regions', []))
        all_regions.extend(analysis_result.get('figure_regions', []))

        print(f"Total regions to process: {len(all_regions)}")
        for i, region in enumerate(all_regions[:3]):  # 只打印前3个
            print(f"Region {i}: type={region.get('type')}, bbox={region.get('bbox')}")

        # Sort by reading order: top->down, left->right
        try:
            sorted_regions = sorted(all_regions, key=lambda r: (min(r.get('bbox', [0,0,0,0])[1], r.get('bbox', [0,0,0,0])[3]), min(r.get('bbox', [0,0,0,0])[0], r.get('bbox', [0,0,0,0])[2])))
        except Exception:
            sorted_regions = all_regions

        # Process regions sequentially - 直接输出内容，不添加元数据
        for region in sorted_regions:
            rtype = region.get('type', 'unknown')

            if rtype in ['text', 'paragraph_title', 'figure_title', 'table_title', 'doc_title', 'chart_title', 'list']:
                # 直接输出识别的文本内容
                text = region.get('text', '').strip()
                if text:
                    # 根据类型添加适当的格式
                    if rtype == 'doc_title':
                        # 文档标题 - 一级标题
                        markdown_parts.append(f"# {text}\n\n")
                    elif rtype in ['paragraph_title', 'figure_title', 'table_title', 'chart_title']:
                        # 段落标题、图表标题等 - 二级标题
                        markdown_parts.append(f"## {text}\n\n")
                    elif rtype == 'list':
                        # 列表项
                        markdown_parts.append(f"- {text}\n")
                    else:
                        # 普通文本
                        markdown_parts.append(f"{text}\n\n")

            elif rtype == 'table':
                # 转换为markdown表格
                table_data = region.get('table_data', [])
                if table_data and isinstance(table_data, list) and len(table_data) > 0:
                    try:
                        # 确定最大列数
                        max_cols = max((len(row) for row in table_data if isinstance(row, list)), default=0)
                        if max_cols > 0:
                            # 生成表头（如果第一行看起来像表头）
                            headers = []
                            data_rows = []
                            if len(table_data) > 0 and isinstance(table_data[0], list):
                                headers = [str(c) for c in table_data[0]]
                                data_rows = table_data[1:]
                            else:
                                headers = [f"Col{i+1}" for i in range(max_cols)]
                                data_rows = table_data

                            # 确保表头有足够的列
                            if len(headers) < max_cols:
                                headers += [''] * (max_cols - len(headers))

                            # 生成markdown表格
                            markdown_parts.append('| ' + ' | '.join(headers) + ' |\n')
                            markdown_parts.append('| ' + ' | '.join(['---'] * max_cols) + ' |\n')

                            # 生成数据行
                            for row in data_rows:
                                if isinstance(row, list):
                                    row_cells = [str(c) for c in row]
                                    # 填充缺失的列
                                    if len(row_cells) < max_cols:
                                        row_cells += [''] * (max_cols - len(row_cells))
                                    markdown_parts.append('| ' + ' | '.join(row_cells) + ' |\n')

                            markdown_parts.append('\n')
                        else:
                            # 回退到HTML
                            html = region.get('table_html', '')
                            if html:
                                markdown_parts.append(f"{html}\n\n")
                            else:
                                markdown_parts.append("*Table content not available*\n\n")
                    except Exception as e:
                        markdown_parts.append(f"*Table formatting error*\n\n")
                else:
                    # 回退到HTML
                    html = region.get('table_html', '')
                    if html:
                        markdown_parts.append(f"{html}\n\n")
                    else:
                        markdown_parts.append("*No table content*\n\n")

            elif rtype == 'formula':
                # 输出LaTeX公式
                latex = region.get('formula_latex', '').strip()
                if latex:
                    markdown_parts.append(f"$${latex}$$\n\n")
                else:
                    text_formula = region.get('formula_text', '').strip()
                    if text_formula:
                        markdown_parts.append(f"`{text_formula}`\n\n")
                    else:
                        markdown_parts.append("*Formula not available*\n\n")

            elif rtype == 'figure' or rtype == 'image':
                # 嵌入裁剪的图片
                try:
                    bbox = region.get('bbox', [])
                    if len(bbox) >= 4:
                        x1, y1, x2, y2 = map(int, bbox[:4])
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(working_image.shape[1], x2), min(working_image.shape[0], y2)
                        if x2 > x1 and y2 > y1:
                            crop = working_image[y1:y2, x1:x2]
                            s, enc = cv2.imencode('.png', cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
                            if s:
                                # 生成唯一的图片文件名
                                image_filename = f"figure_{len(images) + 1}.png"
                                image_data = enc.tobytes()
                                
                                # 将图片数据转换为base64编码的字符串，以便JSON序列化
                                base64_data = base64.b64encode(image_data).decode('utf-8')
                                
                                # 存储图片数据
                                images.append({
                                    'filename': image_filename,
                                    'data': base64_data
                                })
                                
                                # 在markdown中引用图片
                                markdown_parts.append(f"![Figure](images/{image_filename})\n\n")
                                print(f"Added figure to markdown: {image_filename}, bbox={bbox}, image size={crop.shape}")
                            else:
                                markdown_parts.append("*Image encoding failed*\n\n")
                        else:
                            markdown_parts.append("*Invalid image region*\n\n")
                    else:
                        markdown_parts.append("*No image data*\n\n")
                except Exception as e:
                    print(f"Error processing figure: {e}")
                    markdown_parts.append(f"*Image processing error: {e}*\n\n")

        return {
            'markdown': ''.join(markdown_parts),
            'images': images
        }

    def _unclip_polygon(self, box_points: np.ndarray, unclip_ratio: float) -> np.ndarray:
        """
        Expand polygon using similar approach to PaddleOCR's unclip

        Args:
            box_points: Polygon points (Nx2 array)
            unclip_ratio: Expansion ratio

        Returns:
            Expanded polygon points
        """
        try:
            from shapely.geometry import Polygon
        except ImportError:
            # Fallback to simple bbox expansion if shapely not available
            print("Warning: shapely not available, using simple bbox expansion")
            x_coords = box_points[:, 0]
            y_coords = box_points[:, 1]
            x1, x2 = np.min(x_coords), np.max(x_coords)
            y1, y2 = np.min(y_coords), np.max(y_coords)

            # Simple expansion
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            width = x2 - x1
            height = y2 - y1

            new_width = width * unclip_ratio
            new_height = height * unclip_ratio

            new_x1 = center_x - new_width / 2
            new_y1 = center_y - new_height / 2
            new_x2 = center_x + new_width / 2
            new_y2 = center_y + new_height / 2

            return np.array([
                [new_x1, new_y1],
                [new_x2, new_y1],
                [new_x2, new_y2],
                [new_x1, new_y2]
            ], dtype=np.float32)

        # Use shapely for proper polygon expansion (like PaddleOCR)
        poly = Polygon(box_points)
        if poly.is_empty or not poly.is_valid:
            return box_points

        # Calculate expansion distance based on area and perimeter
        distance = poly.area * unclip_ratio / poly.length

        # Expand the polygon
        expanded = poly.buffer(distance)
        if expanded.is_empty:
            return box_points

        # Get the exterior coordinates
        expanded_coords = list(expanded.exterior.coords)
        return np.array(expanded_coords[:-1], dtype=np.float32)  # Remove closing point