use actix_multipart::Multipart;
use actix_web::{web, App, HttpResponse, HttpServer, Responder, get, post, middleware::Logger};
use futures::{StreamExt, TryStreamExt};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::env;

#[cfg(feature = "with-ocr")]
use oar_ocr::prelude::*;
use image::{load_from_memory, ImageEncoder};
use image::codecs::png::PngEncoder;
use image::ColorType;
use env_logger;

#[cfg(feature = "with-ocr")]
type OcrInner = Arc<OAROCR>;

#[cfg(not(feature = "with-ocr"))]
type OcrInner = ();

#[derive(Clone)]
struct AppState {
    // Store OCR pipeline as Arc so it can be cloned cheaply across handlers
    ocr: Arc<Mutex<Option<OcrInner>>>,
}

#[derive(Serialize)]
struct Message { message: String }

#[derive(Serialize)]
struct ModelStatus { loaded: bool }

#[get("/api/health/")]
async fn health() -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({"status": "ok"}))
}

// Load model: uses environment variable OCR_MODEL_DIR or a default models path
#[cfg(feature = "with-ocr")]
#[post("/api/ocr/load")]
async fn load_model(state: web::Data<AppState>) -> impl Responder {
    let model_dir = env::var("OCR_MODEL_DIR").unwrap_or_else(|_| {
        // default relative path from repo: backend/rust-onnx/models/ppocrv5
        // this can be overridden by OCR_MODEL_DIR
        "../models/ppocrv5".to_string()
    });

    let det = format!("{}/pp-ocrv5_mobile_det.onnx", model_dir);
    let rec = format!("{}/pp-ocrv5_mobile_rec.onnx", model_dir);
    let dict = format!("{}/ppocrv5_dict.txt", model_dir);

    match OAROCRBuilder::new(&det, &rec, &dict).build() {
        Ok(ocr) => {
            let arc_ocr = Arc::new(ocr);
            let mut guard = state.ocr.lock().unwrap();
            *guard = Some(arc_ocr);
            HttpResponse::Ok().json(Message{ message: "OCR model loaded successfully".into() })
        }
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("Failed to build model: {}", e)})),
    }
}

#[cfg(not(feature = "with-ocr"))]
#[post("/api/ocr/load")]
async fn load_model(_state: web::Data<AppState>) -> impl Responder {
    HttpResponse::NotImplemented().json(serde_json::json!({"error":"ocr-service built without feature 'with-ocr'; enable it to use native OCR"}))
}

#[cfg(feature = "with-ocr")]
#[post("/api/ocr/unload")]
async fn unload_model(state: web::Data<AppState>) -> impl Responder {
    let mut guard = state.ocr.lock().unwrap();
    *guard = None;
    HttpResponse::Ok().json(Message{ message: "OCR model unloaded".into() })
}

#[cfg(not(feature = "with-ocr"))]
#[post("/api/ocr/unload")]
async fn unload_model(_state: web::Data<AppState>) -> impl Responder {
    HttpResponse::NotImplemented().json(serde_json::json!({"error":"ocr-service built without feature 'with-ocr'; enable it to use native OCR"}))
}

#[cfg(feature = "with-ocr")]
#[get("/api/ocr/model_status")]
async fn model_status(state: web::Data<AppState>) -> impl Responder {
    let guard = state.ocr.lock().unwrap();
    HttpResponse::Ok().json(ModelStatus{ loaded: guard.is_some() })
}

#[cfg(not(feature = "with-ocr"))]
#[get("/api/ocr/model_status")]
async fn model_status(_state: web::Data<AppState>) -> impl Responder {
    HttpResponse::Ok().json(serde_json::json!({"loaded": false, "note": "ocr-service built without feature 'with-ocr'"}))
}

