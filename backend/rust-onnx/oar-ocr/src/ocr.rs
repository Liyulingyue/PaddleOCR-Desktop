use image::{ImageBuffer, RgbImage};
use std::path::Path;

use crate::classification::Classifier;
use crate::detection::{BoundingBox, Detector, Point};
use crate::error::OcrError;
use crate::recognition::Recognizer;

#[derive(Debug, Clone)]
pub struct TextRegion {
    pub bounding_box: BoundingBox,
    pub text: Option<String>,
    pub confidence: Option<f32>,
}

#[derive(Debug, Clone)]
pub struct OcrResult {
    pub text_regions: Vec<TextRegion>,
}

pub struct OAROCR {
    detector: Detector,
    recognizer: Recognizer,
    #[allow(dead_code)]
    classifier: Option<Classifier>,
    #[allow(dead_code)]
    use_cls: bool,
}

pub struct OAROCRBuilder {
    det_model_path: Option<String>,
    rec_model_path: Option<String>,
    dict_path: Option<String>,
    cls_model_path: Option<String>,
    use_cls: bool,
}

impl OAROCRBuilder {
    pub fn new(det_path: &str, rec_path: &str, dict_path: &str) -> Self {
        Self {
            det_model_path: Some(det_path.to_string()),
            rec_model_path: Some(rec_path.to_string()),
            dict_path: Some(dict_path.to_string()),
            cls_model_path: None,
            use_cls: true,
        }
    }

    pub fn with_cls(mut self, cls_path: &str) -> Self {
        self.cls_model_path = Some(cls_path.to_string());
        self
    }

    pub fn use_cls(mut self, use_cls: bool) -> Self {
        self.use_cls = use_cls;
        self
    }

    pub fn build(self) -> Result<OAROCR, OcrError> {
        let det_path = self.det_model_path.ok_or_else(|| OcrError::ModelNotFound("Detection model path not set".to_string()))?;
        let rec_path = self.rec_model_path.ok_or_else(|| OcrError::ModelNotFound("Recognition model path not set".to_string()))?;
        let dict_path = self.dict_path.ok_or_else(|| OcrError::DictNotFound("Dictionary path not set".to_string()))?;

        let detector = Detector::new(Path::new(&det_path))?;
        let recognizer = Recognizer::new(Path::new(&rec_path), Path::new(&dict_path))?;

        let classifier = if let Some(cls_path) = self.cls_model_path {
            Some(Classifier::new(Path::new(&cls_path))?)
        } else {
            None
        };

        Ok(OAROCR {
            detector,
            recognizer,
            classifier,
            use_cls: self.use_cls,
        })
    }
}

impl OAROCR {
    pub fn predict(&self, images: Vec<RgbImage>) -> Result<Vec<OcrResult>, OcrError> {
        images
            .into_iter()
            .map(|img| self.predict_single(&img))
            .collect()
    }

    pub fn predict_single(&self, img: &RgbImage) -> Result<OcrResult, OcrError> {
        let boxes = self.detector.detect(img)?;

        let mut crops: Vec<(usize, RgbImage)> = Vec::new();
        let mut regions: Vec<(usize, BoundingBox)> = Vec::new();

        for (i, box_) in boxes.iter().enumerate() {
            if let Some(crop) = self.crop_rotated(img, &box_.points) {
                crops.push((i, crop));
                regions.push((i, box_.clone()));
            }
        }

        let texts = self.recognizer.recognize(&crops.iter().map(|(_, c)| c).cloned().collect::<Vec<_>>())?;

        let mut text_regions: Vec<TextRegion> = crops
            .iter()
            .zip(texts.iter())
            .map(|((idx, _crop), (ref text, conf))| {
                let region_box = &regions.iter().find(|(i, _)| *i == *idx).unwrap().1;
                TextRegion {
                    bounding_box: region_box.clone(),
                    text: Some(text.clone()),
                    confidence: Some(*conf),
                }
            })
            .collect();

        text_regions.sort_by(|a, b| {
            let a_min_y = a.bounding_box.points.iter().map(|p| p.y).fold(f32::INFINITY, f32::min);
            let b_min_y = b.bounding_box.points.iter().map(|p| p.y).fold(f32::INFINITY, f32::min);
            let y_cmp = a_min_y.partial_cmp(&b_min_y).unwrap();
            if y_cmp != std::cmp::Ordering::Equal {
                y_cmp
            } else {
                let a_min_x = a.bounding_box.points.iter().map(|p| p.x).fold(f32::INFINITY, f32::min);
                let b_min_x = b.bounding_box.points.iter().map(|p| p.x).fold(f32::INFINITY, f32::min);
                a_min_x.partial_cmp(&b_min_x).unwrap()
            }
        });

        Ok(OcrResult { text_regions })
    }

    fn crop_rotated(&self, img: &RgbImage, pts: &[Point]) -> Option<RgbImage> {
        if pts.len() != 4 {
            return None;
        }

        let xs: Vec<f32> = pts.iter().map(|p| p.x).collect();
        let ys: Vec<f32> = pts.iter().map(|p| p.y).collect();

        let x_min = xs.iter().cloned().fold(f32::INFINITY, f32::min).max(0.0) as i32;
        let x_max = xs.iter().cloned().fold(f32::NEG_INFINITY, f32::max).min(img.width() as f32 - 1.0) as i32;
        let y_min = ys.iter().cloned().fold(f32::INFINITY, f32::min).max(0.0) as i32;
        let y_max = ys.iter().cloned().fold(f32::NEG_INFINITY, f32::max).min(img.height() as f32 - 1.0) as i32;

        if x_max <= x_min || y_max <= y_min {
            return None;
        }

        let (img_h, img_w) = img.dimensions();
        let x_min = x_min.max(0) as u32;
        let x_max = x_max.min(img_w as i32) as u32;
        let y_min = y_min.max(0) as u32;
        let y_max = y_max.min(img_h as i32) as u32;

        let crop_w = (x_max - x_min) as u32;
        let crop_h = (y_max - y_min) as u32;

        if crop_w == 0 || crop_h == 0 {
            return None;
        }

        let mut crop: RgbImage = ImageBuffer::new(crop_w, crop_h);

        for y in 0..crop_h {
            for x in 0..crop_w {
                let src_x = (x_min + x).min(img_w - 1);
                let src_y = (y_min + y).min(img_h - 1);
                *crop.get_pixel_mut(x, y) = *img.get_pixel(src_x, src_y);
            }
        }

        Some(crop)
    }
}
