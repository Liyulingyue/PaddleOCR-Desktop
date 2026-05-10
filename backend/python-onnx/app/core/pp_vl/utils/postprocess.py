import html
import itertools
import re
from collections import Counter
from typing import Dict, List, Tuple, Union

import numpy as np


IMAGE_LABELS = ["image", "header_image", "footer_image"]


def crop_margin(img):
    import cv2

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    if gray.dtype != np.uint8:
        gray = gray.astype(np.uint8)

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(binary)

    if coords is None:
        return img

    x, y, w, h = cv2.boundingRect(coords)
    return img[y : y + h, x : x + w]


def filter_overlap_boxes(boxes: List[Dict], layout_shape_mode: str = "auto") -> List[Dict]:
    filtered = [box for box in boxes if box.get("label") != "reference"]
    dropped = set()
    for i in range(len(filtered)):
        bbox = filtered[i].get("coordinate", [])
        if len(bbox) >= 4:
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if w < 6 or h < 6:
                dropped.add(i)
    return [box for idx, box in enumerate(filtered) if idx not in dropped]


def truncate_repetitive_content(
    content: str,
    min_count: int = 50,
) -> str:
    if len(content) < min_count:
        return content

    stripped = content.strip()
    if not stripped:
        return content

    if "\n" not in stripped and len(stripped) > 100:
        suffix_match = _find_repeating_suffix(stripped, min_len=8, min_repeats=5)
        if suffix_match:
            prefix, unit, count = suffix_match
            if len(unit) * count > len(stripped) * 0.5:
                return prefix

    if "\n" not in stripped and len(stripped) > 10:
        repeating = _find_shortest_repeating_substring(stripped)
        if repeating:
            count = len(stripped) // len(repeating)
            if count >= 10:
                return repeating

    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not lines:
        return content
    if len(lines) >= 10:
        line_counts = Counter(lines)
        most_common, count = line_counts.most_common(1)[0]
        if count >= 10 and (count / len(lines)) >= 0.8:
            return most_common

    return content


