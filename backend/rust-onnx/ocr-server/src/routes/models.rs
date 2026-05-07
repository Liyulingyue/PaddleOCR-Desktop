use axum::{
    extract::{Path, State},
    Json,
};
use crate::AppState;
use serde::Serialize;

pub async fn list(State(state): State<AppState>) -> Json<Vec<ocr_lib::registry::ModelInfo>> {
    let models = state.registry.list_models();
    Json(models)
}

#[derive(Serialize)]
pub struct DownloadResponse {
    pub success: bool,
    pub message: String,
    pub path: Option<String>,
}

pub async fn download(
    State(state): State<AppState>,
    Path(model_name): Path<String>,
) -> Json<DownloadResponse> {
    match state.registry.download_model(&model_name).await {
        Ok(path) => Json(DownloadResponse {
            success: true,
            message: format!("{} downloaded successfully", model_name),
            path: Some(path.to_string_lossy().to_string()),
        }),
        Err(e) => Json(DownloadResponse {
            success: false,
            message: format!("Download failed: {}", e),
            path: None,
        }),
    }
}

#[derive(Serialize)]
pub struct DeleteResponse {
    pub success: bool,
    pub message: String,
}

pub async fn delete_model(
    State(state): State<AppState>,
    Path(model_name): Path<String>,
) -> Json<DeleteResponse> {
    match state.registry.delete_model(&model_name) {
        Ok(()) => Json(DeleteResponse {
            success: true,
            message: format!("{} deleted successfully", model_name),
        }),
        Err(e) => Json(DeleteResponse {
            success: false,
            message: format!("Delete failed: {}", e),
        }),
    }
}

#[derive(Debug, Serialize)]
pub struct BatchResult {
    pub model: String,
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct BatchResponse {
    pub results: Vec<BatchResult>,
}

pub async fn batch_download(
    State(state): State<AppState>,
    Json(model_names): Json<Vec<String>>,
) -> Json<BatchResponse> {
    let results: Vec<BatchResult> = model_names
        .iter()
        .map(|name| {
            match state.registry.blocking_download(name) {
                Ok(_) => BatchResult {
                    model: name.clone(),
                    success: true,
                    error: None,
                },
                Err(e) => BatchResult {
                    model: name.clone(),
                    success: false,
                    error: Some(e),
                },
            }
        })
        .collect();
    Json(BatchResponse { results })
}

pub async fn batch_delete(
    State(state): State<AppState>,
    Json(model_names): Json<Vec<String>>,
) -> Json<BatchResponse> {
    let results: Vec<BatchResult> = model_names
        .iter()
        .map(|name| {
            match state.registry.delete_model(name) {
                Ok(()) => BatchResult {
                    model: name.clone(),
                    success: true,
                    error: None,
                },
                Err(e) => BatchResult {
                    model: name.clone(),
                    success: false,
                    error: Some(e),
                },
            }
        })
        .collect();
    Json(BatchResponse { results })
}
