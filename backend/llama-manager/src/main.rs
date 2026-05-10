use std::path::PathBuf;
use std::sync::Arc;

use llama_manager::{AppState, LlamaServerManager};
use tower_http::cors::{Any, CorsLayer};
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

fn get_default_models_dir() -> PathBuf {
    if let Some(data_dir) = dirs::data_local_dir() {
        let base = data_dir.parent().unwrap_or(&data_dir);
        let project_dir = base.join("PaddleOCR-Desktop");
        if project_dir.exists() {
            return project_dir.join("models").join("llama");
        }
    }
    PathBuf::from("models")
}

#[tokio::main]
async fn main() {
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(EnvFilter::from_default_env().add_directive("llama_manager=info".parse().unwrap()))
        .init();

    let manager_port: u16 = std::env::var("LLAMA_MANAGER_PORT")
        .unwrap_or_else(|_| "8081".to_string())
        .parse()
        .unwrap_or(8081);

    let models_dir: PathBuf = std::env::var("MODELS_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| get_default_models_dir());

    if !models_dir.exists() {
        tracing::warn!(
            "Models directory does not exist: {:?}. Create it and add GGUF models.",
            models_dir
        );
    } else {
        tracing::info!("Models directory: {:?}", models_dir);
        let models = llama_manager::discover_models(&models_dir);
        tracing::info!("Found {} model(s) in models directory", models.len());
        for m in &models {
            tracing::info!(
                "  - {} ({}): {:?} {}",
                m.name,
                llama_manager::format_size(m.size_bytes),
                m.path,
                if m.has_mmproj { "[has mmproj]" } else { "" }
            );
        }
    }

    if let Some(path) = std::env::var_os("LLAMA_SERVER_PATH") {
        tracing::info!("LLAMA_SERVER_PATH set to: {:?}", path);
    }

    let manager = Arc::new(LlamaServerManager::new());
    let state = AppState {
        manager,
        models_dir: Arc::new(parking_lot::RwLock::new(models_dir)),
        manager_port,
    };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = llama_manager::router(state).layer(cors);

    let addr = format!("0.0.0.0:{}", manager_port);
    tracing::info!("llama-manager listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
