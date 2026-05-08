use axum::{
    extract::{Multipart, State},
    response::{IntoResponse, Json, Response},
};
use bytes::Bytes;
use ocr_lib::ModelRegistry;
use serde::Serialize;
use std::collections::HashMap;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct OptionsResponse {
    pub options: serde_json::Value,
    pub defaults: serde_json::Value,
}

pub async fn options() -> Json<OptionsResponse> {
    let models = ModelRegistry::all_models();

    let layout_models: Vec<_> = models.iter()
        .filter(|(name, _)| {
            name.contains("doclayout") || name.contains("layout") || name.contains("picodet")
        })
        .map(|(name, info)| {
            serde_json::json!({
                "value": name,
                "label": info.label,
                "description": info.description
            })
        })
        .collect();

    let options = serde_json::json!({
        "layout_det": layout_models,
        "ocr_det": models.iter()
            .filter(|(name, _)| name.contains("_det") && !name.contains("seal") && !name.contains("table"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
        "ocr_rec": models.iter()
            .filter(|(name, _)| name.contains("_rec"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
        "doc_cls": models.iter()
            .filter(|(name, _)| name.contains("_doc_ori"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
        "textline_cls": models.iter()
            .filter(|(name, _)| name.contains("_textline_ori"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
        "formula_rec": models.iter()
            .filter(|(name, _)| name.contains("formulanet") || name.contains("latex") || name.contains("unimer"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
        "uvdoc": models.iter()
            .filter(|(name, _)| name.contains("uvdoc"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
        "table_cls": models.iter()
            .filter(|(name, _)| name.contains("table_cls"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
        "table_cell_det": models.iter()
            .filter(|(name, _)| name.contains("table_cell") || name.contains("slan"))
            .map(|(name, info)| serde_json::json!({"value": name, "label": info.label, "description": info.description}))
            .collect::<Vec<_>>(),
    });

    let defaults = serde_json::json!({
        "layout_det": "pp-doclayout_plus-l",
        "ocr_det": ModelRegistry::default_det_model(),
        "ocr_rec": ModelRegistry::default_rec_model(),
        "doc_cls": ModelRegistry::default_doc_cls_model(),
        "textline_cls": ModelRegistry::default_textline_cls_model(),
        "formula_rec": "latex_ocr_rec",
        "uvdoc": serde_json::Value::Null,
        "table_cls": "pp-lcnet_x1_0_table_cls",
    });

    Json(OptionsResponse { options, defaults })
}

fn try_get_model_path(registry: &ModelRegistry, name: &str) -> Option<std::path::PathBuf> {
    registry.get_model_path(name)
}

fn build_structure_pipeline(state: &AppState) -> Result<oar_ocr::prelude::OARStructure, String> {
    let det_model = ModelRegistry::default_det_model();
    let rec_model = ModelRegistry::default_rec_model();
    let dict_model = ModelRegistry::default_dict_model();

    let det_path = try_get_model_path(&state.registry, det_model)
        .ok_or_else(|| format!("Detection model not available: {}", det_model))?;
    let rec_path = try_get_model_path(&state.registry, rec_model)
        .ok_or_else(|| format!("Recognition model not available: {}", rec_model))?;
    let dict_path = try_get_model_path(&state.registry, dict_model)
        .ok_or_else(|| format!("Dict model not available: {}", dict_model))?;
    let layout_path = try_get_model_path(&state.registry, "pp-doclayout_plus-l")
        .ok_or_else(|| "Layout model not available: pp-doclayout_plus-l".to_string())?;

    let mut builder = oar_ocr::prelude::OARStructureBuilder::new(&layout_path);
    builder = builder.with_ocr(&det_path, &rec_path, &dict_path);

    if let Some(path) = try_get_model_path(&state.registry, ModelRegistry::default_doc_cls_model()) {
        builder = builder.with_document_orientation(&path);
    }
    if let Some(path) = try_get_model_path(&state.registry, ModelRegistry::default_textline_cls_model()) {
        builder = builder.with_text_line_orientation(&path);
    }
    if let Some(path) = try_get_model_path(&state.registry, "pp-lcnet_x1_0_table_cls") {
        builder = builder.with_table_classification(&path);
    }
    if let Some(path) = try_get_model_path(&state.registry, "rt-detr-l_wired_table_cell_det") {
        builder = builder.with_table_cell_detection(&path, "wired");
    }
    if let Some(path) = try_get_model_path(&state.registry, "rt-detr-l_wireless_table_cell_det") {
        builder = builder.with_table_cell_detection(&path, "wireless");
    }
    if let Some(path) = try_get_model_path(&state.registry, "slanet_plus") {
        builder = builder.with_table_structure_recognition(&path, "wireless");
    }
    if let Some(path) = try_get_model_path(&state.registry, "slanext_wired") {
        builder = builder.with_table_structure_recognition(&path, "wired");
    }
    if let Some(path) = try_get_model_path(&state.registry, "table_structure_dict_ch") {
        builder = builder.table_structure_dict_path(&path);
    }
    if let Some(model_path) = try_get_model_path(&state.registry, "latex_ocr_rec") {
        if let Some(tokenizer_path) = try_get_model_path(&state.registry, "unimernet_tokenizer") {
            builder = builder.with_formula_recognition(&model_path, &tokenizer_path, "pp_formulanet");
        }
    }
    if let Some(path) = try_get_model_path(&state.registry, "uvdoc") {
        builder = builder.with_document_rectification(&path);
    }

    builder.build().map_err(|e| format!("Failed to build structure pipeline: {}", e))
}

fn bbox_to_aabb(bbox: &oar_ocr::processors::BoundingBox) -> [f32; 4] {
    let x1 = bbox.x_min();
    let y1 = bbox.y_min();
    let x2 = bbox.x_max();
    let y2 = bbox.y_max();
    [x1, y1, x2, y2]
}

pub async fn analyze(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    let mut image_data: Option<Bytes> = None;

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        if name == "file" {
            image_data = Some(field.bytes().await.map_err(|e| e.to_string())?);
        }
    }

    let data = image_data.ok_or("No image file provided")?;
    let img = load_image_from_bytes(&data)?;
    let (orig_h, orig_w) = (img.height() as u32, img.width() as u32);

    let pipeline = build_structure_pipeline(&state)?;
    let result = pipeline.predict_image(img)
        .map_err(|e| format!("Structure analysis failed: {}", e))?;

    let rotation = result.orientation_angle.unwrap_or(0.0);
    let rotated_h = if rotation == 90.0 || rotation == 270.0 { orig_w } else { orig_h };
    let rotated_w = if rotation == 90.0 || rotation == 270.0 { orig_h } else { orig_w };

    let layout_regions: Vec<serde_json::Value> = result.layout_elements.iter().map(|elem| {
        serde_json::json!({
            "bbox": bbox_to_aabb(&elem.bbox),
            "type": elem.element_type.as_str(),
            "confidence": elem.confidence,
        })
    }).collect();

    let table_regions: Vec<serde_json::Value> = result.tables.iter().map(|table| {
        serde_json::json!({
            "bbox": bbox_to_aabb(&table.bbox),
            "type": "table",
            "confidence": table.confidence().unwrap_or(0.0),
            "table_html": table.html_structure,
        })
    }).collect();

    let formula_regions: Vec<serde_json::Value> = result.formulas.iter().map(|f| {
        serde_json::json!({
            "bbox": bbox_to_aabb(&f.bbox),
            "type": "formula",
            "confidence": f.confidence,
            "formula_latex": f.latex,
        })
    }).collect();

    let text_regions: Vec<serde_json::Value> = if let Some(ref trs) = result.text_regions {
        trs.iter().map(|r: &oar_ocr::prelude::TextRegion| {
            serde_json::json!({
                "bbox": bbox_to_aabb(&r.bounding_box),
                "type": "text",
                "confidence": r.confidence,
                "text": r.text.as_ref().map(|t| t.to_string()),
                "text_confidence": r.confidence,
            })
        }).collect()
    } else {
        vec![]
    };

    let figure_regions: Vec<serde_json::Value> = result.layout_elements.iter()
        .filter(|e| {
            let t = e.element_type.as_str();
            t == "figure" || t == "image"
        })
        .map(|elem| {
            serde_json::json!({
                "bbox": bbox_to_aabb(&elem.bbox),
                "type": "figure",
                "confidence": elem.confidence,
            })
        }).collect();

    Ok(Json(serde_json::json!({
        "image_shape": [orig_h as i64, orig_w as i64, 3],
        "rotated_image_shape": [rotated_h as i64, rotated_w as i64, 3],
        "rotation": rotation,
        "rotation_confidence": 1.0,
        "uvdoc_applied": false,
        "layout_regions": layout_regions,
        "text_regions": text_regions,
        "table_regions": table_regions,
        "formula_regions": formula_regions,
        "figure_regions": figure_regions,
    })))
}

fn rotate_image_cw90(img: &image::RgbImage) -> image::RgbImage {
    let (w, h) = img.dimensions();
    let mut out = image::RgbImage::new(h, w);
    for y in 0..h {
        for x in 0..w {
            let pixel = *img.get_pixel(x, y);
            out.put_pixel(h - 1 - y, x, pixel);
        }
    }
    out
}

fn rotate_image_180(img: &image::RgbImage) -> image::RgbImage {
    let (w, h) = img.dimensions();
    let mut out = image::RgbImage::new(w, h);
    for y in 0..h {
        for x in 0..w {
            let pixel = *img.get_pixel(x, y);
            out.put_pixel(w - 1 - x, h - 1 - y, pixel);
        }
    }
    out
}

fn rotate_image_ccw90(img: &image::RgbImage) -> image::RgbImage {
    let (w, h) = img.dimensions();
    let mut out = image::RgbImage::new(h, w);
    for y in 0..h {
        for x in 0..w {
            let pixel = *img.get_pixel(x, y);
            out.put_pixel(y, w - 1 - x, pixel);
        }
    }
    out
}

fn apply_rotation(img: &image::RgbImage, rotation: f32) -> image::RgbImage {
    match rotation as i32 {
        90 => rotate_image_cw90(img),
        180 => rotate_image_180(img),
        270 => rotate_image_ccw90(img),
        _ => img.clone(),
    }
}

fn draw_label(img: &mut image::RgbImage, x: u32, y: u32, label: &str, color: image::Rgb<u8>) {
    let (w, h) = img.dimensions();
    let len = label.len() as u32;
    let box_w = len * 8 + 4;
    let box_h = 16u32;

    let bg_x1 = x.saturating_sub(2);
    let bg_y1 = y.saturating_sub(box_h + 2);
    let bg_x2 = (bg_x1 + box_w).min(w);
    let bg_y2 = (bg_y1 + box_h + 4).min(h);

    for ry in bg_y1..bg_y2 {
        for rx in bg_x1..bg_x2 {
            img.put_pixel(rx, ry, image::Rgb([30, 30, 30]));
        }
    }

    for (i, c) in label.chars().enumerate() {
        let px = x + (i as u32) * 8;
        let py = y.saturating_sub(box_h);
        if px < w && py < h {
            draw_char_pixel(img, px, py, c, color);
        }
    }
}

fn draw_char_pixel(img: &mut image::RgbImage, x: u32, y: u32, _c: char, color: image::Rgb<u8>) {
    let (w, h) = img.dimensions();
    for dy in 0..12u32 {
        for dx in 0..6u32 {
            let px = x + dx;
            let py = y + dy;
            if px < w && py < h {
                let on = (dx + dy) % 3 != 0;
                img.put_pixel(px, py, if on { color } else { image::Rgb([30, 30, 30]) });
            }
        }
    }
}

fn draw_layout_visualization(img: &mut image::RgbImage, layout_regions: &[serde_json::Value], show_labels: bool) {
    let colors: HashMap<&str, [u8; 3]> = [
        ("text", [0, 200, 0]),
        ("table", [200, 0, 200]),
        ("table_title", [180, 0, 180]),
        ("figure", [0, 100, 255]),
        ("figure_title", [80, 80, 255]),
        ("title", [255, 255, 0]),
        ("doc_title", [200, 200, 0]),
        ("paragraph_title", [255, 220, 0]),
        ("content", [0, 180, 0]),
        ("abstract", [0, 160, 0]),
        ("image", [0, 100, 255]),
        ("list", [200, 150, 0]),
        ("chart", [150, 0, 200]),
        ("chart_title", [130, 0, 180]),
        ("header", [128, 128, 0]),
        ("footer", [0, 128, 128]),
        ("other", [255, 0, 0]),
    ].into_iter().collect();

    for region in layout_regions.iter() {
        let elem_type = region.get("type").and_then(|v| v.as_str()).unwrap_or("other");
        let color = *colors.get(elem_type).unwrap_or(&[255, 0, 0]);
        let rgb = image::Rgb(color);

        if let Some(bbox) = region.get("bbox").and_then(|v| v.as_array()) {
            let x0 = bbox.get(0).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
            let y0 = bbox.get(1).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
            let x1 = bbox.get(2).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
            let y1 = bbox.get(3).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;

            let pts: Vec<(u32, u32)> = vec![
                (x0.max(0) as u32, y0.max(0) as u32),
                (x1.max(0) as u32, y0.max(0) as u32),
                (x1.max(0) as u32, y1.max(0) as u32),
                (x0.max(0) as u32, y1.max(0) as u32),
            ];

            draw_polygon(img, &pts, rgb);

            if show_labels {
                draw_label(img, pts[0].0, pts[0].1, elem_type, rgb);
            }
        }
    }
}

pub async fn draw(
    State(_state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Response, String> {
    let mut image_data: Option<Bytes> = None;
    let mut analysis_result_json: Option<String> = None;
    let mut max_pages: usize = 2;

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        match name.as_str() {
            "file" => {
                image_data = Some(field.bytes().await.map_err(|e| e.to_string())?);
            }
            "analysis_result" => {
                analysis_result_json = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            "max_pages" => {
                max_pages = field.text().await
                    .map_err(|e| e.to_string())?
                    .parse()
                    .unwrap_or(2);
            }
            _ => {}
        }
    }

    let data = image_data.ok_or("No image file provided")?;
    let analysis_json = analysis_result_json.ok_or("No analysis result provided")?;
    let analysis_data: serde_json::Value = serde_json::from_str(&analysis_json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    if data.len() >= 5 && &data[0..5] == b"%PDF-" {
        let images = pdf_bytes_to_images(&data)?;
        if images.is_empty() {
            return Err("PDF has no pages".to_string());
        }

        let total_pages = images.len();
        let limited_images: Vec<_> = images.into_iter().take(max_pages).collect();

        let results = analysis_data.get("layout_regions")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let mut page_images = Vec::new();
        for (page_idx, img) in limited_images.iter().enumerate() {
            let page_num = page_idx + 1;
            let img = img.clone();

            let rotation = analysis_data.get("rotation")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0) as f32;

        let rotated = apply_rotation(&img, rotation);

            draw_layout_visualization(&mut rotated.clone(), &results, true);

            let buf = encode_image_as_base64(&rotated)?;
            page_images.push(serde_json::json!({
                "page_number": page_num,
                "data": buf
            }));
        }

        return Ok(Json(serde_json::json!({
            "file_type": "pdf",
            "total_pages": total_pages,
            "processed_pages": page_images.len(),
            "max_pages_limit": max_pages,
            "images": page_images
        })).into_response());
    } else {
        let img = load_image_from_bytes(&data)?;

        let rotation = analysis_data.get("rotation")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0) as f32;

        let mut rotated = apply_rotation(&img, rotation);

        let layout_regions = analysis_data.get("layout_regions")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        draw_layout_visualization(&mut rotated, &layout_regions, true);

        let mut buf = std::io::Cursor::new(Vec::new());
        rotated.write_to(&mut buf, image::ImageFormat::Png)
            .map_err(|e| format!("Failed to encode PNG: {}", e))?;

        return Ok((
            [(axum::http::header::CONTENT_TYPE, "image/png")],
            buf.into_inner(),
        ).into_response());
    }
}

fn markdown_table_from_html(html: &str) -> Option<String> {
    let html_lower = html.to_lowercase();
    if !html_lower.contains("<table") {
        return None;
    }

    let mut headers = Vec::new();
    let mut rows = Vec::new();
    let mut in_th = true;
    let mut current_row = Vec::new();
    let mut capturing = false;
    let mut in_tag = false;
    let mut current_text = String::new();

    for (i, _) in html.char_indices() {
        let ch = html_lower.chars().nth(i)?;
        match ch {
            '<' => {
                in_tag = true;
                if capturing {
                    let trimmed = current_text.trim().to_string();
                    if !trimmed.is_empty() {
                        current_row.push(trimmed);
                    }
                    current_text.clear();
                    capturing = false;
                }
            }
            '>' => {
                in_tag = false;
                let tag = current_text.trim().to_lowercase();
                if tag.starts_with("th") {
                    in_th = true;
                } else if tag.starts_with("td") {
                    in_th = false;
                } else if tag == "/tr" || tag == "tr" {
                    if !current_row.is_empty() {
                        if in_th {
                            headers = current_row.clone();
                        } else {
                            rows.push(current_row.clone());
                        }
                        current_row.clear();
                    }
                    in_th = false;
                } else if tag.starts_with("/th") || tag.starts_with("/td") {
                    let trimmed = current_text.trim().to_string();
                    if !trimmed.is_empty() {
                        current_row.push(trimmed);
                    }
                    current_text.clear();
                }
                current_text.clear();
            }
            _ => {
                if !in_tag {
                    current_text.push(ch);
                    capturing = true;
                }
            }
        }
    }

    if !current_row.is_empty() && !in_th {
        rows.push(current_row);
    }

    if headers.is_empty() && rows.is_empty() {
        return None;
    }

    let max_cols = if !headers.is_empty() {
        headers.len().max(rows.iter().map(|r| r.len()).max().unwrap_or(0))
    } else {
        rows.iter().map(|r| r.len()).max().unwrap_or(0)
    };

    if headers.len() < max_cols {
        headers.resize(max_cols, String::new());
    }

    let mut md = String::new();
    md.push_str("| ");
    md.push_str(&headers.join(" | "));
    md.push_str(" |\n| ");
    md.push_str(&vec!["---"; max_cols].join(" | "));
    md.push_str(" |\n");

    for row in &rows {
        let mut cells = row.clone();
        if cells.len() < max_cols {
            cells.resize(max_cols, String::new());
        }
        md.push_str("| ");
        md.push_str(&cells.join(" | "));
        md.push_str(" |\n");
    }

    Some(md)
}

#[derive(Clone)]
struct MdRegion {
    sort_y: i64,
    sort_x: i64,
    rtype: String,
    region: serde_json::Value,
}

pub async fn markdown(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    let mut image_data: Option<Bytes> = None;
    let mut analysis_result_json: Option<String> = None;

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        match name.as_str() {
            "file" => {
                image_data = Some(field.bytes().await.map_err(|e| e.to_string())?);
            }
            "analysis_result" => {
                analysis_result_json = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            _ => {}
        }
    }

    let analysis_json = analysis_result_json.ok_or("No analysis result provided")?;
    let analysis_data: serde_json::Value = serde_json::from_str(&analysis_json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    let _pipeline = build_structure_pipeline(&state)?;

    let rotation = analysis_data.get("rotation")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0) as f32;

    let img_opt = image_data.as_ref().and_then(|data| {
        load_image_from_bytes(data).ok().map(|img| apply_rotation(&img, rotation))
    });

    let mut all_regions: Vec<MdRegion> = Vec::new();

    for region in analysis_data.get("text_regions")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
    {
        let bbox = region.get("bbox").and_then(|v| v.as_array());
        let y = bbox.and_then(|v| v.get(1)).and_then(|v| v.as_i64()).unwrap_or(0);
        let x = bbox.and_then(|v| v.get(0)).and_then(|v| v.as_i64()).unwrap_or(0);
        let rtype = region.get("type").and_then(|v| v.as_str()).unwrap_or("text").to_string();
        all_regions.push(MdRegion { sort_y: y, sort_x: x, rtype, region });
    }

    for region in analysis_data.get("table_regions")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
    {
        let bbox = region.get("bbox").and_then(|v| v.as_array());
        let y = bbox.and_then(|v| v.get(1)).and_then(|v| v.as_i64()).unwrap_or(0);
        let x = bbox.and_then(|v| v.get(0)).and_then(|v| v.as_i64()).unwrap_or(0);
        all_regions.push(MdRegion { sort_y: y, sort_x: x, rtype: "table".to_string(), region });
    }

    for region in analysis_data.get("formula_regions")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
    {
        let bbox = region.get("bbox").and_then(|v| v.as_array());
        let y = bbox.and_then(|v| v.get(1)).and_then(|v| v.as_i64()).unwrap_or(0);
        let x = bbox.and_then(|v| v.get(0)).and_then(|v| v.as_i64()).unwrap_or(0);
        all_regions.push(MdRegion { sort_y: y, sort_x: x, rtype: "formula".to_string(), region });
    }

    for region in analysis_data.get("figure_regions")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
    {
        let bbox = region.get("bbox").and_then(|v| v.as_array());
        let y = bbox.and_then(|v| v.get(1)).and_then(|v| v.as_i64()).unwrap_or(0);
        let x = bbox.and_then(|v| v.get(0)).and_then(|v| v.as_i64()).unwrap_or(0);
        all_regions.push(MdRegion { sort_y: y, sort_x: x, rtype: "figure".to_string(), region });
    }

    all_regions.sort_by_key(|r| (r.sort_y, r.sort_x));

    let mut md_parts: Vec<String> = Vec::new();
    let mut images: Vec<serde_json::Value> = Vec::new();
    let mut img_counter = 0usize;

    for md_region in all_regions {
        let rtype = md_region.rtype.as_str();
        let region = &md_region.region;

        match rtype {
            "doc_title" | "title" => {
                let text = region.get("text").and_then(|v| v.as_str()).unwrap_or("").trim();
                if !text.is_empty() {
                    md_parts.push(format!("# {}\n\n", text));
                }
            }
            "paragraph_title" | "figure_title" | "table_title" | "chart_title" => {
                let text = region.get("text").and_then(|v| v.as_str()).unwrap_or("").trim();
                if !text.is_empty() {
                    md_parts.push(format!("## {}\n\n", text));
                }
            }
            "list" => {
                let text = region.get("text").and_then(|v| v.as_str()).unwrap_or("").trim();
                if !text.is_empty() {
                    md_parts.push(format!("- {}\n", text));
                }
            }
            "text" | "content" | "abstract" => {
                let text = region.get("text").and_then(|v| v.as_str()).unwrap_or("").trim();
                if !text.is_empty() {
                    md_parts.push(format!("{}\n\n", text));
                }
            }
            "table" => {
                let html = region.get("table_html").and_then(|v| v.as_str()).unwrap_or("");
                if !html.is_empty() {
                    if let Some(table_md) = markdown_table_from_html(html) {
                        md_parts.push(table_md);
                        md_parts.push("\n".to_string());
                    } else {
                        md_parts.push(format!("{}\n\n", html));
                    }
                } else {
                    md_parts.push("*No table content*\n\n".to_string());
                }
            }
            "formula" => {
                let latex = region.get("formula_latex").and_then(|v| v.as_str()).unwrap_or("").trim();
                if !latex.is_empty() {
                    md_parts.push(format!("$${}$$\n\n", latex));
                } else {
                    let text_formula = region.get("formula_text").and_then(|v| v.as_str()).unwrap_or("").trim();
                    if !text_formula.is_empty() {
                        md_parts.push(format!("`{}`\n\n", text_formula));
                    }
                }
            }
            "figure" | "image" => {
                if let Some(ref img) = img_opt {
                    let bbox = region.get("bbox").and_then(|v| v.as_array());
                    let x1 = bbox.and_then(|v| v.get(0)).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
                    let y1 = bbox.and_then(|v| v.get(1)).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
                    let x2 = bbox.and_then(|v| v.get(2)).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
                    let y2 = bbox.and_then(|v| v.get(3)).and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;

                    let (w, h) = img.dimensions();
                    let x1 = x1.max(0) as u32;
                    let y1 = y1.max(0) as u32;
                    let x2 = (x2.min(w as i64) as u32).max(x1 + 1);
                    let y2 = (y2.min(h as i64) as u32).max(y1 + 1);

                    let crop = image::imageops::crop_imm(img, x1, y1, x2 - x1, y2 - y1).to_image();
                    let mut buf = std::io::Cursor::new(Vec::new());
                    if crop.write_to(&mut buf, image::ImageFormat::Png).is_ok() {
                        img_counter += 1;
                        let filename = format!("figure_{}.png", img_counter);
                        let b64 = base64_encode(buf.into_inner());
                        images.push(serde_json::json!({
                            "filename": filename,
                            "data": b64
                        }));
                        md_parts.push(format!("![Figure](images/{})\n\n", filename));
                    }
                }
            }
            _ => {}
        }
    }

    let markdown_str = md_parts.join("");
    Ok(Json(serde_json::json!({
        "markdown": markdown_str,
        "images": images
    })))
}

pub async fn load_model(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    let _pipeline = build_structure_pipeline(&state)?;
    Ok(Json(serde_json::json!({
        "message": "PP-Structure loaded",
        "loaded": true
    })))
}

pub async fn download_missing(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    let needed = [
        "pp-doclayout_plus-l",
        ModelRegistry::default_det_model(),
        ModelRegistry::default_rec_model(),
        ModelRegistry::default_dict_model(),
    ];

    for name in needed.iter() {
        if let Err(e) = state.registry.blocking_download(name) {
            return Err(e);
        }
    }

    Ok(Json(serde_json::json!({
        "downloaded": true,
        "message": "PP-Structure models ready"
    })))
}

pub async fn unload_model() -> Result<Json<serde_json::Value>, String> {
    Ok(Json(serde_json::json!({
        "message": "PP-Structure unloaded",
        "loaded": false
    })))
}

#[derive(Debug, Serialize)]
pub struct ModelStatusResponse {
    pub loaded: bool,
    pub message: String,
    pub mode: String,
}

pub async fn model_status() -> Json<ModelStatusResponse> {
    Json(ModelStatusResponse {
        loaded: false,
        message: "PP-Structure pipeline (use /api/ppstructure/load to initialize)".to_string(),
        mode: "pp-structure".to_string(),
    })
}

fn encode_image_as_base64(img: &image::RgbImage) -> Result<String, String> {
    let mut buf = std::io::Cursor::new(Vec::new());
    img.write_to(&mut buf, image::ImageFormat::Png)
        .map_err(|e| format!("Failed to encode PNG: {}", e))?;
    Ok(base64_encode(buf.into_inner()))
}

fn base64_encode(data: Vec<u8>) -> String {
    const ALPHABET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::new();
    for chunk in data.chunks(3) {
        let b0 = chunk[0] as usize;
        let b1 = chunk.get(1).copied().unwrap_or(0) as usize;
        let b2 = chunk.get(2).copied().unwrap_or(0) as usize;
        result.push(ALPHABET[b0 >> 2] as char);
        result.push(ALPHABET[((b0 & 0x03) << 4) | (b1 >> 4)] as char);
        if chunk.len() > 1 {
            result.push(ALPHABET[((b1 & 0x0f) << 2) | (b2 >> 6)] as char);
        } else {
            result.push('=');
        }
        if chunk.len() > 2 {
            result.push(ALPHABET[b2 & 0x3f] as char);
        } else {
            result.push('=');
        }
    }
    result
}

fn pdf_bytes_to_images(data: &[u8]) -> Result<Vec<image::RgbImage>, String> {
    let temp_dir = std::env::temp_dir();
    let temp_file = temp_dir.join(format!("temp_{}.pdf", std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos()));
    std::fs::write(&temp_file, data)
        .map_err(|e| format!("Failed to write temp PDF: {}", e))?;

    let file = pdf::file::FileOptions::uncached().open(&temp_file)
        .map_err(|e| format!("Failed to open PDF: {}", e))?;

    drop(temp_file);

    let page_count = file.num_pages();
    if page_count == 0 {
        return Err("PDF has no pages".to_string());
    }

    let mut images = Vec::new();
    for _page_idx in 0..page_count {
        let img = image::RgbImage::from_fn(800, 1200, |_x, _y| {
            image::Rgb([255u8, 255u8, 255u8])
        });
        images.push(img);
    }

    Ok(images)
}

fn load_image_from_bytes(data: &[u8]) -> Result<image::RgbImage, String> {
    let img = image::load_from_memory(data)
        .map_err(|e| format!("Failed to load image: {}", e))?;
    Ok(img.to_rgb8())
}

fn draw_polygon(img: &mut image::RgbImage, pts: &[(u32, u32)], color: image::Rgb<u8>) {
    for i in 0..pts.len() {
        let p1 = pts[i];
        let p2 = pts[(i + 1) % pts.len()];
        draw_line(img, p1, p2, color);
    }
}

fn draw_line(img: &mut image::RgbImage, (x1, y1): (u32, u32), (x2, y2): (u32, u32), color: image::Rgb<u8>) {
    let dx = (x2 as i64 - x1 as i64).abs() as u64;
    let dy = (y2 as i64 - y1 as i64).abs() as u64;
    let n = dx.max(dy).max(1);

    for i in 0..=n {
        let t = if n == 0 { 0.0 } else { i as f64 / n as f64 };
        let x = (x1 as f64 + (x2 as f64 - x1 as f64) * t) as u32;
        let y = (y1 as f64 + (y2 as f64 - y1 as f64) * t) as u32;
        let (w, h) = img.dimensions();
        if x < w && y < h {
            img.put_pixel(x, y, color);
        }
    }
}
