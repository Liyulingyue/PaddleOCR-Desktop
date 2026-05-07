use oar_ocr::prelude::*;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

pub struct OcrEngine {
    ocr: Arc<Mutex<Option<OAROCR>>>,
    models_dir: PathBuf,
}

impl OcrEngine {
    pub fn new(models_dir: PathBuf) -> Self {
        Self {
            ocr: Arc::new(Mutex::new(None)),
            models_dir,
        }
    }

    pub fn predict(&self, img: image::RgbImage) -> Result<OAROCRResult, String> {
        let mut guard = self.ocr.lock().map_err(|e| e.to_string())?;

        if guard.is_none() {
            drop(guard);
            self.load()?;
            guard = self.ocr.lock().map_err(|e| e.to_string())?;
        }

        let ocr = guard.as_ref().ok_or("OCR not initialized")?;
        let results = ocr.predict(vec![img]).map_err(|e| e.to_string())?;
        Ok(results.into_iter().next().unwrap())
    }

    pub fn load(&self) -> Result<(), String> {
        let models_dir = &self.models_dir;
        let det = models_dir.join("pp-ocrv5_mobile_det.onnx");
        let rec = models_dir.join("pp-ocrv5_mobile_rec.onnx");
        let dict = models_dir.join("ppocrv5_dict.txt");

        for (name, path) in [("det", &det), ("rec", &rec), ("dict", &dict)] {
            if !path.exists() {
                return Err(format!("Model {} not found: {}", name, path.display()));
            }
        }

        let ocr = OAROCRBuilder::new(&det, &rec, &dict)
            .build()
            .map_err(|e| e.to_string())?;

        let mut guard = self.ocr.lock().map_err(|e| e.to_string())?;
        *guard = Some(ocr);
        Ok(())
    }

    pub fn unload(&self) -> Result<(), String> {
        let mut guard = self.ocr.lock().map_err(|e| e.to_string())?;
        *guard = None;
        Ok(())
    }

    pub fn is_loaded(&self) -> bool {
        self.ocr.lock().ok().map(|g| g.is_some()).unwrap_or(false)
    }

    pub fn models_dir(&self) -> &PathBuf {
        &self.models_dir
    }
}

impl Clone for OcrEngine {
    fn clone(&self) -> Self {
        Self {
            ocr: Arc::clone(&self.ocr),
            models_dir: self.models_dir.clone(),
        }
    }
}
