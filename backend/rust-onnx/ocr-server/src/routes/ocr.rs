use axum::{
    extract::{Multipart, State},
    response::{IntoResponse, Json, Response},
};
use bytes::Bytes;
use serde::{Deserialize, Serialize};
use std::io::Cursor;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct OcrTextRegion {
    pub bbox: Vec<Vec<f32>>,
    pub text: String,
    #[serde(rename = "text_confidence")]
    pub text_confidence: f32,
    #[serde(rename = "doc_rotation")]
    pub doc_rotation: f32,
    #[serde(rename = "doc_rotation_confidence")]
    pub doc_rotation_confidence: f32,
    #[serde(rename = "textline_rotation")]
    pub textline_rotation: f32,
    #[serde(rename = "textline_rotation_confidence")]
    pub textline_rotation_confidence: f32,
}

#[derive(Debug, Serialize)]
pub struct OcrResponse {
    pub results: Vec<OcrTextRegion>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct OcrParams {
    #[serde(rename = "det_db_thresh", default)]
    pub det_thresh: f32,
    #[serde(rename = "doc_cls_thresh", default)]
    pub doc_cls_thresh: f32,
    #[serde(rename = "use_doc_cls", default)]
    pub use_doc_cls: bool,
    #[serde(rename = "textline_cls_thresh", default)]
    pub textline_cls_thresh: f32,
    #[serde(rename = "use_textline_cls", default)]
    pub use_textline_cls: bool,
    #[serde(rename = "use_uvdoc", default)]
    pub use_uvdoc: bool,
    #[serde(rename = "merge_overlaps", default)]
    pub merge_overlaps: bool,
    #[serde(rename = "overlap_threshold", default)]
    pub overlap_threshold: f32,
}

impl Default for OcrParams {
    fn default() -> Self {
        Self {
            det_thresh: 0.3,
            doc_cls_thresh: 0.3,
            use_doc_cls: true,
            textline_cls_thresh: 0.3,
            use_textline_cls: true,
            use_uvdoc: false,
            merge_overlaps: false,
            overlap_threshold: 0.9,
        }
    }
}

pub async fn recognize(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<OcrResponse>, String> {
    let mut image_data: Option<Bytes> = None;

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        if name == "file" {
            image_data = Some(field.bytes().await.map_err(|e| e.to_string())?);
        }
    }

    let data = image_data.ok_or("No image file provided")?;
    let img = load_image_from_bytes(&data)?;

    let result = state.engine.predict(img).map_err(|e| e.to_string())?;

    let ocr_results: Vec<OcrTextRegion> = result.text_regions.iter()
        .filter(|r| r.has_text())
        .map(|r| {
            let pts: Vec<Vec<f32>> = r.bounding_box.points.iter()
                .map(|p| vec![p.x, p.y])
                .collect();
            let doc_angle = r.orientation_angle.unwrap_or(0.0);
            let rec_conf = r.confidence.unwrap_or(1.0);
            OcrTextRegion {
                bbox: pts,
                text: r.text.as_ref().map(|t| t.to_string()).unwrap_or_default(),
                text_confidence: rec_conf,
                doc_rotation: 0.0,
                doc_rotation_confidence: 0.0,
                textline_rotation: doc_angle,
                textline_rotation_confidence: 0.0,
            }
        })
        .collect();

    Ok(Json(OcrResponse { results: ocr_results }))
}

pub async fn ocr2text(
    Json(body): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, String> {
    let results = body.get("results")
        .and_then(|v| v.as_array())
        .ok_or("Invalid format: missing results array")?;

    let texts: Vec<&str> = results.iter()
        .filter_map(|r| r.get("text").and_then(|t| t.as_str()))
        .collect();

    let full_text = texts.join("\n");
    Ok(Json(serde_json::json!({ "text": full_text })))
}

pub async fn draw(
    State(_state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Response, String> {
    let mut image_data: Option<Bytes> = None;
    let mut ocr_result_json: Option<String> = None;
    let mut drop_score: f32 = 0.0;

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        match name.as_str() {
            "file" => {
                image_data = Some(field.bytes().await.map_err(|e| e.to_string())?);
            }
            "ocr_result" => {
                ocr_result_json = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            "drop_score" => {
                drop_score = field.text().await
                    .map_err(|e| e.to_string())?
                    .parse()
                    .unwrap_or(0.0);
            }
            _ => {}
        }
    }

    let data = image_data.ok_or("No image file provided")?;
    let mut img = load_image_from_bytes(&data)?;
    let (width, height) = img.dimensions();

    let ocr_json = ocr_result_json.ok_or("No OCR result provided")?;
    let ocr_data: serde_json::Value = serde_json::from_str(&ocr_json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    let results = ocr_data.get("results")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();

    for region in results.iter() {
        let conf = region.get("text_confidence")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0) as f32;
        if conf < drop_score {
            continue;
        }

        if let Some(box_pts) = region.get("bbox").and_then(|v| v.as_array()) {
            let pts: Vec<(u32, u32)> = box_pts.iter()
                .filter_map(|p| {
                    let arr = p.as_array()?;
                    let x = arr.first()?.as_f64()? as u32;
                    let y = arr.get(1)?.as_f64()? as u32;
                    Some((x.min(width.saturating_sub(1)), y.min(height.saturating_sub(1))))
                })
                .collect();

            if pts.len() >= 4 {
                draw_polygon(&mut img, &pts, image::Rgb([0u8, 255, 0]));
            }
        }
    }

    let mut buf = Cursor::new(Vec::new());
    img.write_to(&mut buf, image::ImageFormat::Png)
        .map_err(|e| format!("Failed to encode PNG: {}", e))?;

    Ok((
        [(axum::http::header::CONTENT_TYPE, "image/png")],
        buf.into_inner(),
    ).into_response())
}

#[derive(Debug, Serialize)]
pub struct ModelStatusResponse {
    pub loaded: bool,
    pub message: String,
    pub mode: &'static str,
    #[serde(rename = "use_gpu")]
    pub use_gpu: bool,
}

pub async fn model_status(
    State(state): State<AppState>,
) -> Json<ModelStatusResponse> {
    let loaded = state.engine.is_loaded();
    Json(ModelStatusResponse {
        loaded,
        message: if loaded {
            "OCR models loaded".to_string()
        } else {
            "OCR models not loaded".to_string()
        },
        mode: "pipeline",
        use_gpu: false,
    })
}

#[derive(Debug, Serialize)]
pub struct ModelOption {
    pub value: String,
    pub label: String,
    pub description: String,
}

#[derive(Debug, Serialize)]
pub struct OptionsResponse {
    pub options: serde_json::Value,
    pub defaults: serde_json::Value,
}

pub async fn options() -> Json<OptionsResponse> {
    let options = serde_json::json!({
        "ocr_det": [ModelOption {
            value: "pp-ocrv5_mobile_det".to_string(),
            label: "PP-OCRv5 Mobile 检测".to_string(),
            description: "轻量级文本检测模型".to_string(),
        }],
        "ocr_rec": [ModelOption {
            value: "pp-ocrv5_mobile_rec".to_string(),
            label: "PP-OCRv5 Mobile 识别".to_string(),
            description: "轻量级文本识别模型".to_string(),
        }],
    });

    let defaults = serde_json::json!({
        "ocr_det": "pp-ocrv5_mobile_det",
        "ocr_rec": "pp-ocrv5_mobile_rec",
    });

    Json(OptionsResponse { options, defaults })
}

pub async fn download_missing(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    state.registry.ensure_default_models().map_err(|e| e.to_string())?;
    Ok(Json(serde_json::json!({
        "message": "All models downloaded",
        "downloaded": true
    })))
}

pub async fn load(
    State(_state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    Err("Load not implemented - models loaded on first use".to_string())
}

pub async fn unload(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    state.engine.unload().map_err(|e| e.to_string())?;
    Ok(Json(serde_json::json!({
        "message": "OCR models unloaded",
        "loaded": false
    })))
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
