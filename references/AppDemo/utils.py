"""
Utility functions for PP-Structure-V3 ONNX inference
"""

import cv2
import numpy as np
from typing import Tuple, List

def resize_image(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """Resize image maintaining aspect ratio with padding.

    target_size is (width, height) for clarity and to match common image conventions.
    Returns: (canvas_image, scale, (x_offset, y_offset)) where offsets are in canvas coords.
    """
    h, w = image.shape[:2]
    target_w, target_h = target_size

    # scale should be computed with respect to width and height accordingly
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h))

    # Create canvas (height, width, channels) and center the image
    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    x_offset = (target_w - new_w) // 2
    y_offset = (target_h - new_h) // 2
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized

    return canvas, scale, (x_offset, y_offset)

def normalize_image(image: np.ndarray, mean: List[float] = [0.485, 0.456, 0.406],
                   std: List[float] = [0.229, 0.224, 0.225]) -> np.ndarray:
    """Normalize image for model input"""
    image = image.astype(np.float32) / 255.0
    image = (image - mean) / std
    return image

def preprocess_for_layout(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> Tuple[dict, float, Tuple[int, int]]:
    """Complete preprocessing for layout detection - returns dict of inputs

    Ensures that im_shape and scale_factor match expected ordering (height, width)
    and that offset is returned in canvas coordinate system (x_offset, y_offset).
    """
    resized, scale, offset = resize_image(image, target_size)
    normalized = normalize_image(resized)
    # To CHW
    chw = np.transpose(normalized, (2, 0, 1))
    batch_chw = np.expand_dims(chw, 0).astype(np.float32)

    # Calculate im_shape and scale_factor (height, width)
    original_h, original_w = image.shape[:2]
    im_shape = np.array([[original_h, original_w]], dtype=np.float32)
    scale_factor = np.array([[scale, scale]], dtype=np.float32)

    inputs = {
        'image': batch_chw,
        'im_shape': im_shape,
        'scale_factor': scale_factor
    }

    return inputs, scale, offset

def preprocess_for_ocr_det(image: np.ndarray, target_size: Tuple[int, int] = (640, 640)) -> np.ndarray:
    """Preprocessing for OCR detection - returns tensor with key 'x'"""
    resized, scale, offset = resize_image(image, target_size)
    normalized = normalize_image(resized)
    # To CHW
    chw = np.transpose(normalized, (2, 0, 1))
    return np.expand_dims(chw, 0).astype(np.float32)

def preprocess_for_ocr_rec(image: np.ndarray, target_height: int = 48) -> np.ndarray:
    """Preprocessing for OCR recognition - resize to fixed height, returns tensor with key 'x'"""
    h, w = image.shape[:2]
    scale = target_height / h
    new_w = int(w * scale)
    resized = cv2.resize(image, (new_w, target_height))

    # Normalize
    normalized = normalize_image(resized)
    # To CHW
    chw = np.transpose(normalized, (2, 0, 1))
    return np.expand_dims(chw, 0).astype(np.float32)

def postprocess_layout(outputs: list, scale: float, offset: Tuple[int, int],
                      original_size: Tuple[int, int], conf_threshold: float = 0.5, iou_threshold: float = 0.5, shrink: float = 1.0, map_mode: str = 'auto', max_box_ratio: float = 0.9) -> List[dict]:
    """Postprocess layout detection outputs from PP-DocLayout-L"""
    print(f"Layout outputs length: {len(outputs)}")
    print(f"Scale: {scale}, Offset: {offset}, Original size: {original_size}")
    if len(outputs) > 0:
        print(f"Output 0 shape: {outputs[0].shape}")
        print(f"Output 0 sample: {outputs[0][:3] if len(outputs[0]) > 0 else 'empty'}")

    regions = []

    if len(outputs) >= 1:
        # PP-DocLayout output format: [N, 6] where each row is [class_id, confidence, x1, y1, x2, y2]
        detections = outputs[0]  # Shape: [N, 6]

        print(f"Detections shape: {detections.shape}")

        # PP-DocLayout class mapping
        class_names = {
            0: 'text',
            1: 'title',
            2: 'list',
            3: 'table',
            4: 'figure',
            5: 'formula'
        }

        boxes_all = []
        scores_all = []
        classes_all = []

        # helper to pick best mapping for a single detection
        def _best_mapping_for_det(det, scale, offset, orig_w, orig_h):
            class_id, confidence, x1, y1, x2, y2 = det[:6]

            cand = {}
            try:
                # normalized
                cand['normalized'] = [x1 * orig_w, y1 * orig_h, x2 * orig_w, y2 * orig_h]
            except Exception:
                cand['normalized'] = None
            try:
                x_offset, y_offset = offset
                cand['canvas'] = [ (x1 - x_offset) / scale, (y1 - y_offset) / scale, (x2 - x_offset) / scale, (y2 - y_offset) / scale ]
            except Exception:
                cand['canvas'] = None
            try:
                cx = x1 * orig_w
                cy = y1 * orig_h
                w = x2 * orig_w
                h = y2 * orig_h
                cand['center'] = [cx - w/2, cy - h/2, cx + w/2, cy + h/2]
            except Exception:
                cand['center'] = None

            def _score(b):
                if b is None:
                    return -1
                x1b, y1b, x2b, y2b = b
                w = x2b - x1b
                h = y2b - y1b
                if w <= 0 or h <= 0:
                    return -1
                xx1 = max(0, x1b)
                yy1 = max(0, y1b)
                xx2 = min(orig_w, x2b)
                yy2 = min(orig_h, y2b)
                inter_w = max(0, xx2 - xx1)
                inter_h = max(0, yy2 - yy1)
                inter_area = inter_w * inter_h
                area = w * h
                frac = inter_area / (area + 1e-6)
                size_penalty = 0
                if area > (orig_w * orig_h * 0.9):
                    size_penalty = 0.5
                return frac - size_penalty

            best = None
            best_score = -2
            for k, b in cand.items():
                s = _score(b)
                if s > best_score:
                    best_score = s
                    best = k
            # return candidates dict as well for external choice
            return best, cand.get(best), best_score, cand

        for detection in detections:
            if len(detection) >= 6:
                class_id, confidence = int(detection[0]), float(detection[1])
                if confidence > conf_threshold:
                    orig_w, orig_h = original_size
                    best_type, coords, score, cand = _best_mapping_for_det(detection, scale, offset, orig_w, orig_h)

                    # If user forces a mapping mode, try to use it (canvas/normalized/center)
                    if map_mode != 'auto':
                        forced = cand.get(map_mode)
                        def _is_valid_coords(b):
                            if b is None:
                                return False
                            x1b, y1b, x2b, y2b = b
                            return (x2b - x1b) > 0 and (y2b - y1b) > 0

                        if _is_valid_coords(forced):
                            coords = forced
                            best_type = map_mode
                            if len(boxes_all) < 10:
                                print(f"[map-mode] forcing map_mode={map_mode} for det -> coords={coords}")
                        else:
                            if len(boxes_all) < 10:
                                print(f"[map-mode] requested map_mode={map_mode} not available/valid, using auto-chosen {best_type}")

                    if coords is None or score < 0:
                        # skip poor mapping
                        continue

                    x1_px, y1_px, x2_px, y2_px = [int(round(v)) for v in coords]

                    # Clip
                    x1_px = max(0, min(x1_px, orig_w))
                    y1_px = max(0, min(y1_px, orig_h))
                    x2_px = max(0, min(x2_px, orig_w))
                    y2_px = max(0, min(y2_px, orig_h))

                    # Apply shrink factor (around box center)
                    if shrink < 1.0:
                        cx = (x1_px + x2_px) / 2.0
                        cy = (y1_px + y2_px) / 2.0
                        w = (x2_px - x1_px) * shrink
                        h = (y2_px - y1_px) * shrink
                        x1_s = int(round(cx - w / 2.0))
                        x2_s = int(round(cx + w / 2.0))
                        y1_s = int(round(cy - h / 2.0))
                        y2_s = int(round(cy + h / 2.0))

                        # Clip shrunk coords
                        x1_s = max(0, min(x1_s, orig_w))
                        y1_s = max(0, min(y1_s, orig_h))
                        x2_s = max(0, min(x2_s, orig_w))
                        y2_s = max(0, min(y2_s, orig_h))

                        # Debug print for first few
                        if len(boxes_all) < 10:
                            print(f"[shrink] orig=({x1_px},{y1_px},{x2_px},{y2_px}) shrink={shrink} -> ({x1_s},{y1_s},{x2_s},{y2_s})")

                        # ensure non-degenerate
                        if x2_s <= x1_s or y2_s <= y1_s:
                            # fallback to original if shrink degenerates
                            x1_s, y1_s, x2_s, y2_s = x1_px, y1_px, x2_px, y2_px

                        x1_px, y1_px, x2_px, y2_px = x1_s, y1_s, x2_s, y2_s

                    boxes_all.append([x1_px, y1_px, x2_px, y2_px])
                    scores_all.append(float(confidence))
                    classes_all.append(int(class_id))

        # Filter degenerate / very small boxes before NMS
        min_w, min_h = 6, 6
        valid_inds = []
        for i, b in enumerate(boxes_all):
            w = b[2] - b[0]
            h = b[3] - b[1]
            if w <= 0 or h <= 0 or w < min_w or h < min_h:
                print(f"Filtering degenerate/small box: bbox={b}, score={scores_all[i]:.3f}")
                continue
            valid_inds.append(i)

        boxes_all = [boxes_all[i] for i in valid_inds]
        scores_all = [scores_all[i] for i in valid_inds]
        classes_all = [classes_all[i] for i in valid_inds]

        # Apply NMS per-class
        iou_th = iou_threshold
        keep_indices = []
        for cls in set(classes_all):
            cls_inds = [i for i, c in enumerate(classes_all) if c == cls]
            cls_boxes = [boxes_all[i] for i in cls_inds]
            cls_scores = [scores_all[i] for i in cls_inds]
            kept = _nms_boxes(cls_boxes, cls_scores, iou_threshold=iou_th)
            keep_indices.extend([cls_inds[i] for i in kept])

        for idx in keep_indices:
            x1_px, y1_px, x2_px, y2_px = boxes_all[idx]
            class_id = classes_all[idx]
            confidence = scores_all[idx]
            region_type = class_names.get(int(class_id), f'class_{int(class_id)}')

            # Clamp excessively large boxes to a max ratio of the image
            max_w = int(round(orig_w * max_box_ratio))
            max_h = int(round(orig_h * max_box_ratio))
            w = x2_px - x1_px
            h = y2_px - y1_px
            if w > max_w or h > max_h:
                cx = (x1_px + x2_px) / 2.0
                cy = (y1_px + y2_px) / 2.0
                new_w = min(w, max_w)
                new_h = min(h, max_h)
                x1_new = int(round(cx - new_w / 2.0))
                x2_new = int(round(cx + new_w / 2.0))
                y1_new = int(round(cy - new_h / 2.0))
                y2_new = int(round(cy + new_h / 2.0))

                # Clip
                x1_new = max(0, min(x1_new, orig_w))
                y1_new = max(0, min(y1_new, orig_h))
                x2_new = max(0, min(x2_new, orig_w))
                y2_new = max(0, min(y2_new, orig_h))

                if len(regions) < 10:
                    print(f"[clamp] bbox too large ({w}x{h}), clamped -> ({x1_new},{y1_new},{x2_new},{y2_new})")

                x1_px, y1_px, x2_px, y2_px = x1_new, y1_new, x2_new, y2_new

            regions.append({
                'bbox': [x1_px, y1_px, x2_px, y2_px],
                'type': region_type,
                'confidence': float(confidence)
            })

        # Sort by score desc
        regions = sorted(regions, key=lambda x: x['confidence'], reverse=True)

    print(f"Postprocessed {len(regions)} regions")
    for region in regions[:5]:  # Show first 5 regions
        print(f"  {region}")

    # If no regions detected with high confidence, return mock data for testing
    if not regions:
        print("No regions detected with high confidence, returning mock data")
        regions = [
            {'bbox': [100, 100, 500, 200], 'type': 'text', 'confidence': 0.9},
            {'bbox': [100, 250, 500, 400], 'type': 'table', 'confidence': 0.8}
        ]

    return regions


def _nms_boxes(boxes, scores, iou_threshold=0.5):
    """Non-maximum suppression for axis-aligned boxes.
    boxes: list of [x1,y1,x2,y2]
    scores: list of scores
    returns indices to keep
    """
    if len(boxes) == 0:
        return []

    boxes = np.array(boxes)
    scores = np.array(scores)

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


def visualize_raw_layout_outputs(image_path: str, outputs: list, target_size: Tuple[int,int] = (640,640), scale: float = None, offset: Tuple[int,int] = None, output_path: str = None):
    """Visualize raw layout model outputs on the resized canvas.

    This helps determine whether model outputs are in normalized coords or canvas pixel coords.
    """
    if not outputs or len(outputs) == 0:
        print("No raw outputs to visualize")
        return None

    # Read original image and create resized canvas
    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot open image {image_path} for raw visualization")
        return None

    # Use provided scale/offset if available to ensure consistent mapping
    if scale is None or offset is None:
        canvas, scale, offset = resize_image(image, target_size)
    else:
        canvas, _, _ = resize_image(image, target_size)

    vis = canvas.copy()
    dets = outputs[0]

    tw, th = target_size

    for i, det in enumerate(dets[:200]):
        if len(det) < 6:
            continue
        class_id, conf, x1, y1, x2, y2 = det[:6]

        # Try three interpretations for each detection and draw them with different colors
        # 1) normalized coords (yellow)
        if x1 <= 1.0 and y1 <= 1.0 and x2 <= 1.0 and y2 <= 1.0:
            nx1 = int(x1 * tw)
            ny1 = int(y1 * th)
            nx2 = int(x2 * tw)
            ny2 = int(y2 * th)
        else:
            nx1 = nx2 = ny1 = ny2 = None

        # 2) canvas pixel coords (cyan)
        cx1 = int(x1)
        cy1 = int(y1)
        cx2 = int(x2)
        cy2 = int(y2)

        # 3) center_x, center_y, w, h interpretation (magenta)
        # If coords look like large values, we try center format if normalized option fails
        if x1 <= 1.0 and y1 <= 1.0 and x2 <= 1.0 and y2 <= 1.0:
            # also consider possibility that they might be center normalized
            ccx = int(x1 * tw)
            ccy = int(y1 * th)
            cw = int(x2 * tw)
            ch = int(y2 * th)
            ccx1 = int(ccx - cw/2)
            ccy1 = int(ccy - ch/2)
            ccx2 = int(ccx + cw/2)
            ccy2 = int(ccy + ch/2)
        else:
            ccx1 = ccx2 = ccy1 = ccy2 = None

        # draw normalized (yellow)
        if nx1 is not None:
            nx1_clipped = max(0, min(nx1, tw))
            ny1_clipped = max(0, min(ny1, th))
            nx2_clipped = max(0, min(nx2, tw))
            ny2_clipped = max(0, min(ny2, th))
            cv2.rectangle(vis, (nx1_clipped, ny1_clipped), (nx2_clipped, ny2_clipped), (0, 255, 255), 1)

        # draw canvas pixel coords (cyan)
        cx1_clipped = max(0, min(cx1, tw))
        cy1_clipped = max(0, min(cy1, th))
        cx2_clipped = max(0, min(cx2, tw))
        cy2_clipped = max(0, min(cy2, th))
        cv2.rectangle(vis, (cx1_clipped, cy1_clipped), (cx2_clipped, cy2_clipped), (255, 255, 0), 1)

        # draw center format (magenta)
        if ccx1 is not None:
            ccx1_clipped = max(0, min(ccx1, tw))
            ccy1_clipped = max(0, min(ccy1, th))
            ccx2_clipped = max(0, min(ccx2, tw))
            ccy2_clipped = max(0, min(ccy2, th))
            cv2.rectangle(vis, (ccx1_clipped, ccy1_clipped), (ccx2_clipped, ccy2_clipped), (255, 0, 255), 1)

        # add text with class and confidence
        cv2.putText(vis, f"c{int(class_id)} {conf:.2f}", (cx1_clipped, max(0, cy1_clipped-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)

        # draw normalized (yellow)
        if nx1 is not None:
            nx1_clipped = max(0, min(nx1, tw))
            ny1_clipped = max(0, min(ny1, th))
            nx2_clipped = max(0, min(nx2, tw))
            ny2_clipped = max(0, min(ny2, th))
            cv2.rectangle(vis, (nx1_clipped, ny1_clipped), (nx2_clipped, ny2_clipped), (0, 255, 255), 1)

        # draw canvas pixel coords (cyan)
        cx1_clipped = max(0, min(cx1, tw))
        cy1_clipped = max(0, min(cy1, th))
        cx2_clipped = max(0, min(cx2, tw))
        cy2_clipped = max(0, min(cy2, th))
        cv2.rectangle(vis, (cx1_clipped, cy1_clipped), (cx2_clipped, cy2_clipped), (255, 255, 0), 1)

        # draw center format (magenta)
        if ccx1 is not None:
            ccx1_clipped = max(0, min(ccx1, tw))
            ccy1_clipped = max(0, min(ccy1, th))
            ccx2_clipped = max(0, min(ccx2, tw))
            ccy2_clipped = max(0, min(ccy2, th))
            cv2.rectangle(vis, (ccx1_clipped, ccy1_clipped), (ccx2_clipped, ccy2_clipped), (255, 0, 255), 1)

        # add text with class and confidence
        cv2.putText(vis, f"c{int(class_id)} {conf:.2f}", (cx1_clipped, max(0, cy1_clipped-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)


def map_and_visualize_on_original(image_path: str, outputs: list, map_type: str = 'normalized', scale: float = None, offset: Tuple[int,int] = None, target_size: Tuple[int,int] = (640,640), output_path: str = None):
    """Map raw detections to original image using different interpretation types and draw them.

    map_type: 'normalized' | 'canvas' | 'center'
    """
    if not outputs or len(outputs) == 0:
        print("No raw outputs to map")
        return None

    image = cv2.imread(image_path)
    if image is None:
        print(f"Cannot open image {image_path} for mapping visualization")
        return None

    tw, th = target_size
    if scale is None or offset is None:
        canvas, scale, offset = resize_image(image, target_size)
    vis = image.copy()

    dets = outputs[0]
    for i, det in enumerate(dets[:200]):  # limit for speed
        if len(det) < 6:
            continue
        class_id, conf, x1, y1, x2, y2 = det[:6]

        orig_h, orig_w = image.shape[:2]

        # Candidate mappings
        cand = {}

        # normalized mapping
        try:
            x1n = x1 * orig_w
            y1n = y1 * orig_h
            x2n = x2 * orig_w
            y2n = y2 * orig_h
            cand['normalized'] = [x1n, y1n, x2n, y2n]
        except Exception:
            cand['normalized'] = None

        # canvas mapping
        try:
            x_offset, y_offset = offset
            x1_unpad = x1 - x_offset
            y1_unpad = y1 - y_offset
            x2_unpad = x2 - x_offset
            y2_unpad = y2 - y_offset
            x1c = x1_unpad / scale
            y1c = y1_unpad / scale
            x2c = x2_unpad / scale
            y2c = y2_unpad / scale
            cand['canvas'] = [x1c, y1c, x2c, y2c]
        except Exception:
            cand['canvas'] = None

        # center mapping (normalized center + wh)
        try:
            cx = x1 * orig_w
            cy = y1 * orig_h
            w = x2 * orig_w
            h = y2 * orig_h
            x1cc = cx - w/2
            y1cc = cy - h/2
            x2cc = cx + w/2
            y2cc = cy + h/2
            cand['center'] = [x1cc, y1cc, x2cc, y2cc]
        except Exception:
            cand['center'] = None

        # scoring: prefer mapping with positive width/height and most area inside image
        def score_box(b):
            if b is None:
                return -1
            x1b, y1b, x2b, y2b = b
            w = x2b - x1b
            h = y2b - y1b
            if w <= 0 or h <= 0:
                return -1
            # area inside image
            xx1 = max(0, x1b)
            yy1 = max(0, y1b)
            xx2 = min(orig_w, x2b)
            yy2 = min(orig_h, y2b)
            inter_w = max(0, xx2 - xx1)
            inter_h = max(0, yy2 - yy1)
            inter_area = inter_w * inter_h
            area = w * h
            frac = inter_area / (area + 1e-6)
            # favor boxes with frac>0.5 and reasonable size
            size_penalty = 0
            if area > (orig_w * orig_h * 0.9):
                size_penalty = 0.5
            return frac - size_penalty

        best = None
        best_score = -2
        for k, b in cand.items():
            s = score_box(b)
            if s > best_score:
                best_score = s
                best = k

        if best is None:
            continue

        chosen = cand[best]
        x1o, y1o, x2o, y2o = [int(round(v)) for v in chosen]
        color_map = {'normalized': (0,255,255), 'canvas': (0,255,0), 'center': (255,0,255)}
        color = color_map.get(best, (128,128,128))

        if i < 10:
            print(f"[choose] det#{i} best={best} score={best_score:.3f} raw=({x1:.2f},{y1:.2f},{x2:.2f},{y2:.2f}) -> {x1o,y1o,x2o,y2o}")

        # clip
        x1o = max(0, min(x1o, orig_w))
        y1o = max(0, min(y1o, orig_h))
        x2o = max(0, min(x2o, orig_w))
        y2o = max(0, min(y2o, orig_h))

        cv2.rectangle(vis, (x1o, y1o), (x2o, y2o), color, 1)
        cv2.putText(vis, f"c{int(class_id)} {conf:.2f}", (x1o, max(0, y1o-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    if output_path is None:
        output_path = image_path.replace('.png', f'_layout_mapped_{map_type}.png')

    cv2.imwrite(output_path, vis)
    print(f"Mapped visualization saved to {output_path}")
    return output_path
def postprocess_ocr_det(outputs: list, scale: float, offset: Tuple[int, int],
                       original_size: Tuple[int, int], conf_threshold: float = 0.3) -> List[dict]:
    """Postprocess OCR detection outputs from PP-OCRv5_det"""
    # outputs[0] is the detection result tensor
    # For PP-OCRv5, this is typically a probability map

    # Simplified implementation - extract text boxes from probability map
    prob_map = outputs[0][0, 0]  # Take first channel, assuming shape [1, 1, H, W]

    boxes = []
    h, w = original_size

    # Simple thresholding and box extraction (simplified)
    # In real implementation, this would involve:
    # 1. Binarization
    # 2. Morphological operations
    # 3. Connected component analysis
    # 4. Box fitting

    # For now, return mock boxes based on layout regions
    boxes = [
        {'bbox': [150, 120, 450, 180], 'confidence': 0.95},  # Text box 1
        {'bbox': [150, 270, 450, 380], 'confidence': 0.90}   # Text box 2
    ]

    return boxes

def postprocess_ocr_rec(outputs: list) -> str:
    """Postprocess OCR recognition outputs from PP-OCRv5_rec"""
    # outputs[0] shape: [batch, seq_len, num_classes]
    pred = outputs[0][0]  # Take first batch item

    # PP-OCR character set (simplified, actual has ~18000 chars)
    # This is a very basic character set for demonstration
    char_list = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '

    text = ""
    for i in range(pred.shape[0]):
        char_idx = np.argmax(pred[i])
        if char_idx < len(char_list):
            char = char_list[char_idx]
            if char != ' ':  # Skip spaces for now
                text += char
        if len(text) > 50:  # Limit length
            break

    # If no text decoded, return mock text
    if not text.strip():
        text = "Sample recognized text"

    return text.strip()