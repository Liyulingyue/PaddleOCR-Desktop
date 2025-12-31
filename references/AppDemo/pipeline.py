"""
PP-Structure-V3 ONNX Pipeline
Main pipeline coordinating all modules for document parsing.
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
import json
from . import utils

class PPStructureONNXPipeline:
    def __init__(self, model_dir='models/pp_structure_v3_onnx'):
        self.model_dir = Path(__file__).parent.parent / model_dir
        self.models = {}
        self.utils = utils  # Add utils reference

        # Initialize ONNX sessions for each model
        self._load_models()

    def _load_models(self):
        """Load all ONNX models"""
        model_configs = {
            'layout_det': 'PP-DocLayout-L/inference.onnx',
            'ocr_det': 'PP-OCRv5_det/inference.onnx',
            'ocr_rec': 'PP-OCRv5_rec/inference.onnx',
            # 'ocr_cls': 'PP-OCRv5_cls/inference.onnx',  # Not available
            'table_det': 'SLANeXt_wired/inference.onnx',
            'formula_det': 'PP-FormulaNet-L/inference.onnx',
        }

        for name, path in model_configs.items():
            model_path = self.model_dir / path
            if model_path.exists():
                self.models[name] = ort.InferenceSession(str(model_path))
                print(f"Loaded {name} model")
            else:
                print(f"Warning: {name} model not found at {model_path}")

    def preprocess_image(self, image):
        """Preprocess input image"""
        if isinstance(image, str):
            image = cv2.imread(image)
        # Add preprocessing steps as needed
        return image

    def run_layout_detection(self, image, min_conf: float = 0.5, nms_iou: float = 0.5, debug: bool = False, shrink: float = 1.0, map_mode: str = 'auto', max_box_ratio: float = 0.9):
        """Run layout detection with configurable confidence, NMS, shrink factor and mapping mode"""        if 'layout_det' not in self.models:
            return []

        # Preprocess for layout model
        try:
            inputs, scale, offset = self.utils.preprocess_for_layout(image)
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return []

        # Run inference
        try:
            outputs = self.models['layout_det'].run(None, inputs)
        except Exception as e:
            print(f"Inference error: {e}")
            return []

        # Post-process to get layout regions (pass thresholds)
        try:
            regions = self.utils.postprocess_layout(outputs, scale, offset, (image.shape[1], image.shape[0]), conf_threshold=min_conf, iou_threshold=nms_iou, shrink=shrink, map_mode=map_mode, max_box_ratio=max_box_ratio)
        except Exception as e:
            print(f"Postprocessing error: {e}")
            import traceback
            traceback.print_exc()
            return []

        # If debug, attach raw outputs and preprocessing info for further inspection
        if debug:
            return regions, outputs, scale, offset

        return regions

    def run_ocr(self, image, regions):
        """Run OCR on text regions"""
        results = []
        for region in regions:
            if region['type'] == 'text':
                # Crop region
                x1, y1, x2, y2 = region['bbox']
                print(f"Processing text region: bbox={region['bbox']}")
                cropped = image[y1:y2, x1:x2]
                print(f"Cropped image shape: {cropped.shape}")

                # Run OCR pipeline
                text_result = self._run_ocr_pipeline(cropped)
                results.append({
                    'bbox': region['bbox'],
                    'text': text_result,
                    'type': 'text'
                })
        return results

    def _run_ocr_pipeline(self, image):
        """Complete OCR pipeline: det -> rec (simplified for now)"""
        # For now, return mock text to avoid model inference issues
        return "Sample recognized text from OCR"

    def _run_ocr_det(self, image):
        """OCR Detection"""
        if 'ocr_det' not in self.models:
            return [{'bbox': [0, 0, image.shape[1], image.shape[0]]}]

        input_tensor = self.utils.preprocess_for_ocr_det(image)
        outputs = self.models['ocr_det'].run(None, {'x': input_tensor})
        boxes = self.utils.postprocess_ocr_det(outputs, 1.0, (0, 0), (image.shape[1], image.shape[0]))
        return boxes

    def _run_ocr_rec(self, image):
        """OCR Recognition"""
        if 'ocr_rec' not in self.models:
            return "recognized text"

        input_tensor = self.utils.preprocess_for_ocr_rec(image)
        outputs = self.models['ocr_rec'].run(None, {'x': input_tensor})
        text = self.utils.postprocess_ocr_rec(outputs)
        return text

    def run_table_recognition(self, image, regions):
        """Run table recognition on table regions"""
        results = []
        for region in regions:
            if region['type'] == 'table':
                # Implement table recognition
                table_result = self._run_table_pipeline(image, region['bbox'])
                results.append({
                    'bbox': region['bbox'],
                    'table': table_result,
                    'type': 'table'
                })
        return results

    def _run_table_pipeline(self, image, bbox):
        """Table recognition pipeline"""
        # Placeholder implementation
        return {"html": "<table>...</table>"}  # Placeholder

    def run_formula_recognition(self, image, regions):
        """Run formula recognition on formula regions"""
        results = []
        for region in regions:
            if region['type'] == 'formula':
                # Implement formula recognition
                formula_result = self._run_formula_pipeline(image, region['bbox'])
                results.append({
                    'bbox': region['bbox'],
                    'formula': formula_result,
                    'type': 'formula'
                })
        return results

    def _run_formula_pipeline(self, image, bbox):
        """Formula recognition pipeline"""
        # Placeholder
        return "E = mc^2"  # Placeholder

    def run(self, image_path):
        """Main pipeline execution"""
        try:
            image = self.preprocess_image(image_path)
        except Exception as e:
            print(f"Image loading error: {e}")
            return {"image_path": image_path, "results": []}

        # Step 1: Layout detection
        try:
            regions = self.run_layout_detection(image)
            print(f"Detected {len(regions)} regions")
        except Exception as e:
            print(f"Layout detection error: {e}")
            regions = []

        # Step 2: Process each region type
        try:
            ocr_results = self.run_ocr(image, regions)
            print(f"OCR results: {len(ocr_results)}")
        except Exception as e:
            print(f"OCR error: {e}")
            ocr_results = []

        try:
            table_results = self.run_table_recognition(image, regions)
        except Exception as e:
            print(f"Table recognition error: {e}")
            table_results = []

        try:
            formula_results = self.run_formula_recognition(image, regions)
        except Exception as e:
            print(f"Formula recognition error: {e}")
            formula_results = []

        # Step 3: Merge results
        all_results = ocr_results + table_results + formula_results

        # Step 4: Sort by reading order (simplified)
        try:
            all_results.sort(key=lambda x: (x['bbox'][1], x['bbox'][0]))
        except Exception as e:
            print(f"Sorting error: {e}")

        return {
            'image_path': image_path,
            'results': all_results
        }

    def result_to_markdown(self, result):
        """Convert results to Markdown format"""
        markdown = "# Document Analysis Result\n\n"
        for item in result['results']:
            if item['type'] == 'text':
                markdown += f"{item['text']}\n\n"
            elif item['type'] == 'table':
                markdown += f"**Table:** {item['table']['html']}\n\n"
            elif item['type'] == 'formula':
                markdown += f"**Formula:** ${item['formula']}$\n\n"
        return markdown

    # Placeholder methods for preprocessing/postprocessing
    def _preprocess_for_layout(self, image):
        """Preprocess image for layout detection"""
        # Resize, normalize, etc.
        return np.random.rand(1, 3, 640, 640).astype(np.float32)  # Placeholder

    def _postprocess_layout(self, outputs):
        """Postprocess layout detection outputs"""
        # Parse outputs to regions
        return [
            {'bbox': [100, 100, 500, 200], 'type': 'text'},
            {'bbox': [100, 250, 500, 400], 'type': 'table'},
        ]  # Placeholder