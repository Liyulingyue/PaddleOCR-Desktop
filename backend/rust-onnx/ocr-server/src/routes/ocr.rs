use axum::{
    extract::{Multipart, State},
    response::{IntoResponse, Json, Response},
};
use bytes::Bytes;
use ocr_lib::{ModelRegistry, OcrEngine};
use oar_ocr::prelude::TextRegion;
use serde::{Deserialize, Serialize};
use std::io::Cursor;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct OcrTextRegion {
    #[serde(rename = "box")]
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

#[derive(Debug, Serialize)]
pub struct OcrPageResponse {
    pub page: usize,
    pub results: Vec<OcrTextRegion>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct OcrParams {
    #[serde(rename = "det_db_thresh", default)]
    pub det_db_thresh: f32,
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
    #[serde(rename = "det_model", default)]
    pub det_model: Option<String>,
    #[serde(rename = "rec_model", default)]
    pub rec_model: Option<String>,
    #[serde(rename = "doc_cls_model", default)]
    pub doc_cls_model: Option<String>,
    #[serde(rename = "textline_cls_model", default)]
    pub textline_cls_model: Option<String>,
    #[serde(rename = "uvdoc_model", default)]
    pub uvdoc_model: Option<String>,
}

impl Default for OcrParams {
    fn default() -> Self {
        Self {
            det_db_thresh: 0.3,
            doc_cls_thresh: 0.9,
            use_doc_cls: true,
            textline_cls_thresh: 0.9,
            use_textline_cls: true,
            use_uvdoc: false,
            merge_overlaps: false,
            overlap_threshold: 0.9,
            det_model: None,
            rec_model: None,
            doc_cls_model: None,
            textline_cls_model: None,
            uvdoc_model: None,
        }
    }
}

fn format_text_region(r: &TextRegion) -> OcrTextRegion {
    let pts: Vec<Vec<f32>> = r.bounding_box.points.iter()
        .map(|p| vec![p.x, p.y])
        .collect();
    let doc_angle = r.orientation_angle.unwrap_or(0.0);
    let rec_conf = r.confidence.unwrap_or(1.0);
    OcrTextRegion {
        bbox: pts,
        text: r.text.as_ref().map(|t| t.to_string()).unwrap_or_default(),
        text_confidence: rec_conf,
        doc_rotation: doc_angle,
        doc_rotation_confidence: 0.0,
        textline_rotation: doc_angle,
        textline_rotation_confidence: 0.0,
    }
}

fn build_model_key(params: &OcrParams) -> String {
    let default_key = OcrEngine::default_model_key();
    let parts: Vec<&str> = default_key.split('|').collect();

    let det = params.det_model.as_deref()
        .filter(|s| !s.is_empty() && *s != "Default")
        .unwrap_or(parts[0]);
    let rec = params.rec_model.as_deref()
        .filter(|s| !s.is_empty() && *s != "Default")
        .unwrap_or(parts[1]);
    let doc_cls = params.doc_cls_model.as_deref()
        .filter(|s| !s.is_empty() && *s != "Default")
        .or(parts.get(2).copied());
    let textline_cls = params.textline_cls_model.as_deref()
        .filter(|s| !s.is_empty() && *s != "Default")
        .or(parts.get(3).copied());

    if let (Some(d), Some(t)) = (doc_cls, textline_cls) {
        format!("{}|{}|{}|{}", det, rec, d, t)
    } else {
        format!("{}|{}||", det, rec)
    }
}

pub async fn recognize(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Response, String> {
    let mut image_data: Option<Bytes> = None;
    let mut params = OcrParams::default();
    let mut is_pdf = false;

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        match name.as_str() {
            "file" => {
                image_data = Some(field.bytes().await.map_err(|e| e.to_string())?);
            }
            "det_db_thresh" => {
                params.det_db_thresh = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(0.3);
            }
            "doc_cls_thresh" => {
                params.doc_cls_thresh = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(0.9);
            }
            "use_doc_cls" => {
                params.use_doc_cls = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(true);
            }
            "textline_cls_thresh" => {
                params.textline_cls_thresh = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(0.9);
            }
            "use_textline_cls" => {
                params.use_textline_cls = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(true);
            }
            "use_uvdoc" => {
                params.use_uvdoc = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(false);
            }
            "merge_overlaps" => {
                params.merge_overlaps = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(false);
            }
            "overlap_threshold" => {
                params.overlap_threshold = field.text().await.map_err(|e| e.to_string())?.parse().unwrap_or(0.9);
            }
            "det_model" => {
                params.det_model = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            "rec_model" => {
                params.rec_model = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            "doc_cls_model" => {
                params.doc_cls_model = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            "textline_cls_model" => {
                params.textline_cls_model = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            "uvdoc_model" => {
                params.uvdoc_model = Some(field.text().await.map_err(|e| e.to_string())?);
            }
            _ => {}
        }
    }

    let data = image_data.ok_or("No image file provided")?;

    if data.len() >= 5 && &data[0..5] == b"%PDF-" {
        is_pdf = true;
    }

    let model_key = build_model_key(&params);

    if is_pdf {
        let images = pdf_bytes_to_images(&data)?;
        if images.is_empty() {
            return Err("PDF has no pages".to_string());
        }

        let mut all_pages = Vec::new();
        for (page_idx, img) in images.iter().enumerate() {
            let result = state.engine.predict(img.clone(), &model_key).map_err(|e| e.to_string())?;
            let regions: Vec<OcrTextRegion> = result.text_regions.iter()
                .filter(|r| r.has_text())
                .map(format_text_region)
                .collect();
            all_pages.push(OcrPageResponse {
                page: page_idx + 1,
                results: regions,
            });
        }

        Ok(Json(serde_json::json!({ "results": all_pages })).into_response())
    } else {
        let img = load_image_from_bytes(&data)?;
        let result = state.engine.predict(img, &model_key).map_err(|e| e.to_string())?;
        let ocr_results: Vec<OcrTextRegion> = result.text_regions.iter()
            .filter(|r| r.has_text())
            .map(format_text_region)
            .collect();
        Ok(Json(OcrResponse { results: ocr_results }).into_response())
    }
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
    let mut max_pages: usize = 2;

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
    let ocr_json = ocr_result_json.ok_or("No OCR result provided")?;
    let ocr_data: serde_json::Value = serde_json::from_str(&ocr_json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    if data.len() >= 5 && &data[0..5] == b"%PDF-" {
        let images = pdf_bytes_to_images(&data)?;
        if images.is_empty() {
            return Err("PDF has no pages".to_string());
        }

        let total_pages = images.len();
        let limited_images: Vec<_> = images.into_iter().take(max_pages).collect();
        let results = ocr_data.get("results")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let mut page_images = Vec::new();
        for (page_idx, img) in limited_images.iter().enumerate() {
            let page_num = page_idx + 1;
            let mut img = img.clone();

            let page_results = find_page_results(&results, page_num);
            let doc_rotation = extract_doc_rotation(&page_results);

            if doc_rotation != 0.0 {
                img = rotate_image(&img, -doc_rotation);
            }

            draw_ocr_on_image(&mut img, &page_results, drop_score);

            let buf = encode_image_as_base64(&img)?;
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
        let mut img = load_image_from_bytes(&data)?;
        let results = ocr_data.get("results")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let doc_rotation = extract_doc_rotation(&results);
        if doc_rotation != 0.0 {
            img = rotate_image(&img, -doc_rotation);
        }

        draw_ocr_on_image(&mut img, &results, drop_score);

        let mut buf = Cursor::new(Vec::new());
        img.write_to(&mut buf, image::ImageFormat::Png)
            .map_err(|e| format!("Failed to encode PNG: {}", e))?;

        return Ok((
            [(axum::http::header::CONTENT_TYPE, "image/png")],
            buf.into_inner(),
        ).into_response());
    }
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
    let (loaded, _) = state.engine.check_all_models();
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
    let models = ModelRegistry::all_models();

    let det_models: Vec<ModelOption> = models.iter()
        .filter(|(name, _)| name.contains("_det"))
        .filter(|(name, _)| !name.contains("seal") && !name.contains("table") && !name.contains("layout"))
        .map(|(name, info)| ModelOption {
            value: name.to_string(),
            label: info.label.to_string(),
            description: info.description.to_string(),
        })
        .collect();

    let rec_models: Vec<ModelOption> = models.iter()
        .filter(|(name, _)| name.contains("_rec"))
        .map(|(name, info)| ModelOption {
            value: name.to_string(),
            label: info.label.to_string(),
            description: info.description.to_string(),
        })
        .collect();

    let doc_cls_models: Vec<ModelOption> = models.iter()
        .filter(|(name, _)| name.contains("_doc_ori"))
        .map(|(name, info)| ModelOption {
            value: name.to_string(),
            label: info.label.to_string(),
            description: info.description.to_string(),
        })
        .collect();

    let textline_cls_models: Vec<ModelOption> = models.iter()
        .filter(|(name, _)| name.contains("_textline_ori"))
        .map(|(name, info)| ModelOption {
            value: name.to_string(),
            label: info.label.to_string(),
            description: info.description.to_string(),
        })
        .collect();

    let uvdoc_models: Vec<ModelOption> = models.iter()
        .filter(|(name, _)| name.contains("uvdoc"))
        .map(|(name, info)| ModelOption {
            value: name.to_string(),
            label: info.label.to_string(),
            description: info.description.to_string(),
        })
        .collect();

    let options = serde_json::json!({
        "ocr_det": det_models,
        "ocr_rec": rec_models,
        "doc_cls": doc_cls_models,
        "textline_cls": textline_cls_models,
        "uvdoc": uvdoc_models,
    });

    let defaults = serde_json::json!({
        "ocr_det": ModelRegistry::default_det_model(),
        "ocr_rec": ModelRegistry::default_rec_model(),
        "doc_cls": ModelRegistry::default_doc_cls_model(),
        "textline_cls": ModelRegistry::default_textline_cls_model(),
        "uvdoc": null,
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

fn rotate_image(img: &image::RgbImage, angle: f32) -> image::RgbImage {
    use std::f32::consts::PI;
    let rad = -angle as f64 * PI as f64 / 180.0;
    let cos = rad.cos();
    let sin = rad.sin();

    let (w, h) = img.dimensions();
    let cos_a = rad.cos() as f32;
    let sin_a = rad.sin() as f32;

    let new_w = ((w as f32 * cos_a.abs()) + (h as f32 * sin_a.abs())).ceil() as u32;
    let new_h = ((w as f32 * sin_a.abs()) + (h as f32 * cos_a.abs())).ceil() as u32;

    let mut result = image::RgbImage::new(new_w, new_h);
    let cx = w as f32 / 2.0;
    let cy = h as f32 / 2.0;
    let ncx = new_w as f32 / 2.0;
    let ncy = new_h as f32 / 2.0;

    for y in 0..new_h {
        for x in 0..new_w {
            let dx = x as f64 - ncx as f64;
            let dy = y as f64 - ncy as f64;
            let sx = (dx * cos - dy * sin + cx as f64) as i64;
            let sy = (dx * sin + dy * cos + cy as f64) as i64;
            if sx >= 0 && (sx as u32) < w && sy >= 0 && (sy as u32) < h {
                result.put_pixel(x, y, *img.get_pixel(sx as u32, sy as u32));
            }
        }
    }

    result
}

fn extract_doc_rotation(results: &[serde_json::Value]) -> f32 {
    if let Some(first) = results.first() {
        first.get("doc_rotation")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0) as f32
    } else {
        0.0
    }
}

fn find_page_results(results: &[serde_json::Value], page_num: usize) -> Vec<serde_json::Value> {
    if results.is_empty() {
        return vec![];
    }
    if let Some(first) = results.first() {
        if first.get("page").is_some() {
            return results.iter()
                .filter(|r| r.get("page").and_then(|v| v.as_u64()).map(|n| n as usize) == Some(page_num))
                .flat_map(|r| r.get("results").and_then(|v| v.as_array()).cloned().unwrap_or_default())
                .collect();
        }
    }
    if page_num == 1 {
        return results.to_vec();
    }
    vec![]
}

fn draw_ocr_on_image(img: &mut image::RgbImage, results: &[serde_json::Value], drop_score: f32) {
    let (width, height) = img.dimensions();

    for region in results.iter() {
        let conf = region.get("text_confidence")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0) as f32;
        if conf < drop_score {
            continue;
        }

        let box_pts = region.get("box")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let pts: Vec<(u32, u32)> = box_pts.iter()
            .filter_map(|p| {
                let arr = p.as_array()?;
                let x = arr.first()?.as_f64()? as u32;
                let y = arr.get(1)?.as_f64()? as u32;
                Some((x.min(width.saturating_sub(1)), y.min(height.saturating_sub(1))))
            })
            .collect();

        if pts.len() >= 4 {
            draw_polygon(img, &pts, image::Rgb([0u8, 255, 0]));
        }
    }
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

fn encode_image_as_base64(img: &image::RgbImage) -> Result<String, String> {
    let mut buf = Cursor::new(Vec::new());
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
