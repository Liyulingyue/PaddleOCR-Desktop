use std::sync::{Arc, Mutex};
use image::RgbImage;
use ort::session::Session;
use ort::value::Tensor;
use std::path::Path;

use crate::error::OcrError;
use crate::ort_utils::OrtSession;

const CLS_HEIGHT: i32 = 192;
const CLS_WIDTH: i32 = 192;

pub struct Classifier {
    session: Arc<Mutex<Session>>,
}

impl Classifier {
    pub fn new(model_path: &Path) -> Result<Self, OcrError> {
        let ort_session = OrtSession::new(model_path)?;
        Ok(Self {
            session: ort_session.session,
        })
    }

    pub fn classify(&self, img: &RgbImage) -> Result<(i32, f32), OcrError> {
        let resized = image::imageops::resize(
            img,
            CLS_WIDTH as u32,
            CLS_HEIGHT as u32,
            image::imageops::FilterType::Triangle,
        );

        let input_tensor = self.image_to_tensor(&resized)?;

        let probs = {
            let mut guard = self.session.lock().map_err(|e| OcrError::Classification(format!("lock error: {}", e)))?;
            let outputs = guard.run(ort::inputs![input_tensor])
                .map_err(|e| OcrError::Classification(format!("run error: {}", e)))?;

            let output_arr = outputs[0]
                .try_extract_array::<f32>()
                .map_err(|e| OcrError::Classification(format!("extract error: {}", e)))?;

            output_arr.iter().cloned().collect::<Vec<f32>>()
        };

        let mut max_idx = 0;
        let mut max_val = f32::NEG_INFINITY;
        for (i, &v) in probs.iter().enumerate() {
            if v > max_val {
                max_val = v;
                max_idx = i;
            }
        }

        Ok((max_idx as i32, max_val))
    }

    fn image_to_tensor(&self, img: &RgbImage) -> Result<Tensor<f32>, OcrError> {
        let h = CLS_HEIGHT as u32;
        let w = CLS_WIDTH as u32;
        let mut data = ndarray::Array4::<f32>::zeros((1, 3, h as usize, w as usize));

        for y in 0..h {
            for x in 0..w {
                let pixel = img.get_pixel(
                    x.min(img.width().saturating_sub(1)),
                    y.min(img.height().saturating_sub(1)),
                );
                data[[0, 0, y as usize, x as usize]] = (pixel[0] as f32 - 127.5) / 127.5;
                data[[0, 1, y as usize, x as usize]] = (pixel[1] as f32 - 127.5) / 127.5;
                data[[0, 2, y as usize, x as usize]] = (pixel[2] as f32 - 127.5) / 127.5;
            }
        }

        Tensor::from_array(data).map_err(|e| OcrError::Classification(format!("tensor error: {}", e)))
    }
}
