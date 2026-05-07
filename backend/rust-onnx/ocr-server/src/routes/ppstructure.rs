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

    let pipeline = build_structure_pipeline(&state)?;
    let result = pipeline.predict_image(img)
        .map_err(|e| format!("Structure analysis failed: {}", e))?;

    let layout_regions: Vec<serde_json::Value> = result.layout_elements.iter().map(|elem| {
        let pts: Vec<[f32; 2]> = elem.bbox.points.iter()
            .map(|p| [p.x, p.y])
            .collect();
        serde_json::json!({
            "bbox": {
                "points": pts,
            },
            "type": elem.element_type.as_str(),
            "confidence": elem.confidence,
            "label": elem.label,
            "text": elem.text,
            "order_index": elem.order_index,
        })
    }).collect();

    let tables: Vec<serde_json::Value> = result.tables.iter().map(|table| {
        let pts: Vec<[f32; 2]> = table.bbox.points.iter()
            .map(|p| [p.x, p.y])
            .collect();
        serde_json::json!({
            "bbox": {
                "points": pts,
            },
            "table_type": format!("{:?}", table.table_type),
            "confidence": table.confidence().unwrap_or(0.0),
            "html": table.html_structure,
            "num_cells": table.cells.len(),
        })
    }).collect();

    let formulas: Vec<serde_json::Value> = result.formulas.iter().map(|f| {
        let pts: Vec<[f32; 2]> = f.bbox.points.iter()
            .map(|p| [p.x, p.y])
            .collect();
        serde_json::json!({
            "bbox": {
                "points": pts,
            },
            "latex": f.latex,
            "confidence": f.confidence,
        })
    }).collect();

    let text_regions: Vec<serde_json::Value> = if let Some(ref trs) = result.text_regions {
        trs.iter().map(|r: &oar_ocr::prelude::TextRegion| {
            let bbox_pts: Vec<Vec<f32>> = r.bounding_box.points.iter()
                .map(|p| vec![p.x, p.y])
                .collect();
            serde_json::json!({
                "box": bbox_pts,
                "text": r.text.as_ref().map(|t| t.to_string()),
                "text_confidence": r.confidence,
                "orientation_angle": r.orientation_angle,
            })
        }).collect()
    } else {
        vec![]
    };

    Ok(Json(serde_json::json!({
        "layout_regions": layout_regions,
        "tables": tables,
        "formulas": formulas,
        "text_regions": text_regions,
        "rotation": result.orientation_angle.unwrap_or(0.0),
    })))
}

pub async fn draw(
    State(_state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Response, String> {
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

    let data = image_data.ok_or("No image file provided")?;
    let analysis_json = analysis_result_json.ok_or("No analysis result provided")?;
    let analysis_data: serde_json::Value = serde_json::from_str(&analysis_json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    let mut img = load_image_from_bytes(&data)?;

    let layout_regions = analysis_data.get("layout_regions")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let colors: HashMap<&str, [u8; 3]> = [
        ("text", [0, 255, 0]),
        ("table", [255, 0, 255]),
        ("table_title", [200, 0, 200]),
        ("figure", [0, 0, 255]),
        ("figure_title", [100, 100, 255]),
        ("title", [255, 255, 0]),
        ("doc_title", [200, 200, 0]),
        ("content", [0, 200, 0]),
        ("header", [128, 128, 0]),
        ("footer", [0, 128, 128]),
    ].into_iter().collect();

    for region in layout_regions.iter() {
        let elem_type = region.get("type").and_then(|v| v.as_str()).unwrap_or("other");
        let color = colors.get(elem_type).copied().unwrap_or([255, 0, 0]);

        if let Some(bbox) = region.get("bbox") {
            let x0 = bbox.get("x0").and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
            let y0 = bbox.get("y0").and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
            let x1 = bbox.get("x1").and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;
            let y1 = bbox.get("y1").and_then(|v| v.as_f64()).unwrap_or(0.0) as i64;

            let pts: Vec<(u32, u32)> = vec![
                (x0.max(0) as u32, y0.max(0) as u32),
                (x1.max(0) as u32, y0.max(0) as u32),
                (x1.max(0) as u32, y1.max(0) as u32),
                (x0.max(0) as u32, y1.max(0) as u32),
            ];

            draw_polygon(&mut img, &pts, image::Rgb(color));
        }
    }

    let mut buf = std::io::Cursor::new(Vec::new());
    img.write_to(&mut buf, image::ImageFormat::Png)
        .map_err(|e| format!("Failed to encode PNG: {}", e))?;

    Ok((
        [(axum::http::header::CONTENT_TYPE, "image/png")],
        buf.into_inner(),
    ).into_response())
}

pub async fn markdown(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    let mut analysis_result_json: Option<String> = None;

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        if name == "analysis_result" {
            analysis_result_json = Some(field.text().await.map_err(|e| e.to_string())?);
        }
    }

    let analysis_json = analysis_result_json.ok_or("No analysis result provided")?;
    let analysis_data: serde_json::Value = serde_json::from_str(&analysis_json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    let _pipeline = build_structure_pipeline(&state)?;

    let layout_regions = analysis_data.get("layout_regions")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let tables = analysis_data.get("tables")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let formulas = analysis_data.get("formulas")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    let mut md_parts = Vec::new();

    for region in layout_regions.iter() {
        let elem_type = region.get("type").and_then(|v| v.as_str()).unwrap_or("other");
        let text = region.get("text").and_then(|v| v.as_str()).unwrap_or("");

        match elem_type {
            "doc_title" | "title" => {
                md_parts.push(format!("# {}\n\n", text.trim()));
            }
            "paragraph_title" => {
                md_parts.push(format!("## {}\n\n", text.trim()));
            }
            "text" | "content" | "abstract" => {
                if !text.trim().is_empty() {
                    md_parts.push(format!("{}\n\n", text.trim()));
                }
            }
            "image" => {
                md_parts.push("![image](...)\n\n".to_string());
            }
            _ => {}
        }
    }

    if !tables.is_empty() {
        for table in tables.iter() {
            if let Some(html) = table.get("html").and_then(|v| v.as_str()) {
                md_parts.push(format!("{}\n\n", html));
            }
        }
    }

    if !formulas.is_empty() {
        for formula in formulas.iter() {
            let latex = formula.get("latex").and_then(|v| v.as_str()).unwrap_or("");
            if !latex.is_empty() {
                md_parts.push(format!("$\n{}\n$\n\n", latex));
            }
        }
    }

    let markdown = md_parts.join("");
    Ok(Json(serde_json::json!({
        "markdown": markdown,
        "images": Vec::<serde_json::Value>::new()
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
