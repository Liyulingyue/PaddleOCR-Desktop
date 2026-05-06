use thiserror::Error;

#[derive(Error, Debug)]
pub enum OcrError {
    #[error("ONNX Runtime error: {0}")]
    Ort(String),

    #[error("Model file not found: {0}")]
    ModelNotFound(String),

    #[error("Image decode error: {0}")]
    ImageDecode(String),

    #[error("Invalid image dimensions: {0}")]
    InvalidDimensions(String),

    #[error("Detection failed: {0}")]
    Detection(String),

    #[error("Recognition failed: {0}")]
    Recognition(String),

    #[error("Classification failed: {0}")]
    Classification(String),

    #[error("Dictionary file not found: {0}")]
    DictNotFound(String),

    #[error("Invalid dictionary: {0}")]
    InvalidDict(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Image error: {0}")]
    Image(#[from] image::ImageError),
}

impl From<ort::Error> for OcrError {
    fn from(e: ort::Error) -> Self {
        OcrError::Ort(e.to_string())
    }
}
