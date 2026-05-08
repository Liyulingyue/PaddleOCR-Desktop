use axum::{
    extract::{Multipart, State},
    response::{IntoResponse, Json, Response},
};
use bytes::Bytes;
use serde::Serialize;
use std::io::Cursor;

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
) -> Result<Response, (axum::http::StatusCode, Json<serde_json::Value>)> {
    let mut image_data: Option<Bytes> = None;

    while let Some(field) = multipart.next_field().await.map_err(|e| {
        (axum::http::StatusCode::BAD_REQUEST, Json(serde_json::json!({ "error": e.to_string() })))
    })? {
        let name = field.name().unwrap_or("").to_string();
        if name == "file" {
            image_data = Some(field.bytes().await.map_err(|e| {
                (axum::http::StatusCode::BAD_REQUEST, Json(serde_json::json!({ "error": e.to_string() })))
            })?);
        }
    }

    let data = image_data.ok_or_else(|| {
        (axum::http::StatusCode::BAD_REQUEST, Json(serde_json::json!({ "error": "No image file provided" })))
    })?;
    let img = load_image_from_bytes(&data).map_err(|e| {
        (axum::http::StatusCode::BAD_REQUEST, Json(serde_json::json!({ "error": e })))
    })?;
    let (orig_w, orig_h) = (img.width(), img.height());

    let start = std::time::Instant::now();
    let predictor = build_uvdoc_predictor(&state).map_err(|e| {
        (axum::http::StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({ "error": e })))
    })?;
    let result = predictor.predict(vec![img]).map_err(|e| {
        (axum::http::StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({ "error": format!("UVDoc failed: {}", e) })))
    })?;

    let rectified = result.images.into_iter().next().ok_or_else(|| {
        (axum::http::StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({ "error": "No rectified image returned" })))
    })?;

    let elapsed = start.elapsed().as_secs_f64();
    let (result_w, result_h) = (rectified.width(), rectified.height());

    let mut buf = Cursor::new(Vec::new());
    rectified.write_to(&mut buf, image::ImageFormat::Png).map_err(|e| {
        (axum::http::StatusCode::INTERNAL_SERVER_ERROR, Json(serde_json::json!({ "error": format!("Failed to encode image: {}", e) })))
    })?;

    let png_bytes = buf.into_inner();

    let header_elapsed = format!("{:.3}", elapsed);
    let header_orig_shape = format!("{},{}", orig_h, orig_w);
    let header_result_shape = format!("{},{}", result_h, result_w);

    Ok((
        [
            (axum::http::header::CONTENT_TYPE, "image/png"),
            ("X-Elapsed-Time".parse().unwrap(), header_elapsed.as_str()),
            ("X-Original-Shape".parse().unwrap(), header_orig_shape.as_str()),
            ("X-Result-Shape".parse().unwrap(), header_result_shape.as_str()),
        ],
        png_bytes,
    ).into_response())
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
