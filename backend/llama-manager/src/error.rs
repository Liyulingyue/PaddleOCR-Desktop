use thiserror::Error;

#[derive(Error, Debug)]
pub enum LlamaManagerError {
    #[error("llama-server not running")]
    NotRunning,
    #[error("llama-server already running at {0}")]
    AlreadyRunning(String),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("reqwest error: {0}")]
    Reqwest(#[from] reqwest::Error),
    #[error("Server error: {0}")]
    ServerError(String),
    #[error("Config error: {0}")]
    ConfigError(String),
    #[error("Model not found: {0}")]
    ModelNotFound(String),
    #[error("Process error: {0}")]
    ProcessError(String),
}

pub type Result<T> = std::result::Result<T, LlamaManagerError>;
