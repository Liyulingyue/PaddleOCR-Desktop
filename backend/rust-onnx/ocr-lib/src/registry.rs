use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tokio::fs::File;
use tokio::io::AsyncWriteExt;

#[derive(Clone)]
pub struct ModelRegistry {
    models_dir: PathBuf,
    verbose: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    pub name: String,
    #[serde(rename = "modelscope_id")]
    pub modelscope_id: String,
    #[serde(rename = "local_path")]
    pub local_path: String,
    pub label: String,
    pub description: String,
    #[serde(rename = "is_downloaded")]
    pub is_downloaded: bool,
    pub size: u64,
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

    pub fn get_model_path(&self, name: &str) -> Option<PathBuf> {
        let models = Self::all_models();
        let info = models.get(name)?;
        let path = self.models_dir.join(&info.local_path);
        if path.exists() {
            Some(path)
        } else {
            None
        }
    }

    pub fn model_exists(&self, name: &str) -> bool {
        self.get_model_path(name).is_some()
    }

    pub fn default_det_model() -> &'static str {
        "pp-ocrv5_mobile_det"
    }

    pub fn default_rec_model() -> &'static str {
        "pp-ocrv5_mobile_rec"
    }

    pub fn default_doc_cls_model() -> &'static str {
        "pp-lcnet_x1_0_doc_ori"
    }

    pub fn default_textline_cls_model() -> &'static str {
        "pp-lcnet_x1_0_textline_ori"
    }

    pub fn default_dict_model() -> &'static str {
        "ppocrv5_dict"
    }

    pub fn list_models(&self) -> Vec<ModelInfo> {
        Self::all_models()
            .into_iter()
            .map(|(key, info)| {
                let local_path = self.models_dir.join(&info.local_path);
                let is_downloaded = local_path.exists();
                let size = if is_downloaded {
                    Self::directory_size(&local_path)
                } else {
                    0
                };
                ModelInfo {
                    name: key.to_string(),
                    modelscope_id: info.modelscope_id.to_string(),
                    local_path: local_path.to_string_lossy().to_string(),
                    label: info.label.to_string(),
                    description: info.description.to_string(),
                    is_downloaded,
                    size,
                }
            })
            .collect()
    }

    fn directory_size(path: &PathBuf) -> u64 {
        if path.is_file() {
            return path.metadata().map(|m| m.len()).unwrap_or(0);
        }
        let mut total = 0u64;
        if let Ok(entries) = std::fs::read_dir(path) {
            for entry in entries.flatten() {
                let p = entry.path();
                total += if p.is_dir() {
                    Self::directory_size(&p)
                } else {
                    p.metadata().map(|m| m.len()).unwrap_or(0)
                };
            }
        }
        total
    }

    pub async fn download_model(&self, name: &str) -> Result<PathBuf, String> {
        let models = Self::all_models();
        let info = models.get(name).ok_or_else(|| format!("Unknown model: {}", name))?;
        let dest = self.models_dir.join(&info.local_path);

        if dest.exists() {
            if self.verbose {
                println!("  [exists] {}", info.local_path);
            }
            return Ok(dest);
        }

        tokio::fs::create_dir_all(&self.models_dir)
            .await
            .map_err(|e| format!("Failed to create directory: {}", e))?;

        let url = info.url;
        if url.is_empty() {
            return Err(format!(
                "No download URL available for model '{}'.",
                name
            ));
        }

        if self.verbose {
            println!("  Downloading {}...", info.local_path);
        }

        download_file_async(url, &dest, self.verbose).await?;

        if self.verbose {
            println!("  -> {}", dest.display());
        }

        Ok(dest)
    }

    pub fn blocking_download(&self, name: &str) -> Result<PathBuf, String> {
        let models = Self::all_models();
        let info = models.get(name).ok_or_else(|| format!("Unknown model: {}", name))?;
        let dest = self.models_dir.join(&info.local_path);

        if dest.exists() {
            if self.verbose {
                println!("  [exists] {}", info.local_path);
            }
            return Ok(dest);
        }

        std::fs::create_dir_all(&self.models_dir)
            .map_err(|e| format!("Failed to create directory: {}", e))?;

        let url = info.url;
        if url.is_empty() {
            return Err(format!(
                "No download URL available for model '{}'.",
                name
            ));
        }

        if self.verbose {
            println!("  Downloading {}...", info.local_path);
        }

        download_file_blocking(url, &dest, self.verbose)?;

        if self.verbose {
            println!("  -> {}", dest.display());
        }

        Ok(dest)
    }

    pub fn delete_model(&self, name: &str) -> Result<(), String> {
        let models = Self::all_models();
        let info = models.get(name).ok_or_else(|| format!("Unknown model: {}", name))?;
        let path = self.models_dir.join(&info.local_path);
        if path.exists() {
            if path.is_dir() {
                std::fs::remove_dir_all(&path)
                    .map_err(|e| format!("Failed to delete directory: {}", e))?;
            } else {
                std::fs::remove_file(&path)
                    .map_err(|e| format!("Failed to delete file: {}", e))?;
            }
        }
        Ok(())
    }

    pub fn ensure_default_models(&self) -> Result<(PathBuf, PathBuf, PathBuf), String> {
        let models = Self::all_models();
        let det_info = models.get("pp-ocrv5_mobile_det").unwrap();
        let rec_info = models.get("pp-ocrv5_mobile_rec").unwrap();
        let dict_info = models.get("ppocrv5_dict").unwrap();

        let det = self.models_dir.join(&det_info.local_path);
        let rec = self.models_dir.join(&rec_info.local_path);
        let dict = self.models_dir.join(&dict_info.local_path);

        if !det.exists() {
            let url = det_info.url;
            if !url.is_empty() {
                download_file_blocking(url, &det, self.verbose)?;
            }
        }
        if !rec.exists() {
            let url = rec_info.url;
            if !url.is_empty() {
                download_file_blocking(url, &rec, self.verbose)?;
            }
        }
        if !dict.exists() {
            let url = dict_info.url;
            if !url.is_empty() {
                download_file_blocking(url, &dict, self.verbose)?;
            }
        }

        Ok((det, rec, dict))
    }

    pub fn all_models() -> std::collections::HashMap<&'static str, ModelRegEntry> {
        let mut m = std::collections::HashMap::new();

        // PP-OCR 检测模型
        m.insert("pp-ocrv5_mobile_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv5_mobile_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_mobile_det.onnx",
            label: "PP-OCRv5 Mobile 检测 (轻量级)",
            description: "轻量级文本检测模型，适合移动端和一般场景",
        });
        m.insert("pp-ocrv5_server_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv5_server_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_server_det.onnx",
            label: "PP-OCRv5 Server 检测 (高精度)",
            description: "高精度文本检测模型，适合服务器端和复杂场景",
        });
        m.insert("pp-ocrv4_mobile_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv4_mobile_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv4_mobile_det.onnx",
            label: "PP-OCRv4 Mobile 检测",
            description: "PP-OCRv4 轻量级文本检测模型",
        });
        m.insert("pp-ocrv4_server_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv4_server_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv4_server_det.onnx",
            label: "PP-OCRv4 Server 检测 (高精度)",
            description: "PP-OCRv4 高精度文本检测模型",
        });
        m.insert("pp-ocrv4_mobile_seal_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv4_mobile_seal_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv4_mobile_seal_det.onnx",
            label: "PP-OCRv4 Mobile 印章检测",
            description: "印章检测模型",
        });
        m.insert("pp-ocrv4_server_seal_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv4_server_seal_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv4_server_seal_det.onnx",
            label: "PP-OCRv4 Server 印章检测 (高精度)",
            description: "高精度印章检测模型",
        });

        // PP-OCR 识别模型
        m.insert("pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Mobile 识别 (轻量级)",
            description: "轻量级文本识别模型，适合移动端和一般场景",
        });
        m.insert("pp-ocrv5_server_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv5_server_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_server_rec.onnx",
            label: "PP-OCRv5 Server 识别 (高精度)",
            description: "高精度文本识别模型，适合服务器端和复杂场景",
        });
        m.insert("pp-ocrv4_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv4_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv4_mobile_rec.onnx",
            label: "PP-OCRv4 Mobile 识别",
            description: "PP-OCRv4 轻量级文本识别模型",
        });
        m.insert("pp-ocrv4_server_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv4_server_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv4_server_rec.onnx",
            label: "PP-OCRv4 Server 识别 (高精度)",
            description: "PP-OCRv4 高精度文本识别模型",
        });
        m.insert("pp-ocrv4_server_rec_doc", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv4_server_rec_doc.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv4_server_rec_doc.onnx",
            label: "PP-OCRv4 Server 文档识别",
            description: "文档场景专用识别模型",
        });
        m.insert("pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Mobile 识别",
            description: "PP-OCRv3 轻量级文本识别模型",
        });
        m.insert("en_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "en_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/en_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 English 识别",
            description: "英文专用识别模型",
        });
        m.insert("en_pp-ocrv4_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "en_pp-ocrv4_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/en_pp-ocrv4_mobile_rec.onnx",
            label: "PP-OCRv4 English 识别",
            description: "英文专用识别模型",
        });
        m.insert("en_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "en_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/en_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 English 识别",
            description: "英文专用识别模型",
        });

        // 多语言识别模型
        m.insert("chinese_cht_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "chinese_cht_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/chinese_cht_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 繁体中文识别",
            description: "繁体中文文本识别模型",
        });
        m.insert("ch_repsvtr_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "ch_repsvtr_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ch_repsvtr_rec.onnx",
            label: "中文 REPSVTR 识别",
            description: "基于 REPSVTR 的中文识别模型",
        });
        m.insert("ch_svtrv2_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "ch_svtrv2_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ch_svtrv2_rec.onnx",
            label: "中文 SVTRv2 识别",
            description: "基于 SVTRv2 的中文识别模型",
        });
        m.insert("latin_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "latin_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/latin_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Latin 识别",
            description: "拉丁语系文本识别模型",
        });
        m.insert("latin_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "latin_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/latin_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Latin 识别",
            description: "拉丁语系文本识别模型",
        });
        m.insert("arabic_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "arabic_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/arabic_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Arabic 识别",
            description: "阿拉伯语文本识别模型",
        });
        m.insert("arabic_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "arabic_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/arabic_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Arabic 识别",
            description: "阿拉伯语文本识别模型",
        });
        m.insert("cyrillic_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "cyrillic_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/cyrillic_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Cyrillic 识别",
            description: "西里尔语文本识别模型",
        });
        m.insert("cyrillic_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "cyrillic_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/cyrillic_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Cyrillic 识别",
            description: "西里尔语文本识别模型",
        });
        m.insert("devanagari_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "devanagari_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/devanagari_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Devanagari 识别",
            description: "天城文文本识别模型",
        });
        m.insert("devanagari_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "devanagari_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/devanagari_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Devanagari 识别",
            description: "天城文文本识别模型",
        });
        m.insert("korean_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "korean_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/korean_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Korean 识别",
            description: "韩语文本识别模型",
        });
        m.insert("korean_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "korean_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/korean_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Korean 识别",
            description: "韩语文本识别模型",
        });
        m.insert("japan_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "japan_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/japan_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Japanese 识别",
            description: "日语文本识别模型",
        });
        m.insert("el_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "el_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/el_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Greek 识别",
            description: "希腊语文本识别模型",
        });
        m.insert("eslav_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "eslav_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/eslav_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Eslavic 识别",
            description: "斯拉夫语文本识别模型",
        });
        m.insert("ka_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "ka_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ka_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Georgian 识别",
            description: "格鲁吉亚语文本识别模型",
        });
        m.insert("ta_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "ta_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ta_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Tamil 识别",
            description: "泰米尔语文本识别模型",
        });
        m.insert("ta_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "ta_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ta_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Tamil 识别",
            description: "泰米尔语文本识别模型",
        });
        m.insert("te_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "te_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/te_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Telugu 识别",
            description: "泰卢固语文本识别模型",
        });
        m.insert("te_pp-ocrv3_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "te_pp-ocrv3_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/te_pp-ocrv3_mobile_rec.onnx",
            label: "PP-OCRv3 Telugu 识别",
            description: "泰卢固语文本识别模型",
        });
        m.insert("th_pp-ocrv5_mobile_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "th_pp-ocrv5_mobile_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/th_pp-ocrv5_mobile_rec.onnx",
            label: "PP-OCRv5 Thai 识别",
            description: "泰语文本识别模型",
        });

        // 字典文件
        m.insert("ppocrv5_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_dict.txt",
            label: "PP-OCRv5 字符字典 (默认)",
            description: "PP-OCRv5 默认字符字典",
        });
        m.insert("ppocrv4_doc_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv4_doc_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv4_doc_dict.txt",
            label: "PP-OCRv4 文档字典",
            description: "PP-OCRv4 文档识别字典",
        });
        m.insert("ppocr_keys_v1", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocr_keys_v1.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocr_keys_v1.txt",
            label: "PP-OCR Keys V1",
            description: "PP-OCR 字符键表",
        });
        m.insert("ppocrv5_arabic_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_arabic_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_arabic_dict.txt",
            label: "PP-OCRv5 Arabic 字典",
            description: "阿拉伯语字符字典",
        });
        m.insert("ppocrv5_cyrillic_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_cyrillic_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_cyrillic_dict.txt",
            label: "PP-OCRv5 Cyrillic 字典",
            description: "西里尔字符字典",
        });
        m.insert("ppocrv5_devanagari_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_devanagari_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_devanagari_dict.txt",
            label: "PP-OCRv5 Devanagari 字典",
            description: "天城文字符字典",
        });
        m.insert("ppocrv5_el_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_el_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_el_dict.txt",
            label: "PP-OCRv5 Greek 字典",
            description: "希腊字符字典",
        });
        m.insert("ppocrv5_en_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_en_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_en_dict.txt",
            label: "PP-OCRv5 English 字典",
            description: "英文字符字典",
        });
        m.insert("ppocrv5_eslav_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_eslav_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_eslav_dict.txt",
            label: "PP-OCRv5 Eslavic 字典",
            description: "斯拉夫字符字典",
        });
        m.insert("ppocrv5_korean_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_korean_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_korean_dict.txt",
            label: "PP-OCRv5 Korean 字典",
            description: "韩文字符字典",
        });
        m.insert("ppocrv5_latin_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_latin_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_latin_dict.txt",
            label: "PP-OCRv5 Latin 字典",
            description: "拉丁字符字典",
        });
        m.insert("ppocrv5_ta_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_ta_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_ta_dict.txt",
            label: "PP-OCRv5 Tamil 字典",
            description: "泰米尔字符字典",
        });
        m.insert("ppocrv5_te_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_te_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_te_dict.txt",
            label: "PP-OCRv5 Telugu 字典",
            description: "泰卢固字符字典",
        });
        m.insert("ppocrv5_th_dict", ModelRegEntry {
            modelscope_id: "",
            local_path: "ppocrv5_th_dict.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_th_dict.txt",
            label: "PP-OCRv5 Thai 字典",
            description: "泰文字符字典",
        });

        // 文档布局检测模型
        m.insert("picodet-l_layout_17cls", ModelRegEntry {
            modelscope_id: "",
            local_path: "picodet-l_layout_17cls.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/picodet-l_layout_17cls.onnx",
            label: "PicoDet L Layout 17类",
            description: "17类文档布局检测（大模型）",
        });
        m.insert("picodet-s_layout_17cls", ModelRegEntry {
            modelscope_id: "",
            local_path: "picodet-s_layout_17cls.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/picodet-s_layout_17cls.onnx",
            label: "PicoDet S Layout 17类",
            description: "17类文档布局检测（小模型）",
        });
        m.insert("picodet-l_layout_3cls", ModelRegEntry {
            modelscope_id: "",
            local_path: "picodet-l_layout_3cls.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/picodet-l_layout_3cls.onnx",
            label: "PicoDet L Layout 3类",
            description: "3类文档布局检测（大模型）",
        });
        m.insert("picodet-s_layout_3cls", ModelRegEntry {
            modelscope_id: "",
            local_path: "picodet-s_layout_3cls.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/picodet-s_layout_3cls.onnx",
            label: "PicoDet S Layout 3类",
            description: "3类文档布局检测（小模型）",
        });
        m.insert("picodet_layout_1x", ModelRegEntry {
            modelscope_id: "",
            local_path: "picodet_layout_1x.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/picodet_layout_1x.onnx",
            label: "PicoDet Layout 1x",
            description: "通用文档布局检测模型",
        });
        m.insert("pp-doclayout-l", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-doclayout-l.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-doclayout-l.onnx",
            label: "PP-DocLayout L",
            description: "文档布局检测 L 模型",
        });
        m.insert("pp-doclayout-m", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-doclayout-m.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-doclayout-m.onnx",
            label: "PP-DocLayout M",
            description: "文档布局检测 M 模型",
        });
        m.insert("pp-doclayout-s", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-doclayout-s.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-doclayout-s.onnx",
            label: "PP-DocLayout S",
            description: "文档布局检测 S 模型",
        });
        m.insert("pp-doclayout_plus-l", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-doclayout_plus-l.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-doclayout_plus-l.onnx",
            label: "PP-DocLayout Plus L",
            description: "增强版文档布局检测 L 模型",
        });
        m.insert("pp-doclayoutv2", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-doclayoutv2.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-doclayoutv2.onnx",
            label: "PP-DocLayout V2",
            description: "文档布局检测 V2 模型",
        });
        m.insert("pp-doclayoutv2-old", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-doclayoutv2-old.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-doclayoutv2-old.onnx",
            label: "PP-DocLayout V2 Old",
            description: "文档布局检测 V2 旧版模型",
        });
        m.insert("pp-docblocklayout", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-docblocklayout.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-docblocklayout.onnx",
            label: "PP-DocBlockLayout",
            description: "文档块级布局检测模型",
        });
        m.insert("rt-detr-h_layout_17cls", ModelRegEntry {
            modelscope_id: "",
            local_path: "rt-detr-h_layout_17cls.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/rt-detr-h_layout_17cls.onnx",
            label: "RT-DETR-H Layout 17类",
            description: "RT-DETR 高精度 17类布局检测",
        });
        m.insert("rt-detr-h_layout_3cls", ModelRegEntry {
            modelscope_id: "",
            local_path: "rt-detr-h_layout_3cls.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/rt-detr-h_layout_3cls.onnx",
            label: "RT-DETR-H Layout 3类",
            description: "RT-DETR 高精度 3类布局检测",
        });

        // 方向分类模型
        m.insert("pp-lcnet_x1_0_doc_ori", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-lcnet_x1_0_doc_ori.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-lcnet_x1_0_doc_ori.onnx",
            label: "PP-LCNet x1.0 文档方向检测",
            description: "文档场景方向分类模型",
        });
        m.insert("pp-lcnet_x1_0_textline_ori", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-lcnet_x1_0_textline_ori.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-lcnet_x1_0_textline_ori.onnx",
            label: "PP-LCNet x1.0 文本行方向检测",
            description: "文本行场景方向分类模型",
        });
        m.insert("pp-lcnet_x0_25_textline_ori", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-lcnet_x0_25_textline_ori.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-lcnet_x0_25_textline_ori.onnx",
            label: "PP-LCNet x0.25 文本行方向检测",
            description: "轻量级文本行方向分类模型",
        });
        m.insert("pp-lcnet_x1_0_table_cls", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-lcnet_x1_0_table_cls.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-lcnet_x1_0_table_cls.onnx",
            label: "PP-LCNet x1.0 表格分类",
            description: "表格分类模型",
        });

        // 表格相关模型
        m.insert("picodet_layout_1x_table", ModelRegEntry {
            modelscope_id: "",
            local_path: "picodet_layout_1x_table.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/picodet_layout_1x_table.onnx",
            label: "PicoDet Layout 表格",
            description: "表格布局检测模型",
        });
        m.insert("rt-detr-l_wired_table_cell_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "rt-detr-l_wired_table_cell_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/rt-detr-l_wired_table_cell_det.onnx",
            label: "RT-DETR-L 有线表格单元格检测",
            description: "有线表格单元格检测模型",
        });
        m.insert("rt-detr-l_wireless_table_cell_det", ModelRegEntry {
            modelscope_id: "",
            local_path: "rt-detr-l_wireless_table_cell_det.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/rt-detr-l_wireless_table_cell_det.onnx",
            label: "RT-DETR-L 无线表格单元格检测",
            description: "无线表格单元格检测模型",
        });
        m.insert("table_structure_dict_ch", ModelRegEntry {
            modelscope_id: "",
            local_path: "table_structure_dict_ch.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/table_structure_dict_ch.txt",
            label: "表格结构字典 (中文)",
            description: "中文表格结构识别字典",
        });

        // 公式识别模型
        m.insert("pp-formulanet-l", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-formulanet-l.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-formulanet-l.onnx",
            label: "PP-FormulaNet L",
            description: "公式识别 L 模型",
        });
        m.insert("pp-formulanet-s", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-formulanet-s.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-formulanet-s.onnx",
            label: "PP-FormulaNet S",
            description: "公式识别 S 模型",
        });
        m.insert("pp-formulanet_plus-l", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-formulanet_plus-l.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-formulanet_plus-l.onnx",
            label: "PP-FormulaNet Plus L",
            description: "增强版公式识别 L 模型",
        });
        m.insert("pp-formulanet_plus-m", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-formulanet_plus-m.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-formulanet_plus-m.onnx",
            label: "PP-FormulaNet Plus M",
            description: "增强版公式识别 M 模型",
        });
        m.insert("pp-formulanet_plus-s", ModelRegEntry {
            modelscope_id: "",
            local_path: "pp-formulanet_plus-s.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-formulanet_plus-s.onnx",
            label: "PP-FormulaNet Plus S",
            description: "增强版公式识别 S 模型",
        });
        m.insert("latex_ocr_rec", ModelRegEntry {
            modelscope_id: "",
            local_path: "latex_ocr_rec.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/latex_ocr_rec.onnx",
            label: "LaTeX OCR 识别",
            description: "LaTeX 公式识别模型 (使用 unimernet_tokenizer)",
        });

        // Table structure dictionary
        m.insert("table_structure_dict_ch", ModelRegEntry {
            modelscope_id: "",
            local_path: "table_structure_dict_ch.txt",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/table_structure_dict_ch.txt",
            label: "表格结构字典 (中文)",
            description: "中文表格结构识别字典",
        });

        // UVDoc
        m.insert("uvdoc", ModelRegEntry {
            modelscope_id: "",
            local_path: "uvdoc.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/uvdoc.onnx",
            label: "UVDoc",
            description: "UVDoc 文档纠偏模型",
        });

        // Tokenizers
        m.insert("unimernet_tokenizer", ModelRegEntry {
            modelscope_id: "",
            local_path: "unimernet_tokenizer.json",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/unimernet_tokenizer.json",
            label: "UniMERNet Tokenizer",
            description: "UniMERNet 公式识别分词器",
        });

        // SlanNet
        m.insert("slanet", ModelRegEntry {
            modelscope_id: "",
            local_path: "slanet.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/slanet.onnx",
            label: "SlaNet",
            description: "表格检测模型",
        });
        m.insert("slanet_plus", ModelRegEntry {
            modelscope_id: "",
            local_path: "slanet_plus.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/slanet_plus.onnx",
            label: "SlaNet Plus",
            description: "增强版表格检测模型",
        });
        m.insert("slanext_wired", ModelRegEntry {
            modelscope_id: "",
            local_path: "slanext_wired.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/slanext_wired.onnx",
            label: "SlaExt Wired",
            description: "有线表格扩展模型",
        });
        m.insert("slanext_wireless", ModelRegEntry {
            modelscope_id: "",
            local_path: "slanext_wireless.onnx",
            url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/slanext_wireless.onnx",
            label: "SlaExt Wireless",
            description: "无线表格扩展模型",
        });

        m
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRegEntry {
    pub modelscope_id: &'static str,
    pub local_path: &'static str,
    pub url: &'static str,
    pub label: &'static str,
    pub description: &'static str,
}

async fn download_file_async(url: &str, dest: &PathBuf, verbose: bool) -> Result<(), String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(300))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Failed to send request: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("HTTP {}", response.status()));
    }

    let total_size = response.content_length().unwrap_or(0);
    if verbose {
        println!("    Size: {:.1} MB", total_size as f64 / 1_048_576.0);
    }

    let bytes = response
        .bytes()
        .await
        .map_err(|e| format!("Failed to read response body: {}", e))?;

    let mut file = File::create(dest)
        .await
        .map_err(|e| format!("Failed to create file: {}", e))?;
    file.write_all(&bytes)
        .await
        .map_err(|e| format!("Failed to write file: {}", e))?;

    Ok(())
}

fn download_file_blocking(url: &str, dest: &PathBuf, verbose: bool) -> Result<(), String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(300))
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let mut response = client
        .get(url)
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
