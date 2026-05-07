use axum::{
    extract::{Multipart, State},
    response::Json,
};
use serde::{Deserialize, Serialize};
use serde_json;

use crate::AppState;

pub async fn unwarp(
    State(_state): State<AppState>,
    _multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    Err("UVDoc not implemented in Rust backend".to_string())
}

pub async fn load_model(
    State(_state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    Err("UVDoc not implemented in Rust backend".to_string())
}

pub async fn download_missing(
    State(_state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    Err("UVDoc not implemented in Rust backend".to_string())
}

pub async fn unload_model() -> Result<Json<serde_json::Value>, String> {
    Err("UVDoc not implemented in Rust backend".to_string())
}

#[derive(Debug, Serialize)]
pub struct ModelStatusResponse {
    pub loaded: bool,
}

pub async fn model_status() -> Json<ModelStatusResponse> {
    Json(ModelStatusResponse { loaded: false })
}
