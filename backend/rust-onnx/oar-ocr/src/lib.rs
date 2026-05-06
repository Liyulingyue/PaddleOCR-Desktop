pub mod error;
pub mod ort_utils;
pub mod detection;
pub mod recognition;
pub mod classification;
pub mod ocr;

pub mod prelude {
    pub use crate::error::OcrError;
    pub use crate::ocr::{OAROCR, OAROCRBuilder, OcrResult, TextRegion};
    pub use crate::detection::{BoundingBox, Point};
}
