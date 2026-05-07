use std::net::SocketAddr;
use std::path::PathBuf;
use axum::{
    routing::{get, post},
    Router,
};
use tower_http::cors::{CorsLayer, Any};

mod routes;

#[derive(Clone)]
pub struct AppState {
    pub engine: ocr_lib::OcrEngine,
    pub registry: ocr_lib::ModelRegistry,
}

fn get_models_dir() -> PathBuf {
    dirs::data_local_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("oar-ocr")
        .join("models")
}

#[tokio::main]
async fn main() {
    let models_dir = get_models_dir();
    std::fs::create_dir_all(&models_dir).ok();

    let engine = ocr_lib::OcrEngine::new(models_dir.clone());
    let registry = ocr_lib::ModelRegistry::new(models_dir.clone());

    let state = AppState { engine, registry };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/api/health/", get(routes::health::health))
        .route("/api/ocr/", post(routes::ocr::recognize))
        .route("/api/ocr/draw", post(routes::ocr::draw))
        .route("/api/ocr/ocr2text", post(routes::ocr::ocr2text))
        .route("/api/ocr/load", post(routes::ocr::load))
        .route("/api/ocr/unload", post(routes::ocr::unload))
        .route("/api/ocr/model_status", get(routes::ocr::model_status))
        .route("/api/ocr/options", get(routes::ocr::options))
        .route("/api/ocr/download_missing", post(routes::ocr::download_missing))
        .route("/api/ppstructure/", post(routes::ppstructure::analyze))
        .route("/api/ppstructure/draw", post(routes::ppstructure::draw))
        .route("/api/ppstructure/markdown", post(routes::ppstructure::markdown))
        .route("/api/ppstructure/model_status", get(routes::ppstructure::model_status))
        .route("/api/ppstructure/load", post(routes::ppstructure::load_model))
        .route("/api/ppstructure/unload", post(routes::ppstructure::unload_model))
        .route("/api/ppstructure/options", get(routes::ppstructure::options))
        .route("/api/ppstructure/download_missing", post(routes::ppstructure::download_missing))
        .route("/api/formula/recognize/model_options", get(routes::formula::model_options))
        .route("/api/formula/recognize", post(routes::formula::recognize))
        .route("/api/formula/recognize/load", post(routes::formula::load_model))
        .route("/api/formula/recognize/unload", post(routes::formula::unload_model))
        .route("/api/formula/recognize/model_status", get(routes::formula::model_status))
        .route("/api/formula/recognize/download_missing", post(routes::formula::download_missing))
        .route("/api/uvdoc/unwarp", post(routes::uvdoc::unwarp))
        .route("/api/uvdoc/unwarp/load", post(routes::uvdoc::load_model))
        .route("/api/uvdoc/unwarp/unload", post(routes::uvdoc::unload_model))
        .route("/api/uvdoc/unwarp/model_status", get(routes::uvdoc::model_status))
        .route("/api/uvdoc/unwarp/download_missing", post(routes::uvdoc::download_missing))
        .route("/api/models/list", get(routes::models::list))
        .route("/api/models/download/{model_name}", post(routes::models::download))
        .route("/api/models/delete/{model_name}", axum::routing::delete(routes::models::delete_model))
        .route("/api/models/batch-download", post(routes::models::batch_download))
        .route("/api/models/batch-delete", axum::routing::delete(routes::models::batch_delete))
        .layer(cors)
        .with_state(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], 8000));
    let listener = tokio::net::TcpListener::bind(addr).await.expect("Failed to bind");
    let port = listener.local_addr().unwrap().port();

    println!("[INFO] Starting OCR backend on port {}", port);
    println!("[PORT] Backend port allocated: {}", port);
    eprintln!("[PORT] Backend port allocated: {}", port);
    eprintln!("[INFO] Backend port allocated: {}", port);

    axum::serve(listener, app).await.expect("Server error");
}