/// Accepts multipart form with `file` and optional form fields:
/// det_db_thresh (f32), cls_thresh (f32), use_cls (bool)
#[cfg(feature = "with-ocr")]
#[post("/api/ocr/")]
async fn recognize(mut payload: Multipart, state: web::Data<AppState>) -> impl Responder {
    // collect fields
    let mut file_bytes: Option<Vec<u8>> = None;
    let mut det_db_thresh: f32 = 0.3;
    let mut cls_thresh: f32 = 0.9;
    let mut use_cls: bool = true;

    while let Ok(Some(mut field)) = payload.try_next().await {
        let content_disposition = field.content_disposition();
        let name = content_disposition
            .get_name()
            .map(|s| s.to_string())
            .unwrap_or_default();

        if name == "file" {
            let mut data = Vec::new();
            while let Some(chunk) = field.next().await {
                let chunk = chunk.unwrap();
                data.extend_from_slice(&chunk);
            }
            file_bytes = Some(data);
        } else if name == "det_db_thresh" {
            let mut d = Vec::new();
            while let Some(chunk) = field.next().await { d.extend_from_slice(&chunk.unwrap()); }
            if let Ok(s) = std::str::from_utf8(&d) { if let Ok(v) = s.parse::<f32>() { det_db_thresh = v; } }
        } else if name == "cls_thresh" {
            let mut d = Vec::new();
            while let Some(chunk) = field.next().await { d.extend_from_slice(&chunk.unwrap()); }
            if let Ok(s) = std::str::from_utf8(&d) { if let Ok(v) = s.parse::<f32>() { cls_thresh = v; } }
        } else if name == "use_cls" {
            let mut d = Vec::new();
            while let Some(chunk) = field.next().await { d.extend_from_slice(&chunk.unwrap()); }
            if let Ok(s) = std::str::from_utf8(&d) { if let Ok(v) = s.parse::<bool>() { use_cls = v; } }
        }
    }

    let bytes = match file_bytes { Some(b) => b, None => return HttpResponse::BadRequest().json(serde_json::json!({"error":"missing file"})), };

    // Note: PDF support is not implemented here. Return helpful error matching python behaviour.
    if let Ok(name) = infer_image_format(&bytes) {
        // OK image
    } else {
        return HttpResponse::BadRequest().json(serde_json::json!({"error":"Unsupported file type or PDF is not supported by Rust service yet"}));
    }

    // Decode image
    let dyn_img = match load_from_memory(&bytes) {
        Ok(d) => d.to_rgb8(),
        Err(e) => return HttpResponse::BadRequest().json(serde_json::json!({"error": format!("Failed to decode image: {}", e)})),
    };

    // Clone Arc<OAROCR> out of the lock then drop the lock before blocking.
    let arc_opt = {
        let guard = state.ocr.lock().unwrap();
        guard.as_ref().cloned()
    };
    let arc_ocr = match arc_opt {
        Some(a) => a,
        None => return HttpResponse::BadRequest().json(serde_json::json!({"error":"Model not loaded"})),
    };

    // Run OCR in blocking thread because predict is CPU-heavy
    let img_vec = vec![dyn_img.clone()];
    let arc_for_thread = arc_ocr.clone();
    let res = web::block(move || arc_for_thread.predict(img_vec)).await;
    let results = match res {
        Ok(Ok(mut vec_res)) => vec_res.remove(0),
        Ok(Err(e)) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("OCR error: {}", e)})),
        Err(e) => return HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("Task error: {}", e)})),
    };

    // Convert result into Python-compatible structure
    // Python format: {"result": [ [box_points, [text,score]], ... ] }
    let mut lines: Vec<serde_json::Value> = Vec::new();
    for region in results.text_regions.iter() {
        let box_points: Vec<Vec<f32>> = region.bounding_box.points.iter().map(|p| vec![p.x, p.y]).collect();
        let text = region.text.as_ref().map(|s| s.to_string()).unwrap_or_default();
        let score = region.confidence.unwrap_or(0.0);
        lines.push(serde_json::json!([box_points, [text, score]]));
    }

    HttpResponse::Ok().json(serde_json::json!({"result": [lines]}))
}

#[cfg(not(feature = "with-ocr"))]
#[post("/api/ocr/")]
async fn recognize(_payload: Multipart, _state: web::Data<AppState>) -> impl Responder {
    HttpResponse::NotImplemented().json(serde_json::json!({"error":"ocr-service built without feature 'with-ocr'; enable it to use native OCR"}))
}

// Very small helper to try to infer whether bytes are image-like
fn infer_image_format(bytes: &[u8]) -> Result<(), ()> {
    if image::guess_format(bytes).is_ok() { Ok(()) } else { Err(()) }
}

#[derive(Deserialize)]
struct OcrResultWrapper { result: serde_json::Value }

