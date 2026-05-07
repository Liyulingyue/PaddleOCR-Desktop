use oar_ocr::prelude::*;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

pub struct OcrEngine {
    pipelines: Arc<Mutex<HashMap<String, Arc<OAROCR>>>>,
    models_dir: PathBuf,
}

impl Clone for OcrEngine {
    fn clone(&self) -> Self {
        Self {
            pipelines: Arc::clone(&self.pipelines),
            models_dir: self.models_dir.clone(),
        }
    }
}

impl OcrEngine {
    pub fn new(models_dir: PathBuf) -> Self {
        Self {
            pipelines: Arc::new(Mutex::new(HashMap::new())),
            models_dir,
        }
    }

    pub fn models_dir(&self) -> &PathBuf {
        &self.models_dir
    }

    pub fn get_or_build_pipeline(&self, model_key: &str) -> Result<Arc<OAROCR>, String> {
        {
            let guard = self.pipelines.lock().map_err(|e| e.to_string())?;
            if let Some(pipeline) = guard.get(model_key) {
                return Ok(Arc::clone(pipeline));
            }
        }

        let pipeline = Self::build_pipeline(&self.models_dir, model_key)?;
        let pipeline = Arc::new(pipeline);

        {
            let mut guard = self.pipelines.lock().map_err(|e| e.to_string())?;
            guard.insert(model_key.to_string(), Arc::clone(&pipeline));
        }

        Ok(pipeline)
    }

    fn build_pipeline(models_dir: &PathBuf, model_key: &str) -> Result<OAROCR, String> {
        let parts: Vec<&str> = model_key.split('|').collect();
        let det_model = parts.first().copied().unwrap_or(Self::default_det());
        let rec_model = parts.get(1).copied().unwrap_or(Self::default_rec());
        let doc_cls_model = parts.get(2).copied();
        let textline_cls_model = parts.get(3).copied();

        let det_path = Self::resolve_model(models_dir, det_model)?;
        let rec_path = Self::resolve_model(models_dir, rec_model)?;
        let dict_path = Self::resolve_default_dict(models_dir)?;

        let mut builder = OAROCRBuilder::new(&det_path, &rec_path, &dict_path);

        if let Some(cls) = doc_cls_model {
            if let Ok(path) = Self::resolve_model(models_dir, cls) {
                builder = builder.with_document_image_orientation_classification(&path);
            }
        }

        if let Some(cls) = textline_cls_model {
            if let Ok(path) = Self::resolve_model(models_dir, cls) {
                builder = builder.with_text_line_orientation_classification(&path);
            }
        }

        builder.build().map_err(|e| e.to_string())
    }

    fn resolve_model(models_dir: &PathBuf, name: &str) -> Result<PathBuf, String> {
        let models = crate::registry::ModelRegistry::all_models();
        let info = models.get(name).ok_or_else(|| format!("Unknown model: {}", name))?;
        let path = models_dir.join(info.local_path);
        if path.exists() {
            Ok(path)
        } else {
            Err(format!(
                "Model file not found: {} (expected at {})",
                name,
                path.display()
            ))
        }
    }

    fn resolve_default_dict(models_dir: &PathBuf) -> Result<PathBuf, String> {
        Self::resolve_model(models_dir, Self::default_dict())
    }

    pub fn default_model_key() -> String {
        format!(
            "{}|{}|{}|{}",
            Self::default_det(),
            Self::default_rec(),
            Self::default_doc_cls(),
            Self::default_textline_cls()
        )
    }

    pub fn default_det() -> &'static str {
        "pp-ocrv5_mobile_det"
    }

    pub fn default_rec() -> &'static str {
        "pp-ocrv5_mobile_rec"
    }

    pub fn default_doc_cls() -> &'static str {
        "pp-lcnet_x1_0_doc_ori"
    }

    pub fn default_textline_cls() -> &'static str {
        "pp-lcnet_x1_0_textline_ori"
    }

    pub fn default_dict() -> &'static str {
        "ppocrv5_dict"
    }

    pub fn predict(&self, img: image::RgbImage, model_key: &str) -> Result<OAROCRResult, String> {
        let pipeline = self.get_or_build_pipeline(model_key)?;
        let results = pipeline.predict(vec![img]).map_err(|e| e.to_string())?;
        Ok(results.into_iter().next().unwrap())
    }

    pub fn unload(&self) -> Result<(), String> {
        let mut guard = self.pipelines.lock().map_err(|e| e.to_string())?;
        guard.clear();
        Ok(())
    }

    pub fn is_loaded(&self) -> bool {
        self.pipelines.lock().ok().map(|g| !g.is_empty()).unwrap_or(false)
    }

    pub fn check_all_models(&self) -> (bool, Vec<&'static str>) {
        let models = crate::registry::ModelRegistry::all_models();
        let mut missing = Vec::new();
        for name in [Self::default_det(), Self::default_rec(), Self::default_doc_cls(), Self::default_textline_cls()] {
            if let Some(info) = models.get(name) {
                let path = self.models_dir.join(info.local_path);
                if !path.exists() {
                    missing.push(name);
                }
            }
        }
        (missing.is_empty(), missing)
    }
}