def _find_shortest_repeating_substring(s: str) -> Union[str, None]:
    n = len(s)
    for i in range(1, n // 2 + 1):
        if n % i == 0:
            substring = s[:i]
            if substring * (n // i) == s:
                return substring
    return None


def _find_repeating_suffix(s: str, min_len: int = 8, min_repeats: int = 5) -> Union[Tuple[str, str, int], None]:
    for i in range(len(s) // (min_repeats), min_len - 1, -1):
        unit = s[-i:]
        if s.endswith(unit * min_repeats):
            count = 0
            temp = s
            while temp.endswith(unit):
                temp = temp[:-i]
                count += 1
            start_index = len(s) - (count * i)
            return s[:start_index], unit, count
    return None


OTSL_NL = "<nl>"
OTSL_FCEL = "<fcel>"
OTSL_ECEL = "<ecel>"
OTSL_LCEL = "<lcel>"
OTSL_UCEL = "<ucel>"
OTSL_XCEL = "<xcel>"


def convert_otsl_to_html(otsl_content: str) -> str:
    otsl_content = _otsl_pad_to_sqr_v2(otsl_content)
    tokens, mixed_texts = _otsl_extract_tokens_and_text(otsl_content)
    table_cells, split_row_tokens = _otsl_parse_texts(mixed_texts, tokens)
    if not split_row_tokens:
        return ""
    nrows = len(split_row_tokens)
    ncols = max(len(row) for row in split_row_tokens) if split_row_tokens else 0
    if not table_cells:
        return ""
    grid = [[None] * ncols for _ in range(nrows)]
    for cell in table_cells:
        sr, er, sc, ec = (
            cell["start_row"],
            cell["end_row"],
            cell["start_col"],
            cell["end_col"],
        )
        for r in range(max(0, sr), min(nrows, er)):
            for c in range(max(0, sc), min(ncols, ec)):
                grid[r][c] = cell

    body = ""
    for i in range(nrows):
        body += "<tr>"
        for j in range(ncols):
            cell = grid[i][j]
            if cell is None:
                continue
            if cell.get("start_row") != i or cell.get("start_col") != j:
                continue
            content = html.escape(cell.get("text", "").strip())
            rowspan = cell.get("row_span", 1)
            colspan = cell.get("col_span", 1)
            celltag = "td"
            attrs = ""
            if rowspan > 1:
                attrs += f' rowspan="{rowspan}"'
            if colspan > 1:
                attrs += f' colspan="{colspan}"'
            body += f"<td{attrs}>{content}</td>"
        body += "</tr>"
    return f"<table>{body}</table>"


def _otsl_pad_to_sqr_v2(s: str) -> str:
    s = s.strip()
    if OTSL_NL not in s:
        return s + OTSL_NL
    lines = s.split(OTSL_NL)
    row_data = []
    for line in lines:
        if not line:
            continue
        cells = re.findall(r"<fcel>|<ecel>|<nl>|<lcel>|<ucel>|<xcel>", line)
        if not cells:
            continue
        row_data.append({"cells": cells, "total": len(cells)})
    if not row_data:
        return OTSL_NL
    max_total = max(r["total"] for r in row_data)
    result_lines = []
    for row in row_data:
        cells = row["cells"]
        if len(cells) > max_total:
            cells = cells[:max_total]
        else:
            cells = cells + [OTSL_ECEL] * (max_total - len(cells))
        result_lines.append("".join(cells))
    return OTSL_NL.join(result_lines) + OTSL_NL


def _otsl_extract_tokens_and_text(s: str):
    pattern = r"(" + "|".join([re.escape(OTSL_NL), re.escape(OTSL_FCEL), re.escape(OTSL_ECEL), re.escape(OTSL_LCEL), re.escape(OTSL_UCEL), re.escape(OTSL_XCEL)]) + r")"
    tokens = re.findall(pattern, s)
    parts = re.split(pattern, s)
    parts = [p for p in parts if p.strip()]
    return tokens, parts


def _otsl_parse_texts(texts, tokens):
    split_nl = OTSL_NL
    split_row_tokens = [
        list(group)
        for key, group in itertools.groupby(tokens, lambda z: z == split_nl)
        if not key
    ]
    table_cells = []
    r_idx, c_idx = 0, 0
    if split_row_tokens:
        max_cols = max(len(row) for row in split_row_tokens)
        for row in split_row_tokens:
            while len(row) < max_cols:
                row.append(OTSL_ECEL)

    for i, text in enumerate(texts):
        cell_text = ""
        row_span, col_span = 1, 1
        right_offset = 1
        if text in [OTSL_FCEL, OTSL_ECEL]:
            if text != OTSL_ECEL:
                cell_text = texts[i + 1] if i + 1 < len(texts) else ""
                right_offset = 2

            next_right = texts[i + right_offset] if i + right_offset < len(texts) else ""
            next_bottom = split_row_tokens[r_idx + 1][c_idx] if r_idx + 1 < len(split_row_tokens) and c_idx < len(split_row_tokens[r_idx + 1]) else ""

            if next_right in [OTSL_LCEL, OTSL_XCEL]:
                col_span += _count_right(split_row_tokens, c_idx + 1, r_idx, [OTSL_LCEL, OTSL_XCEL])
            if next_bottom in [OTSL_UCEL, OTSL_XCEL]:
                row_span += _count_down(split_row_tokens, c_idx, r_idx + 1, [OTSL_UCEL, OTSL_XCEL])

            table_cells.append({
                "text": cell_text.strip(),
                "row_span": row_span,
                "col_span": col_span,
                "start_row": r_idx,
                "end_row": r_idx + row_span,
                "start_col": c_idx,
                "end_col": c_idx + col_span,
            })

        if text in [OTSL_FCEL, OTSL_ECEL, OTSL_LCEL, OTSL_UCEL, OTSL_XCEL]:
            c_idx += 1
        if text == OTSL_NL:
            r_idx += 1
            c_idx = 0

    return table_cells, split_row_tokens


def _count_right(tokens, c_idx, r_idx, which):
    span = 0
    while c_idx < len(tokens[r_idx]) and tokens[r_idx][c_idx] in which:
        c_idx += 1
        span += 1
        if c_idx >= len(tokens[r_idx]):
            break
    return span


def _count_down(tokens, c_idx, r_idx, which):
    span = 0
    while r_idx < len(tokens) and c_idx < len(tokens[r_idx]) and tokens[r_idx][c_idx] in which:
        r_idx += 1
        span += 1
        if r_idx >= len(tokens):
            break
    return span


def apply_latex_formatting(text: str) -> str:
    text = text.replace("$", "")
    text = text.replace("\\(", " $ ").replace("\\)", " $")
    text = text.replace("\\[\\[", "[").replace("\\]\\]", "]")
    text = text.replace("\\[", " $$ ").replace("\\]", " $$ ")
    return text


def format_vlm_result(result_str: str, block_label: str) -> str:
    if result_str is None:
        return ""

    min_count = 5000 if block_label == "table" else 50
    result_str = truncate_repetitive_content(result_str, min_count=min_count)
    result_str = apply_latex_formatting(result_str)

    if block_label == "table":
        html_str = convert_otsl_to_html(result_str)
        if html_str:
            return html_str

    return result_str