// draw endpoint: takes file + ocr_result (string JSON) and returns PNG image bytes
#[post("/api/ocr/draw")]
async fn draw(mut payload: Multipart, _state: web::Data<AppState>) -> impl Responder {
    let mut file_bytes: Option<Vec<u8>> = None;
    let mut ocr_result_str: Option<String> = None;
    let mut drop_score: f32 = 0.5;

    while let Ok(Some(mut field)) = payload.try_next().await {
        let name = field.content_disposition().get_name().unwrap_or("");
        if name == "file" {
            let mut data = Vec::new();
            while let Some(chunk) = field.next().await { data.extend_from_slice(&chunk.unwrap()); }
            file_bytes = Some(data);
        } else if name == "ocr_result" {
            let mut data = Vec::new();
            while let Some(chunk) = field.next().await { data.extend_from_slice(&chunk.unwrap()); }
            if let Ok(s) = String::from_utf8(data) { ocr_result_str = Some(s); }
        } else if name == "drop_score" {
            let mut d = Vec::new(); while let Some(chunk) = field.next().await { d.extend_from_slice(&chunk.unwrap()); }
            if let Ok(s) = std::str::from_utf8(&d) { if let Ok(v) = s.parse::<f32>() { drop_score = v; } }
        }
    }

    let bytes = match file_bytes { Some(b) => b, None => return HttpResponse::BadRequest().json(serde_json::json!({"error":"missing file"})), };
    let ocr_json = match ocr_result_str { Some(s) => s, None => return HttpResponse::BadRequest().json(serde_json::json!({"error":"missing ocr_result"})), };

    // decode image
    let dyn_img = match load_from_memory(&bytes) { Ok(d) => d.to_rgb8(), Err(e) => return HttpResponse::BadRequest().json(serde_json::json!({"error": format!("Failed to decode image: {}", e)})), };

    // parse ocr_result JSON and convert into the expected format used by visualization
    let parsed: serde_json::Value = match serde_json::from_str(&ocr_json) { Ok(v) => v, Err(e) => return HttpResponse::BadRequest().json(serde_json::json!({"error": format!("Invalid ocr_result JSON: {}", e)})), };

    // Build a minimal OAROCRResult that visualization functions can use would be heavy; for now use simple drawing: draw bounding boxes from parsed data
    use imageproc::drawing::draw_hollow_rect_mut;
    use imageproc::rect::Rect;
    use image::Rgb;

    let mut output = dyn_img.clone();
    if let Some(lines) = parsed.get("result") {
        // Expecting result to be [ lines ] (for single page)
        let lines_arr = if lines.is_array() && !lines.as_array().unwrap().is_empty() { &lines.as_array().unwrap()[0] } else { lines };
        if let Some(arr) = lines_arr.as_array() {
            for item in arr.iter() {
                // each item like [box_points, [text,score]]
                if let Some(box_points) = item.get(0) {
                    if let Some(pts) = box_points.as_array() {
                        // compute bounding rect
                        let xs: Vec<i32> = pts.iter().filter_map(|p| p.as_array().and_then(|pa| pa.get(0)).and_then(|x| x.as_f64()).map(|x| x as i32)).collect();
                        let ys: Vec<i32> = pts.iter().filter_map(|p| p.as_array().and_then(|pa| pa.get(1)).and_then(|y| y.as_f64()).map(|y| y as i32)).collect();
                        if !xs.is_empty() && !ys.is_empty() {
                            let x_min = *xs.iter().min().unwrap();
                            let x_max = *xs.iter().max().unwrap();
                            let y_min = *ys.iter().min().unwrap();
                            let y_max = *ys.iter().max().unwrap();
                            let rect = Rect::at(x_min, y_min).of_size((x_max - x_min) as u32, (y_max - y_min) as u32);
                            draw_hollow_rect_mut(&mut output, rect, Rgb([255u8, 0u8, 0u8]));
                        }
                    }
                }
            }
        }
    }

    // encode to png using PngEncoder
    let mut buf = Vec::new();
    let encode_res = {
        let w = output.width();
        let h = output.height();
        let data = output.as_raw();
        let mut encoder = PngEncoder::new(&mut buf);
        encoder.write_image(data, w, h, ColorType::Rgb8.into())
    };
    match encode_res {
        Ok(_) => HttpResponse::Ok().content_type("image/png").body(buf),
        Err(e) => HttpResponse::InternalServerError().json(serde_json::json!({"error": format!("Failed to encode PNG: {}", e)})),
    }
}

// ocr2text endpoint
#[post("/api/ocr/ocr2text")]
async fn ocr2text(body: web::Json<serde_json::Value>) -> impl Responder {
    // Mirror python behavior: accept {"result": ...}
    if body.get("result").is_none() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error":"Invalid OCR result format"}));
    }
    let result_data = body.get("result").unwrap();
    let mut all_text_lines: Vec<String> = Vec::new();

    // Detect multi-page result like [{"page":1, "result": [...]}, ...]
    if result_data.is_array() && !result_data.as_array().unwrap().is_empty() && result_data.as_array().unwrap()[0].is_object() && result_data.as_array().unwrap()[0].get("page").is_some() {
        for page in result_data.as_array().unwrap().iter() {
            let page_result = page.get("result").unwrap_or(&serde_json::Value::Null);
            if page_result.is_array() {
                if let Some(first) = page_result.get(0) {
                    if first.is_array() {
                        for line in first.as_array().unwrap().iter() {
                            if let Some(txt) = line.get(1).and_then(|t| t.get(0)).and_then(|s| s.as_str()) {
                                if !txt.trim().is_empty() { all_text_lines.push(txt.to_string()); }
                            }
                        }
                    }
                }
            }
        }
    } else {
        // single page expected: result[0] -> lines
        if result_data.is_array() && !result_data.as_array().unwrap().is_empty() {
            if let Some(page0) = result_data.as_array().unwrap().get(0) {
                if page0.is_array() {
                    for line in page0.as_array().unwrap().iter() {
                        if let Some(txt) = line.get(1).and_then(|t| t.get(0)).and_then(|s| s.as_str()) {
                            if !txt.trim().is_empty() { all_text_lines.push(txt.to_string()); }
                        }
                    }
                }
            }
        }
    }

    let full_text = all_text_lines.join("\n");
    HttpResponse::Ok().json(serde_json::json!({"text": full_text}))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    let state = AppState{ ocr: Arc::new(Mutex::new(None)) };

    HttpServer::new(move || {
        App::new()
            .wrap(Logger::default())
            .app_data(web::Data::new(state.clone()))
            .service(health)
            .service(load_model)
            .service(unload_model)
            .service(model_status)
            .service(recognize)
            .service(draw)
            .service(ocr2text)
    })
    .bind(("127.0.0.1", 8081))?
    .run()
    .await
}
