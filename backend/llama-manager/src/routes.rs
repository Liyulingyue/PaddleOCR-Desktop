use axum::{
    extract::{Query, State, Json},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

use crate::error::LlamaManagerError;
use crate::models::{discover_models, format_size};
use crate::server::{LlamaServerConfig, LlamaServerManager};

#[derive(Clone)]
pub struct AppState {
    pub manager: Arc<LlamaServerManager>,
    pub models_dir: Arc<parking_lot::RwLock<std::path::PathBuf>>,
    pub manager_port: u16,
}

#[derive(Serialize)]
pub struct ServerUrlResponse {
    pub url: String,
}

#[derive(Serialize)]
pub struct StatusResponse {
    pub running: bool,
    pub server_url: Option<String>,
    pub pid: Option<u32>,
    pub model_name: Option<String>,
    pub manager_url: String,
}

#[derive(Deserialize)]
pub struct StartParams {
    pub model_path: Option<String>,
    pub model_name: Option<String>,
    pub mmproj_path: Option<String>,
    pub host: Option<String>,
    pub port: Option<u16>,
    pub ctx_size: Option<u32>,
    pub n_gpu_layers: Option<i32>,
    pub n_threads: Option<u32>,
    pub batch_size: Option<u32>,
    pub flash_attention: Option<bool>,
    pub additional_args: Option<String>,
}

#[derive(Serialize)]
pub struct ModelsResponse {
    pub models: Vec<ModelInfo>,
}

#[derive(Serialize)]
pub struct ModelInfo {
    pub name: String,
    pub path: String,
    pub size: String,
    pub has_mmproj: bool,
}

impl IntoResponse for LlamaManagerError {
    fn into_response(self) -> Response {
        let status = match &self {
            LlamaManagerError::NotRunning => StatusCode::SERVICE_UNAVAILABLE,
            LlamaManagerError::AlreadyRunning(_) => StatusCode::CONFLICT,
            LlamaManagerError::ModelNotFound(_) => StatusCode::NOT_FOUND,
            LlamaManagerError::ConfigError(_) => StatusCode::BAD_REQUEST,
            _ => StatusCode::INTERNAL_SERVER_ERROR,
        };
        (status, Json(serde_json::json!({ "error": self.to_string() }))).into_response()
    }
}

pub async fn health() -> impl IntoResponse {
    Json(serde_json::json!({ "status": "ok" }))
}

pub async fn start_server(
    State(state): State<AppState>,
    Query(params): Query<StartParams>,
) -> Result<Json<ServerUrlResponse>, LlamaManagerError> {
    let config = if let Some(ref model_path) = params.model_path {
        let model_path = std::path::PathBuf::from(model_path);
        let mmproj = params.mmproj_path.map(std::path::PathBuf::from);
        LlamaServerConfig {
            model_path,
            mmproj_path: mmproj,
            host: params.host.unwrap_or_else(|| "127.0.0.1".to_string()),
            port: params.port.unwrap_or(8080),
            ctx_size: params.ctx_size.unwrap_or(8192),
            n_gpu_layers: params.n_gpu_layers,
            n_threads: params.n_threads,
            batch_size: params.batch_size,
            flash_attention: params.flash_attention.unwrap_or(true),
            additional_args: params
                .additional_args
                .as_ref()
                .map(|s| s.split_whitespace().map(String::from).collect())
                .unwrap_or_default(),
        }
    } else if let Some(ref model_name) = params.model_name {
        let models_dir = state.models_dir.read();
        let model = crate::models::find_model(&models_dir, model_name)?;
        LlamaServerConfig::from_model(&model, params.port.unwrap_or(8080))
    } else {
        return Err(LlamaManagerError::ConfigError(
            "Either model_path or model_name must be provided".to_string(),
        ));
    };

    let url = state.manager.start(config).await?;
    Ok(Json(ServerUrlResponse { url }))
}

pub async fn stop_server(
    State(state): State<AppState>,
) -> Result<impl IntoResponse, LlamaManagerError> {
    state.manager.stop().await?;
    Ok(Json(serde_json::json!({ "status": "stopped" })))
}

pub async fn get_status(
    State(state): State<AppState>,
) -> Result<Json<StatusResponse>, LlamaManagerError> {
    let status = state.manager.get_status().await;
    let manager_url = format!("http://127.0.0.1:{}", state.manager_port);
    Ok(Json(StatusResponse {
        running: status.running,
        server_url: status.server_url,
        pid: status.pid,
        model_name: status.model_name,
        manager_url,
    }))
}

pub async fn get_models(
    State(state): State<AppState>,
) -> Result<Json<ModelsResponse>, LlamaManagerError> {
    let models_dir = state.models_dir.read();
    let models = discover_models(&models_dir);
    let model_infos: Vec<ModelInfo> = models
        .into_iter()
        .map(|m| ModelInfo {
            name: m.name,
            path: m.path.to_string_lossy().to_string(),
            size: format_size(m.size_bytes),
            has_mmproj: m.has_mmproj,
        })
        .collect();
    Ok(Json(ModelsResponse { models: model_infos }))
}

pub async fn get_manager_url(
    State(state): State<AppState>,
) -> impl IntoResponse {
    let url = format!("http://127.0.0.1:{}", state.manager_port);
    Json(serde_json::json!({ "url": url }))
}

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/start", post(start_server))
        .route("/stop", post(stop_server))
        .route("/status", get(get_status))
        .route("/models", get(get_models))
        .route("/manager_url", get(get_manager_url))
        .with_state(state)
}
