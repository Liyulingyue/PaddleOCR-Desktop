use std::sync::{Arc, Mutex};
use image::RgbImage;
use ort::session::Session;
use ort::value::Tensor;
use std::path::Path;

use crate::error::OcrError;
use crate::ort_utils::OrtSession;

const REC_HEIGHT: i32 = 48;
const REC_WIDTH_MAX: i32 = 256;

pub struct Recognizer {
    session: Arc<Mutex<Session>>,
    labels: Vec<String>,
}

impl Recognizer {
    pub fn new(model_path: &Path, dict_path: &Path) -> Result<Self, OcrError> {
        let labels = crate::ort_utils::read_dict(dict_path)?;
        let ort_session = OrtSession::new(model_path)?;
        Ok(Self {
            session: ort_session.session,
            labels,
        })
    }

    pub fn recognize(&self, crops: &[RgbImage]) -> Result<Vec<(String, f32)>, OcrError> {
        crops.iter().map(|crop| self.recognize_single(crop)).collect()
    }

    pub fn recognize_single(&self, crop: &RgbImage) -> Result<(String, f32), OcrError> {
        let (h, w) = crop.dimensions();
        let w = w.min(REC_WIDTH_MAX as u32);

        let resized = if h != REC_HEIGHT as u32 || w < crop.dimensions().0 {
            image::imageops::resize(
                crop,
                w,
                REC_HEIGHT as u32,
                image::imageops::FilterType::Triangle,
            )
        } else {
            crop.clone()
        };

        let input_tensor = self.image_to_tensor(&resized)?;

        let (seq_len, num_classes, probs) = {
            let mut guard = self.session.lock().map_err(|e| OcrError::Recognition(format!("lock error: {}", e)))?;
            let outputs = guard.run(ort::inputs![input_tensor])
                .map_err(|e| OcrError::Recognition(format!("run error: {}", e)))?;

            let output_arr = outputs[0]
                .try_extract_array::<f32>()
                .map_err(|e| OcrError::Recognition(format!("extract error: {}", e)))?;

            let shape = output_arr.shape();
            let seq_len = shape[1];
            let num_classes = shape[2];

            let probs: Vec<f32> = output_arr.iter().cloned().collect();
            (seq_len, num_classes, probs)
        };

        let (text, conf) = self.ctc_decode(&probs, seq_len, num_classes);
        Ok((text, conf))
    }

    fn image_to_tensor(&self, img: &RgbImage) -> Result<Tensor<f32>, OcrError> {
        let (h, w) = (REC_HEIGHT as u32, img.width().max(1));
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

        Tensor::from_array(data).map_err(|e| OcrError::Recognition(format!("tensor error: {}", e)))
    }

    fn ctc_decode(&self, probs: &[f32], seq_len: usize, num_classes: usize) -> (String, f32) {
        let mut result = String::new();
        let mut last_idx = 0usize;
        let mut sum_conf = 0.0f32;
        let mut count = 0usize;

        for t in 0..seq_len {
            let mut max_val = f32::NEG_INFINITY;
            let mut max_idx = 0usize;

            for c in 0..num_classes {
                let val = probs[t * num_classes + c];
                if val > max_val {
                    max_val = val;
                    max_idx = c;
                }
            }

            if max_idx != 0 && max_idx != last_idx {
                if max_idx < self.labels.len() {
                    result.push_str(&self.labels[max_idx]);
                }
                sum_conf += max_val.exp();
                count += 1;
            }
            last_idx = max_idx;
        }

        let conf = if count > 0 { sum_conf / count as f32 } else { 0.0 };
        (result, conf)
    }
}
