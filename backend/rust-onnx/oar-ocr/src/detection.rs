use std::sync::{Arc, Mutex};
use image::RgbImage;
use ort::session::Session;
use ort::value::Tensor;
use std::path::Path;

use crate::error::OcrError;
use crate::ort_utils::OrtSession;

const DET_IMAGE_SIZE: i32 = 736;
const DET_STRIDE: i32 = 8;

#[derive(Debug, Clone)]
pub struct BoundingBox {
    pub points: Vec<Point>,
}

#[derive(Debug, Clone, Copy)]
pub struct Point {
    pub x: f32,
    pub y: f32,
}

pub struct Detector {
    session: Arc<Mutex<Session>>,
    stride: i32,
    thresh: f32,
}

impl Detector {
    pub fn new(model_path: &Path) -> Result<Self, OcrError> {
        let ort_session = OrtSession::new(model_path)?;
        Ok(Self {
            session: ort_session.session,
            stride: DET_STRIDE,
            thresh: 0.3,
        })
    }

    pub fn set_thresh(&mut self, thresh: f32) {
        self.thresh = thresh;
    }

    pub fn detect(&self, img: &RgbImage) -> Result<Vec<BoundingBox>, OcrError> {
        let (h, w) = img.dimensions();
        let (ratio_h, ratio_w) = (DET_IMAGE_SIZE as f32 / h as f32, DET_IMAGE_SIZE as f32 / w as f32);

        let resized = self.resize_image(img, DET_IMAGE_SIZE as u32, DET_IMAGE_SIZE as u32);
        let input_tensor = self.image_to_tensor(&resized)?;

        let (out_h, out_w, pred) = {
            let mut guard = self.session.lock().map_err(|e| OcrError::Detection(format!("lock error: {}", e)))?;
            let outputs = guard.run(ort::inputs![input_tensor])
                .map_err(|e| OcrError::Detection(format!("run error: {}", e)))?;

            let output_arr = outputs[0]
                .try_extract_array::<f32>()
                .map_err(|e| OcrError::Detection(format!("extract error: {}", e)))?;

            let shape = output_arr.shape();
            let out_h = shape[1] as i32;
            let out_w = shape[2] as i32;

            let mut pred = vec![0u8; out_h as usize * out_w as usize];
            for y in 0..out_h as usize {
                for x in 0..out_w as usize {
                    let idx = y * out_w as usize + x;
                    pred[idx] = if output_arr[[0, y, x]] > self.thresh { 255 } else { 0 };
                }
            }
            (out_h, out_w, pred)
        };

        let boxes = self.post_process(&pred, out_h, out_w, ratio_h, ratio_w, h, w);
        Ok(boxes)
    }

    fn resize_image(&self, img: &RgbImage, target_h: u32, target_w: u32) -> RgbImage {
        image::imageops::resize(img, target_w, target_h, image::imageops::FilterType::Triangle)
    }

    fn image_to_tensor(&self, img: &RgbImage) -> Result<Tensor<f32>, OcrError> {
        let (h, w) = img.dimensions();
        let mut data = ndarray::Array4::<f32>::zeros((1, 3, h as usize, w as usize));

        for y in 0..h {
            for x in 0..w {
                let pixel = img.get_pixel(x, y);
                data[[0, 0, y as usize, x as usize]] = (pixel[0] as f32 - 127.5) / 127.5;
                data[[0, 1, y as usize, x as usize]] = (pixel[1] as f32 - 127.5) / 127.5;
                data[[0, 2, y as usize, x as usize]] = (pixel[2] as f32 - 127.5) / 127.5;
            }
        }

        Tensor::from_array(data).map_err(|e| OcrError::Detection(format!("tensor error: {}", e)))
    }

