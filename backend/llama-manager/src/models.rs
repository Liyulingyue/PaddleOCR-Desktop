use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use crate::error::{LlamaManagerError, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlamaModelInfo {
    pub name: String,
    pub path: PathBuf,
    pub size_bytes: u64,
    pub has_mmproj: bool,
    pub mmproj_path: Option<PathBuf>,
}

impl LlamaModelInfo {
    pub fn from_dir(dir: &Path) -> Option<Self> {
        if !dir.is_dir() {
            return None;
        }

        let name = dir.file_name()?.to_string_lossy().to_string();

        let gguf_files: Vec<_> = std::fs::read_dir(dir)
            .ok()?
            .filter_map(|e| e.ok())
            .filter(|e| {
                let p = e.path();
                p.is_file() && p.extension().map_or(false, |ext| ext == "gguf")
            })
            .collect();

        if gguf_files.is_empty() {
            return None;
        }

        let main_file = gguf_files
            .iter()
            .find(|f| {
                let name_lower = f.file_name().to_string_lossy().to_lowercase();
                !name_lower.contains("mmproj")
            })
            .or(gguf_files.first())?;

        let mmproj_file = gguf_files.iter().find(|f| {
            let name_lower = f.file_name().to_string_lossy().to_lowercase();
            name_lower.contains("mmproj")
        });

        let size_bytes = std::fs::metadata(main_file.path()).ok()?.len();

        Some(Self {
            name,
            path: main_file.path().clone(),
            size_bytes,
            has_mmproj: mmproj_file.is_some(),
            mmproj_path: mmproj_file.map(|f| f.path().clone()),
        })
    }
}

pub fn discover_models(models_dir: &Path) -> Vec<LlamaModelInfo> {
    if !models_dir.is_dir() {
        return Vec::new();
    }

    std::fs::read_dir(models_dir)
        .ok()
        .into_iter()
        .flat_map(|iter| iter.filter_map(|e| e.ok()))
        .filter_map(|entry| LlamaModelInfo::from_dir(&entry.path()))
        .collect()
}

pub fn find_model(models_dir: &Path, model_name: &str) -> Result<LlamaModelInfo> {
    let candidates = discover_models(models_dir);

    candidates
        .into_iter()
        .find(|m| m.name.to_lowercase() == model_name.to_lowercase())
        .ok_or_else(|| LlamaManagerError::ModelNotFound(model_name.to_string()))
}

pub fn format_size(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} B", bytes)
    }
}
