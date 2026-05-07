use axum::{
    extract::{Multipart, State},
    response::Json,
};
use serde::{Deserialize, Serialize};
use serde_json;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct ModelOption {
    pub value: String,
    pub label: String,
    pub description: String,
}

#[derive(Debug, Serialize)]
pub struct OptionsResponse {
    pub options: Vec<ModelOption>,
}

pub async fn model_options() -> Json<OptionsResponse> {
    Json(OptionsResponse {
        options: vec![
            ModelOption {
                value: "PP-FormulaNet_plus-M-ONNX".to_string(),
                label: "PP-FormulaNet plus-M (推荐)".to_string(),
                description: "平衡精度与速度，适合大多数场景".to_string(),
            },
            ModelOption {
                value: "PP-FormulaNet_plus-S-ONNX".to_string(),
                label: "PP-FormulaNet plus-S (快速)".to_string(),
                description: "体积最小，速度最快，轻量优先".to_string(),
            },
            ModelOption {
                value: "PP-FormulaNet_plus-L-ONNX".to_string(),
                label: "PP-FormulaNet plus-L (高精度)".to_string(),
                description: "最高精度，体积较大，适合复杂公式".to_string(),
            },
            ModelOption {
                value: "PP-FormulaNet-L-ONNX".to_string(),
                label: "PP-FormulaNet L (高精度)".to_string(),
                description: "高精度非Plus版本，需768×768输入".to_string(),
            },
        ],
    })
}

pub async fn recognize(
    State(_state): State<AppState>,
    _multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    Err("Formula recognition not implemented in Rust backend".to_string())
}

pub async fn load_model(
    State(_state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    Err("Formula recognition not implemented in Rust backend".to_string())
}

pub async fn download_missing(
    State(_state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    Err("Formula recognition not implemented in Rust backend".to_string())
}

pub async fn unload_model() -> Result<Json<serde_json::Value>, String> {
    Err("Formula recognition not implemented in Rust backend".to_string())
}

#[derive(Debug, Deserialize)]
pub struct ModelStatusQuery {
    #[serde(rename = "use_gpu", default)]
    use_gpu: bool,
}

#[derive(Debug, Serialize)]
pub struct ModelStatusResponse {
    pub loaded: bool,
}

pub async fn model_status() -> Json<ModelStatusResponse> {
    Json(ModelStatusResponse { loaded: false })
}
