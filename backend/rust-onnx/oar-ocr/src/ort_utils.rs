use std::sync::{Arc, Mutex};
use ort::session::Session;
use std::path::Path;
use crate::error::OcrError;

pub struct OrtSession {
    pub session: Arc<Mutex<Session>>,
}

impl OrtSession {
    pub fn new(model_path: &Path) -> Result<Self, OcrError> {
        let session = ort::session::Session::builder()
            .map_err(|e| OcrError::Ort(format!("build error: {}", e)))?
            .with_execution_providers([ort::execution_providers::CPUExecutionProvider::default().build()])
            .map_err(|e| OcrError::Ort(format!("EP error: {}", e)))?
            .commit_from_file(model_path)
            .map_err(|e| OcrError::Ort(format!("commit error: {}", e)))?;
        Ok(Self {
            session: Arc::new(Mutex::new(session)),
        })
    }
}

pub fn read_dict(dict_path: &Path) -> Result<Vec<String>, OcrError> {
    if !dict_path.exists() {
        return Err(OcrError::DictNotFound(dict_path.display().to_string()));
    }
    let content = std::fs::read_to_string(dict_path)?;
    let labels: Vec<String> = content
        .lines()
        .map(|l| l.trim_end_matches('\r').to_string())
        .collect();
    Ok(labels)
}
