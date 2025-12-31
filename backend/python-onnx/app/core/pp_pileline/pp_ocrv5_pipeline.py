"""
PP-OCRv5 Pipeline

完整的PP-OCRv5 OCR流水线，整合检测、分类和识别模型，
提供端到端的OCR功能。
"""

from typing import List, Dict, Any, Tuple, Optional, Union
from pathlib import Path
import cv2
import numpy as np

from ..pp_onnx.pp_ocrv5det_onnx import PPOCRv5DetONNX
from ..pp_onnx.pp_ocrv5cls_onnx import PPOCRv5ClsONNX
from ..pp_onnx.pp_ocrv5rec_onnx import PPOCRv5RecONNX


class PPOCRv5Pipeline:
    """
    PP-OCRv5 完整OCR流水线

    整合文本检测、方向分类和文本识别，提供端到端的OCR功能。
    支持动态加载和卸载模型以节省内存。
    """

    def __init__(
        self,
        det_model_path: str,
        rec_model_path: str,
        cls_model_path: Optional[str] = None,
        rec_char_dict_path: Optional[str] = None,
        use_gpu: bool = False,
        gpu_id: int = 0,
        det_config: Optional[Dict[str, Any]] = None,
        cls_config: Optional[Dict[str, Any]] = None,
        rec_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化PP-OCRv5流水线

        Args:
            det_model_path: 检测模型路径
            rec_model_path: 识别模型路径
            cls_model_path: 分类模型路径（可选，用于文本方向检测）
            rec_char_dict_path: 识别模型字符字典路径
            use_gpu: 是否使用GPU
            gpu_id: GPU设备ID
            det_config: 检测模型配置
            cls_config: 分类模型配置
            rec_config: 识别模型配置
        """
        # 保存配置，不立即创建模型
        self.det_model_path = det_model_path
        self.rec_model_path = rec_model_path
        self.cls_model_path = cls_model_path
        self.rec_char_dict_path = rec_char_dict_path
        self.use_gpu = use_gpu
        self.gpu_id = gpu_id
        self.det_config = det_config or {}
        self.cls_config = cls_config or {}
        self.rec_config = rec_config or {}
        if rec_char_dict_path:
            self.rec_config['rec_char_dict_path'] = rec_char_dict_path

        # 模型实例（延迟加载）
        self.det_model = None
        self.rec_model = None
        self.cls_model = None
        self._loaded = False

    def load(self) -> bool:
        """
        加载所有OCR模型

        Returns:
            bool: 加载是否成功
        """
        try:
            if self._loaded:
                return True

            # 初始化检测模型
            self.det_model = PPOCRv5DetONNX(
                model_path=self.det_model_path,
                use_gpu=self.use_gpu,
                gpu_id=self.gpu_id,
                **self.det_config
            )

            # 初始化识别模型
            self.rec_model = PPOCRv5RecONNX(
                model_path=self.rec_model_path,
                use_gpu=self.use_gpu,
                gpu_id=self.gpu_id,
                **self.rec_config
            )

            # 初始化分类模型（可选）
            if self.cls_model_path:
                self.cls_model = PPOCRv5ClsONNX(
                    model_path=self.cls_model_path,
                    use_gpu=self.use_gpu,
                    gpu_id=self.gpu_id,
                    **self.cls_config
                )

            self._loaded = True
            return True
        except Exception as e:
            print(f"Failed to load OCR models: {e}")
            self.unload()  # 清理部分加载的模型
            return False

    def unload(self) -> bool:
        """
        卸载所有OCR模型以释放内存

        Returns:
            bool: 卸载是否成功
        """
        try:
            # 删除模型实例
            if self.det_model is not None:
                del self.det_model
                self.det_model = None

            if self.rec_model is not None:
                del self.rec_model
                self.rec_model = None

            if self.cls_model is not None:
                del self.cls_model
                self.cls_model = None

            self._loaded = False
            return True
        except Exception as e:
            print(f"Failed to unload OCR models: {e}")
            return False

    def is_loaded(self) -> bool:
        """
        检查模型是否已加载

        Returns:
            bool: 模型是否已加载
        """
        return self._loaded

    def ocr(
        self,
        image: Union[str, np.ndarray],
        det: bool = True,
        rec: bool = True,
        cls: bool = True,
        max_batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        执行完整的OCR流程

        Args:
            image: 输入图像（文件路径或numpy数组）
            det: 是否执行文本检测
            rec: 是否执行文本识别
            cls: 是否执行文本方向分类
            max_batch_size: 最大批处理大小

        Returns:
            OCR结果列表，每个元素包含：
            {
                'box': [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],  # 文本框坐标
                'text': '识别的文本内容',
                'text_confidence': 0.95,  # 文本识别置信度
                'rotation': '0' 或 '180',  # 旋转角度
                'rotation_confidence': 0.99  # 旋转分类置信度
            }
        """
        # 自动加载模型（如果尚未加载）
        if not self._loaded:
            if not self.load():
                raise RuntimeError("Failed to load OCR models")

        # 加载图像
        if isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                raise ValueError(f"无法加载图像: {image}")
        else:
            img = image.copy()

        results = []

        # 步骤1: 文本检测
        if det:
            dt_boxes = self.det_model.detect(img)
            if dt_boxes is None or len(dt_boxes) == 0:
                return results  # 没有检测到文本

            # 排序文本框（从上到下，从左到右）
            dt_boxes = self._sort_boxes(dt_boxes)
        else:
            # 如果不进行检测，整个图像作为单个文本区域
            h, w = img.shape[:2]
            dt_boxes = [np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)]

        # 步骤2: 裁剪文本区域
        cropped_images = []
        valid_boxes = []

        for box in dt_boxes:
            try:
                # 处理不同格式的文本框
                if box.shape == (4, 2):  # 四边形
                    cropped = self._get_rotate_crop_image(img, box)
                elif box.shape == (8,):  # 展平的四边形
                    points = box.reshape(4, 2)
                    cropped = self._get_rotate_crop_image(img, points)
                else:
                    continue  # 跳过不支持的格式

                cropped_images.append(cropped)
                valid_boxes.append(box)
            except Exception:
                continue  # 跳过裁剪失败的区域

        if not cropped_images:
            return results

        # 步骤3: 文本方向分类
        cls_results = []
        if cls and self.cls_model is not None:
            try:
                rotated_images, cls_res = self.cls_model.classify(cropped_images)
                cropped_images = rotated_images  # 使用旋转后的图像
                cls_results = cls_res
            except Exception:
                # 分类失败，使用默认值
                cls_results = [('0', 1.0)] * len(cropped_images)
        else:
            # 不进行分类，使用默认值
            cls_results = [('0', 1.0)] * len(cropped_images)

        # 步骤4: 文本识别
        rec_results = []
        if rec:
            try:
                # 分批处理以避免内存问题
                for i in range(0, len(cropped_images), max_batch_size):
                    batch_images = cropped_images[i:i + max_batch_size]
                    batch_rec_results = self.rec_model.recognize(batch_images)
                    rec_results.extend(batch_rec_results)
            except Exception:
                # 识别失败，使用空结果
                rec_results = [('', 0.0)] * len(cropped_images)
        else:
            # 不进行识别，使用空结果
            rec_results = [('', 0.0)] * len(cropped_images)

        # 步骤5: 组合结果
        for box, (text, text_conf), (rotation, rot_conf) in zip(valid_boxes, rec_results, cls_results):
            result = {
                'box': box.tolist() if hasattr(box, 'tolist') else box,
                'text': text,
                'text_confidence': float(text_conf),
                'rotation': rotation,
                'rotation_confidence': float(rot_conf)
            }
            results.append(result)

        return results

    def _sort_boxes(self, dt_boxes: np.ndarray) -> List[np.ndarray]:
        """
        排序文本框：从上到下，从左到右
        """
        def sort_key(box):
            if box.shape == (4, 2):
                return (box[0][1], box[0][0])  # (y, x) of top-left point
            elif box.shape == (8,):
                points = box.reshape(4, 2)
                return (points[0][1], points[0][0])
            else:
                return (0, 0)

        sorted_boxes = sorted(dt_boxes, key=sort_key)
        boxes = list(sorted_boxes)

        # 进一步排序：同一行的框按x坐标排序
        num_boxes = len(boxes)
        for i in range(num_boxes - 1):
            for j in range(i, -1, -1):
                box1_y = sort_key(boxes[j + 1])[0]
                box2_y = sort_key(boxes[j])[0]
                box1_x = sort_key(boxes[j + 1])[1]
                box2_x = sort_key(boxes[j])[1]

                if abs(box1_y - box2_y) < 10 and box1_x < box2_x:
                    boxes[j], boxes[j + 1] = boxes[j + 1], boxes[j]
                else:
                    break

        return boxes

    def _get_rotate_crop_image(self, img: np.ndarray, points: np.ndarray) -> np.ndarray:
        """
        透视变换裁剪旋转矩形区域
        """
        assert len(points) == 4, "shape of points must be 4*2"

        # 找到最小外接矩形
        rect = cv2.minAreaRect(points)
        box = cv2.boxPoints(rect)
        box = np.intp(box)

        # 计算目标尺寸
        width = int(rect[1][0])
        height = int(rect[1][1])

        # 透视变换
        src_pts = box.astype("float32")
        dst_pts = np.array([[0, height-1],
                           [0, 0],
                           [width-1, 0],
                           [width-1, height-1]], dtype="float32")

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        dst_img = cv2.warpPerspective(
            img,
            M,
            (width, height),
            borderMode=cv2.BORDER_REPLICATE,
            flags=cv2.INTER_CUBIC
        )

        # 如果高度明显大于宽度，进行旋转
        dst_img_height, dst_img_width = dst_img.shape[0:2]
        if dst_img_height * 1.0 / dst_img_width >= 1.5:
            dst_img = np.rot90(dst_img)

        return dst_img

    def __repr__(self) -> str:
        """字符串表示"""
        models_info = []
        if hasattr(self, 'det_model'):
            models_info.append("DET")
        if hasattr(self, 'cls_model') and self.cls_model:
            models_info.append("CLS")
        if hasattr(self, 'rec_model'):
            models_info.append("REC")

        return f"PPOCRv5Pipeline(models={'+'.join(models_info)}, gpu={self.use_gpu})"


if __name__ == "__main__":
    print("PPOCRv5Pipeline ready")