    fn post_process(
        &self,
        pred: &[u8],
        out_h: i32,
        out_w: i32,
        ratio_h: f32,
        ratio_w: f32,
        img_h: u32,
        img_w: u32,
    ) -> Vec<BoundingBox> {
        let w = out_w;
        let w_us = w as usize;

        let mut boxes: Vec<BoundingBox> = Vec::new();

        for y in 0..out_h {
            for x in 0..out_w {
                if pred[(y as usize * w_us) + (x as usize)] == 0 {
                    continue;
                }

                let mut contour = vec![Point { x: x as f32, y: y as f32 }];
                self.expand_contour(pred, out_h, w, x, y, &mut contour, 2);

                if contour.len() < self.stride as usize * 3 {
                    continue;
                }

                let box_pts = self.shrink_box(&contour);
                let area = self.polygon_area(&box_pts);
                if area < 16.0 {
                    continue;
                }

                let min_x = box_pts.iter().map(|p| p.x).fold(f32::INFINITY, f32::min);
                let max_x = box_pts.iter().map(|p| p.x).fold(f32::NEG_INFINITY, f32::max);
                let min_y = box_pts.iter().map(|p| p.y).fold(f32::INFINITY, f32::min);
                let max_y = box_pts.iter().map(|p| p.y).fold(f32::NEG_INFINITY, f32::max);

                let pts = vec![
                    Point { x: min_x, y: min_y },
                    Point { x: max_x, y: min_y },
                    Point { x: max_x, y: max_y },
                    Point { x: min_x, y: max_y },
                ];

                let scaled: Vec<Point> = pts
                    .iter()
                    .map(|p| Point {
                        x: (p.x * self.stride as f32 / ratio_w).min(img_w as f32 - 1.0).max(0.0),
                        y: (p.y * self.stride as f32 / ratio_h).min(img_h as f32 - 1.0).max(0.0),
                    })
                    .collect();

                boxes.push(BoundingBox { points: scaled });
            }
        }

        boxes.sort_by(|a, b| {
            let a_min_x = a.points.iter().map(|p| p.x).fold(f32::INFINITY, f32::min);
            let b_min_x = b.points.iter().map(|p| p.x).fold(f32::INFINITY, f32::min);
            a_min_x.partial_cmp(&b_min_x).unwrap()
        });

        let mut filtered: Vec<BoundingBox> = Vec::new();
        for box_a in boxes {
            let mut keep = true;
            for box_b in &filtered {
                if self.boxes_overlap(&box_a, box_b, 0.8) {
                    keep = false;
                    break;
                }
            }
            if keep {
                filtered.push(box_a);
            }
        }

        filtered
    }

    fn expand_contour(
        &self,
        pred: &[u8],
        h: i32,
        w: i32,
        x: i32,
        y: i32,
        contour: &mut Vec<Point>,
        border: i32,
    ) {
        let mut stack = vec![(x, y)];
        let mut visited = vec![vec![false; w as usize]; h as usize];

        while let Some((cx, cy)) = stack.pop() {
            if cx < 0 || cx >= w || cy < 0 || cy >= h {
                continue;
            }
            if visited[cy as usize][cx as usize] {
                continue;
            }
            if pred[(cy as usize * w as usize) + (cx as usize)] == 0 {
                continue;
            }

            visited[cy as usize][cx as usize] = true;
            contour.push(Point { x: cx as f32, y: cy as f32 });

            for dy in -border..=border {
                for dx in -border..=border {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    let nx = cx + dx;
                    let ny = cy + dy;
                    if nx >= 0 && nx < w && ny >= 0 && ny < h && !visited[ny as usize][nx as usize] {
                        stack.push((nx, ny));
                    }
                }
            }
        }
    }

    fn shrink_box(&self, contour: &[Point]) -> Vec<Point> {
        let xs: Vec<f32> = contour.iter().map(|p| p.x).collect();
        let ys: Vec<f32> = contour.iter().map(|p| p.y).collect();
        let x_min = xs.iter().cloned().fold(f32::INFINITY, f32::min);
        let x_max = xs.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let y_min = ys.iter().cloned().fold(f32::INFINITY, f32::min);
        let y_max = ys.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

        let shrink = 2.0;
        vec![
            Point { x: x_min + shrink, y: y_min + shrink },
            Point { x: x_max - shrink, y: y_min + shrink },
            Point { x: x_max - shrink, y: y_max - shrink },
            Point { x: x_min + shrink, y: y_max - shrink },
        ]
    }

    fn polygon_area(&self, pts: &[Point]) -> f32 {
        let n = pts.len();
        let mut area = 0.0;
        for i in 0..n {
            let j = (i + 1) % n;
            area += pts[i].x * pts[j].y;
            area -= pts[j].x * pts[i].y;
        }
        area.abs() / 2.0
    }

    fn boxes_overlap(&self, a: &BoundingBox, b: &BoundingBox, threshold: f32) -> bool {
        let a_xs: Vec<f32> = a.points.iter().map(|p| p.x).collect();
        let a_ys: Vec<f32> = a.points.iter().map(|p| p.y).collect();
        let b_xs: Vec<f32> = b.points.iter().map(|p| p.x).collect();
        let b_ys: Vec<f32> = b.points.iter().map(|p| p.y).collect();

        let a_x_min = a_xs.iter().cloned().fold(f32::INFINITY, f32::min);
        let a_x_max = a_xs.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let a_y_min = a_ys.iter().cloned().fold(f32::INFINITY, f32::min);
        let a_y_max = a_ys.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

        let b_x_min = b_xs.iter().cloned().fold(f32::INFINITY, f32::min);
        let b_x_max = b_xs.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let b_y_min = b_ys.iter().cloned().fold(f32::INFINITY, f32::min);
        let b_y_max = b_ys.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

        let inter_x_min = a_x_min.max(b_x_min);
        let inter_y_min = a_y_min.max(b_y_min);
        let inter_x_max = a_x_max.min(b_x_max);
        let inter_y_max = a_y_max.min(b_y_max);

        if inter_x_max <= inter_x_min || inter_y_max <= inter_y_min {
            return false;
        }

        let inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min);
        let a_area = (a_x_max - a_x_min) * (a_y_max - a_y_min);
        inter_area / a_area > threshold
    }
}
