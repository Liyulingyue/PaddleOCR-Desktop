use axum::{
    extract::{Multipart, State},
    response::Json,
};
use bytes::Bytes;
use ocr_lib::ModelRegistry;
use serde::Serialize;
use std::time::Instant;

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
    let options = vec![
        ModelOption {
            value: "latex_ocr_rec".to_string(),
            label: "LaTeX OCR (推荐)".to_string(),
            description: "通用公式识别模型，使用 UniMERNet tokenizer".to_string(),
        },
        ModelOption {
            value: "pp-formulanet_plus-m".to_string(),
            label: "PP-FormulaNet Plus M".to_string(),
            description: "平衡精度与速度，适合大多数场景".to_string(),
        },
        ModelOption {
            value: "pp-formulanet_plus-s".to_string(),
            label: "PP-FormulaNet Plus S (快速)".to_string(),
            description: "体积最小，速度最快，轻量优先".to_string(),
        },
        ModelOption {
            value: "pp-formulanet_plus-l".to_string(),
            label: "PP-FormulaNet Plus L (高精度)".to_string(),
            description: "最高精度，体积较大，适合复杂公式".to_string(),
        },
        ModelOption {
            value: "pp-formulanet-l".to_string(),
            label: "PP-FormulaNet L (高精度)".to_string(),
            description: "高精度非Plus版本".to_string(),
        },
        ModelOption {
            value: "pp-formulanet-s".to_string(),
            label: "PP-FormulaNet S".to_string(),
            description: "轻量级公式识别".to_string(),
        },
    ];
    Json(OptionsResponse { options })
}

fn build_formula_predictor(state: &AppState, model_name: &str) -> Result<oar_ocr::predictors::FormulaRecognitionPredictor, String> {
    let _models = ModelRegistry::all_models();

    let model_path = state.registry.get_model_path(model_name)
        .ok_or_else(|| format!("Model not downloaded: {}", model_name))?;

    let tokenizer_name = if model_name == "latex_ocr_rec" { "unimernet_tokenizer" } else { "unimernet_tokenizer" };
    let tokenizer_path = state.registry.get_model_path(tokenizer_name)
        .ok_or_else(|| format!("Tokenizer not downloaded: {}", tokenizer_name))?;

    oar_ocr::predictors::FormulaRecognitionPredictor::builder()
        .model_name(model_name)
        .tokenizer_path(&tokenizer_path)
        .score_threshold(0.0)
        .build(&model_path)
        .map_err(|e| format!("Failed to build formula predictor: {}", e))
}

pub async fn recognize(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    let mut image_data: Option<Bytes> = None;
    let mut model_name = "latex_ocr_rec".to_string();

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        match name.as_str() {
            "file" => {
                image_data = Some(field.bytes().await.map_err(|e| e.to_string())?);
            }
            "model" => {
                model_name = field.text().await.map_err(|e| e.to_string())?;
            }
            _ => {}
        }
    }

    let data = image_data.ok_or("No image file provided")?;
    let img = load_image_from_bytes(&data)?;

    let predictor = build_formula_predictor(&state, &model_name)?;
    let start = Instant::now();
    let result = predictor.predict(vec![img])
        .map_err(|e| format!("Formula recognition failed: {}", e))?;
    let elapsed = start.elapsed().as_secs_f64() * 1000.0;

    let formula = result.formulas.first().cloned().unwrap_or_default();

    Ok(Json(serde_json::json!({
        "latex": formula,
        "elapsed": elapsed,
        "input_size": [384, 384],
    })))
}

pub async fn load_model(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Json<serde_json::Value>, String> {
    let mut model_name = "latex_ocr_rec".to_string();

    while let Some(field) = multipart.next_field().await.map_err(|e| e.to_string())? {
        let name = field.name().unwrap_or("").to_string();
        if name == "model" {
            model_name = field.text().await.map_err(|e| e.to_string())?;
        }
    }

    let _predictor = build_formula_predictor(&state, &model_name)?;
    Ok(Json(serde_json::json!({
        "message": format!("{} loaded", model_name),
        "loaded": true
    })))
}

pub async fn download_missing(
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, String> {
    state.registry.blocking_download("latex_ocr_rec")
        .map_err(|e| e.to_string())?;
    state.registry.blocking_download("unimernet_tokenizer")
        .map_err(|e| e.to_string())?;
    Ok(Json(serde_json::json!({
        "downloaded": true,
        "message": "Formula model files ready"
    })))
}

pub async fn unload_model() -> Result<Json<serde_json::Value>, String> {
    Ok(Json(serde_json::json!({
        "message": "Formula model unloaded",
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
