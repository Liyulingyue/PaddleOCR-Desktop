use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Clone)]
pub struct ModelRegistry {
    models_dir: PathBuf,
    verbose: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    pub filename: &'static str,
    pub url: &'static str,
    pub size_mb: f32,
    pub label: &'static str,
    pub description: &'static str,
}

impl ModelRegistry {
    pub fn new(models_dir: PathBuf) -> Self {
        Self { models_dir, verbose: true }
    }

    pub fn verbose(mut self, v: bool) -> Self {
        self.verbose = v;
        self
    }

    pub fn models_dir(&self) -> &PathBuf {
        &self.models_dir
    }

    pub fn list_models(&self) -> Vec<ModelListEntry> {
        Self::all_models().into_iter().map(|(key, info)| {
            let path = self.models_dir.join(info.filename);
            let downloaded = path.exists();
            let size_bytes = if downloaded {
                std::fs::metadata(&path).map(|m| m.len()).unwrap_or(0)
            } else {
                0
            };
            ModelListEntry {
                name: key.to_string(),
                filename: info.filename.to_string(),
                url: info.url.to_string(),
                label: info.label.to_string(),
                description: info.description.to_string(),
                downloaded,
                size_bytes,
            }
        }).collect()
    }

    pub fn download_model(&self, name: &str) -> Result<PathBuf, String> {
        let models = Self::all_models();
        let info = models.get(name).ok_or_else(|| format!("Unknown model: {}", name))?;
        let dest = self.models_dir.join(info.filename);

        if dest.exists() {
            if self.verbose {
                println!("  [exists] {}", info.filename);
            }
            return Ok(dest);
        }

        std::fs::create_dir_all(&self.models_dir)
            .map_err(|e| format!("Failed to create directory: {}", e))?;

        if self.verbose {
            println!("  Downloading {} ({:.1} MB)...", info.filename, info.size_mb);
        }

        download_file(info.url, &dest, self.verbose)?;

        if self.verbose {
            println!("  -> {}", dest.display());
        }

        Ok(dest)
    }

    pub fn download_all(&self) -> Vec<DownloadResult> {
        let mut results = Vec::new();
        for (name, _info) in Self::all_models() {
            match self.download_model(name) {
                Ok(path) => results.push(DownloadResult {
                    name: name.to_string(),
                    success: true,
                    path: Some(path.to_string_lossy().to_string()),
                    error: None,
                }),
                Err(e) => results.push(DownloadResult {
                    name: name.to_string(),
                    success: false,
                    path: None,
                    error: Some(e),
                }),
            }
        }
        results
    }

    pub fn delete_model(&self, name: &str) -> Result<(), String> {
        let models = Self::all_models();
        let info = models.get(name).ok_or_else(|| format!("Unknown model: {}", name))?;
        let path = self.models_dir.join(info.filename);
        if path.exists() {
            std::fs::remove_file(&path)
                .map_err(|e| format!("Failed to delete: {}", e))?;
        }
        Ok(())
    }

    pub fn ensure_default_models(&self) -> Result<(PathBuf, PathBuf, PathBuf), String> {
        let det = self.download_model("pp-ocrv5_mobile_det")?;
        let rec = self.download_model("pp-ocrv5_mobile_rec")?;
        let dict = self.download_model("pp-ocrv5_dict")?;
        Ok((det, rec, dict))
    }

    pub fn all_models() -> std::collections::HashMap<&'static str, ModelInfo> {
        let mut m = std::collections::HashMap::new();
        m.insert("pp-ocrv5_mobile_det", ModelInfo {
            filename: "pp-ocrv5_mobile_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_mobile_det.onnx",
            size_mb: 4.6,
            label: "PP-OCRv5 Mobile 检测 (轻量级)",
            description: "轻量级文本检测模型，适合移动端和一般场景",
        });
        m.insert("pp-ocrv5_mobile_rec", ModelInfo {
            filename: "pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_mobile_rec.onnx",
            size_mb: 15.8,
            label: "PP-OCRv5 Mobile 识别 (轻量级)",
            description: "轻量级文本识别模型，适合移动端和一般场景",
        });
        m.insert("pp-ocrv5_dict", ModelInfo {
            filename: "ppocrv5_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_dict.txt",
            size_mb: 0.05,
            label: "PP-OCRv5 字符字典",
            description: "PP-OCRv5 识别模型使用的字符字典",
        });
        m
    }
}

fn download_file(url: &str, dest: &PathBuf, verbose: bool) -> Result<(), String> {
    let client = reqwest::blocking::Client::builder()
        .proxy(reqwest::Proxy::https("http://127.0.0.1:7890").map_err(|e| e.to_string())?)
        .proxy(reqwest::Proxy::http("http://127.0.0.1:7890").map_err(|e| e.to_string())?)
        .build()
        .map_err(|e| e.to_string())?;

    let mut response = client.get(url)
        .send()
        .map_err(|e| format!("Failed to send request: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("HTTP {}", response.status()));
    }

    let total_size = response.content_length().unwrap_or(0);
    if verbose {
        println!("    Size: {:.1} MB", total_size as f64 / 1_048_576.0);
    }

    let mut dest_file = std::fs::File::create(dest)
        .map_err(|e| format!("Failed to create file: {}", e))?;
    std::io::copy(&mut response, &mut dest_file)
        .map_err(|e| format!("Failed to write file: {}", e))?;

    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelListEntry {
    pub name: String,
    pub filename: String,
    pub url: String,
    pub label: String,
    pub description: String,
    pub downloaded: bool,
    pub size_bytes: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DownloadResult {
    pub name: String,
    pub success: bool,
    pub path: Option<String>,
    pub error: Option<String>,
}
