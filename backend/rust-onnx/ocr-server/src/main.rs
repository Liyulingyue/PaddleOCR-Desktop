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
        .route("/api/models/list", get(routes::models::list))
        .route("/api/models/download/{model_name}", post(routes::models::download))
        .route("/api/models/delete/{model_name}", axum::routing::delete(routes::models::delete_model))
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
