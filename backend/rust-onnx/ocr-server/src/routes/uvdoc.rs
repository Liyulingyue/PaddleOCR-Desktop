use axum::{
    extract::{Multipart, State},
    response::Json,
};
use bytes::Bytes;
use serde::Serialize;

use crate::AppState;

fn build_uvdoc_predictor(state: &AppState) -> Result<oar_ocr::predictors::DocumentRectificationPredictor, String> {
    let model_path = state.registry.get_model_path("uvdoc")
        .ok_or_else(|| "UVDoc model not downloaded".to_string())?;

    oar_ocr::predictors::DocumentRectificationPredictor::builder()
        .build(&model_path)
        .map_err(|e| format!("Failed to build UVDoc predictor: {}", e))
}

pub async fn unwarp(
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

    let predictor = build_uvdoc_predictor(&state)?;
    let result = predictor.predict(vec![img])
        .map_err(|e| format!("UVDoc failed: {}", e))?;

    let rectified = result.images.into_iter().next()
        .ok_or("No rectified image returned")?;

    let mut buf = std::io::Cursor::new(Vec::new());
    rectified.write_to(&mut buf, image::ImageFormat::Png)
        .map_err(|e| format!("Failed to encode image: {}", e))?;

    use base64::Engine;
    let b64 = base64::engine::general_purpose::STANDARD.encode(buf.into_inner());

    Ok(Json(serde_json::json!({
        "image": b64,
        "format": "png"
    })))
}

pub async fn load_model(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    let _predictor = build_uvdoc_predictor(&state)?;
    Ok(Json(serde_json::json!({
        "message": "UVDoc loaded",
        "loaded": true
    })))
}

pub async fn download_missing(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    state.registry.blocking_download("uvdoc")
        .map_err(|e| e.to_string())?;
    Ok(Json(serde_json::json!({
        "downloaded": true,
        "message": "UVDoc model ready"
    })))
}

pub async fn unload_model() -> Result<Json<serde_json::Value>, String> {
    Ok(Json(serde_json::json!({
        "message": "UVDoc unloaded",
        "loaded": false
    })))
}

#[derive(Debug, Serialize)]
pub struct ModelStatusResponse {
    pub loaded: bool,
}

pub async fn model_status() -> Json<ModelStatusResponse> {
    Json(ModelStatusResponse { loaded: false })
}

fn load_image_from_bytes(data: &[u8]) -> Result<image::RgbImage, String> {
    let img = image::load_from_memory(data)
        .map_err(|e| format!("Failed to load image: {}", e))?;
    Ok(img.to_rgb8())
}
