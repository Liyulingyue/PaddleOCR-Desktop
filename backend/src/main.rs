use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use axum_extra::extract::Multipart;
use image::ImageFormat;
use oar_ocr::oarocr::{OAROCR, OAROCRBuilder};
use serde::Serialize;
use std::sync::Arc;
use tokio::sync::OnceCell;

static OCR: OnceCell<Arc<OAROCR>> = OnceCell::const_new();

async fn get_ocr() -> &'static Arc<OAROCR> {
    OCR.get_or_init(|| async {
        let builder = OAROCRBuilder::new(
            "models/ppocrv4_mobile_det.onnx",
            "models/ppocrv4_mobile_rec.onnx",
            "models/ppocr_keys_v1.txt",
        )
        .build()
        .expect("Failed to build OAROCR");
        Arc::new(builder)
    })
    .await
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
}

#[derive(Serialize)]
struct OcrResponse {
    text: String,
}

async fn health_handler() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
    })
}

async fn ocr_handler(State(_): State<()>, mut multipart: Multipart) -> Result<Json<OcrResponse>, StatusCode> {
    let ocr = get_ocr().await;

    while let Some(field) = multipart.next_field().await.map_err(|_| StatusCode::BAD_REQUEST)? {
        if field.name() == Some("image") {
            let data = field.bytes().await.map_err(|_| StatusCode::BAD_REQUEST)?;
            let img = image::load_from_memory_with_format(&data, ImageFormat::Png)
                .or_else(|_| image::load_from_memory_with_format(&data, ImageFormat::Jpeg))
                .or_else(|_| image::load_from_memory_with_format(&data, ImageFormat::WebP))
                .map_err(|_| StatusCode::BAD_REQUEST)?
                .to_rgb8();

            let result = ocr.predict(vec![img]).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
            let mut text = String::new();
            for res in result {
                for region in &res.text_regions {
                    if let Some((t, _)) = region.text_with_confidence() {
                        text.push_str(&t);
                        text.push('\n');
                    }
                }
            }
            return Ok(Json(OcrResponse { text }));
        }
    }

    Err(StatusCode::BAD_REQUEST)
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/ocr", post(ocr_handler));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    println!("Server running on http://0.0.0.0:3000");
    axum::serve(listener, app).await.unwrap();
}