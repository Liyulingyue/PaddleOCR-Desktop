use axum::{
    extract::{Path, State},
    Json,
};
use crate::AppState;
use serde::Serialize;

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
