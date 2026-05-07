use axum::{
    extract::{Path, State},
    Json,
};
use crate::AppState;
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
pub struct ListResponse {
    pub models: Vec<ocr_lib::registry::ModelListEntry>,
}

pub async fn list(State(state): State<AppState>) -> Json<ListResponse> {
    let models = state.registry.list_models();
    Json(ListResponse { models })
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
    match state.registry.download_model(&model_name) {
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

#[derive(Debug, Deserialize)]
pub struct BatchRequest {
    pub model_names: Vec<String>,
}

#[derive(Debug, Serialize)]
pub struct BatchDownloadResult {
    pub model: String,
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct BatchDownloadResponse {
    pub results: Vec<BatchDownloadResult>,
}

pub async fn batch_download(
    State(state): State<AppState>,
    Json(req): Json<BatchRequest>,
) -> Json<BatchDownloadResponse> {
    let results: Vec<BatchDownloadResult> = req.model_names.iter().map(|name| {
        match state.registry.download_model(name) {
            Ok(_) => BatchDownloadResult {
                model: name.clone(),
                success: true,
                error: None,
            },
            Err(e) => BatchDownloadResult {
                model: name.clone(),
                success: false,
                error: Some(e),
            },
        }
    }).collect();
    Json(BatchDownloadResponse { results })
}

#[derive(Debug, Serialize)]
pub struct BatchDeleteResult {
    pub model: String,
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct BatchDeleteResponse {
    pub results: Vec<BatchDeleteResult>,
}

pub async fn batch_delete(
    State(state): State<AppState>,
    Json(req): Json<BatchRequest>,
) -> Json<BatchDeleteResponse> {
    let results: Vec<BatchDeleteResult> = req.model_names.iter().map(|name| {
        match state.registry.delete_model(name) {
            Ok(()) => BatchDeleteResult {
                model: name.clone(),
                success: true,
                error: None,
            },
            Err(e) => BatchDeleteResult {
                model: name.clone(),
                success: false,
                error: Some(e),
            },
        }
    }).collect();
    Json(BatchDeleteResponse { results })
}
