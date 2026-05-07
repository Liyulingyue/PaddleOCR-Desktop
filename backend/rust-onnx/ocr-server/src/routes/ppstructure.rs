use axum::{
    extract::{Multipart, State},
    response::{IntoResponse, Json, Response},
};
use serde::{Deserialize, Serialize};
use serde_json;

use crate::AppState;

#[derive(Debug, Serialize)]
pub struct StructureResponse {
    #[serde(rename = "layout_regions")]
    pub layout_regions: Vec<serde_json::Value>,
    pub rotation: i32,
}

pub async fn analyze(
    State(_state): State<AppState>,
    _multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    Err("PP-StructureV3 not implemented in Rust backend".to_string())
}

pub async fn draw(
    State(_state): State<AppState>,
    _multipart: Multipart,
) -> Result<Response, String> {
    Err("PP-StructureV3 draw not implemented in Rust backend".to_string())
}

pub async fn markdown(
    State(_state): State<AppState>,
    _multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    Err("PP-StructureV3 markdown not implemented in Rust backend".to_string())
}

#[derive(Debug, Serialize)]
pub struct ModelStatusResponse {
    pub loaded: bool,
    pub message: String,
    pub mode: String,
}

pub async fn model_status() -> Json<ModelStatusResponse> {
    Json(ModelStatusResponse {
        loaded: false,
        message: "PP-StructureV3 not implemented in Rust backend".to_string(),
        mode: "pp-structure-v3".to_string(),
    })
}

pub async fn load_model(
    State(_state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    Err("PP-StructureV3 not implemented in Rust backend".to_string())
}

pub async fn download_missing(
    State(_state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    Err("PP-StructureV3 not implemented in Rust backend".to_string())
}

pub async fn unload_model() -> Result<Json<serde_json::Value>, String> {
    Err("PP-StructureV3 not implemented in Rust backend".to_string())
}

#[derive(Debug, Serialize)]
pub struct OptionsResponse {
    pub options: serde_json::Value,
    pub defaults: serde_json::Value,
}

pub async fn options() -> Json<OptionsResponse> {
    let options = serde_json::json!({
        "layout_det": [{
            "value": "PP-DocLayout-L-ONNX",
            "label": "PP-DocLayout L (标准精度)",
            "description": "标准精度的文档布局检测模型"
        }],
        "ocr_det": [{
            "value": "PP-OCRv5_mobile_det-ONNX",
            "label": "PP-OCRv5 Mobile 检测",
            "description": "轻量级文本检测模型"
        }],
        "ocr_rec": [{
            "value": "PP-OCRv5_mobile_rec-ONNX",
            "label": "PP-OCRv5 Mobile 识别",
            "description": "轻量级文本识别模型"
        }],
        "doc_cls": [{
            "value": "PP-LCNet_x1_0_doc_ori-ONNX",
            "label": "PP-LCNet x1.0 文档方向检测",
            "description": "标准尺寸的方向检测模型"
        }],
        "textline_cls": [{
            "value": "PP-LCNet_x1_0_textline_ori-ONNX",
            "label": "PP-LCNet x1.0 文本行方向检测",
            "description": "标准尺寸的方向检测模型"
        }],
        "formula_rec": [{
            "value": "PP-FormulaNet_plus-M-ONNX",
            "label": "PP-FormulaNet plus-M (推荐)",
            "description": "高精度公式识别模型"
        }],
        "uvdoc": [{
            "value": "UVDoc-ONNX",
            "label": "UVDoc 文档处理",
            "description": "UV文档处理模型"
        }]
    });

    let defaults = serde_json::json!({
        "layout_det": "PP-DocLayout-L-ONNX",
        "ocr_det": "PP-OCRv5_mobile_det-ONNX",
        "ocr_rec": "PP-OCRv5_mobile_rec-ONNX",
        "doc_cls": "PP-LCNet_x1_0_doc_ori-ONNX",
        "textline_cls": "PP-LCNet_x1_0_textline_ori-ONNX",
        "formula_rec": "PP-FormulaNet_plus-M-ONNX",
        "uvdoc": "UVDoc-ONNX"
    });

    Json(OptionsResponse { options, defaults })
}
