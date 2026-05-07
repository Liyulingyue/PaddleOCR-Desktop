pub struct ModelInfo {
    pub filename: &'static str,
    pub url: &'static str,
    pub size_mb: f32,
}

pub fn default_detection() -> &'static ModelInfo {
    &ModelInfo {
        filename: "pp-ocrv5_mobile_det.onnx",
        url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_mobile_det.onnx",
        size_mb: 4.6,
    }
}

pub fn default_recognition() -> &'static ModelInfo {
    &ModelInfo {
        filename: "pp-ocrv5_mobile_rec.onnx",
        url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/pp-ocrv5_mobile_rec.onnx",
        size_mb: 15.8,
    }
}

pub fn default_dict() -> &'static ModelInfo {
    &ModelInfo {
        filename: "ppocrv5_dict.txt",
        url: "https://github.com/GreatV/oar-ocr/releases/download/v0.3.0/ppocrv5_dict.txt",
        size_mb: 0.05,
    }
}
