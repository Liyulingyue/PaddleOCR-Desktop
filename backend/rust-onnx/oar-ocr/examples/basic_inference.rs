use oar_ocr::prelude::*;
use std::env;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();

    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <image_path> [det_model] [rec_model] [dict_path] [cls_model]", args[0]);
        eprintln!("Example: {} test.jpg ../models/ppocrv5/pp-ocrv5_mobile_det.onnx ../models/ppocrv5/pp-ocrv5_mobile_rec.onnx ../models/ppocrv5/ppocrv5_dict.txt", args[0]);
        return Ok(());
    }

    let image_path = &args[1];
    let (det_path, rec_path, dict_path, cls_path) = if args.len() >= 5 {
        (args[2].clone(), args[3].clone(), args[4].clone(),
         args.get(5).cloned())
    } else {
        let model_dir = env::var("OCR_MODEL_DIR").unwrap_or_else(|_| "../../models/ppocrv5".to_string());
        (
            format!("{}/pp-ocrv5_mobile_det.onnx", model_dir),
            format!("{}/pp-ocrv5_mobile_rec.onnx", model_dir),
            format!("{}/ppocrv5_dict.txt", model_dir),
            None,
        )
    };

    println!("Loading models...");
    println!("  Detection: {}", det_path);
    println!("  Recognition: {}", rec_path);
    println!("  Dictionary: {}", dict_path);
    if let Some(ref cp) = cls_path {
        println!("  Classifier: {}", cp);
    }
    println!("  Image: {}", image_path);

    let img = image::open(image_path)?.to_rgb8();
    println!("Image size: {}x{}", img.width(), img.height());

    let mut builder = OAROCRBuilder::new(&det_path, &rec_path, &dict_path);
    if let Some(ref cp) = cls_path {
        builder = builder.with_cls(cp);
    }

    println!("Building OCR model...");
    let ocr = builder.build().map_err(|e| format!("Failed to build OCR: {}", e))?;

    println!("Running OCR inference...");
    let start = std::time::Instant::now();
    let results = ocr.predict(vec![img]).map_err(|e| format!("OCR failed: {}", e))?;
    let elapsed = start.elapsed();
    println!("Inference time: {:.2}s", elapsed.as_secs_f64());

    let result = &results[0];
    println!("\nDetected {} text regions:", result.text_regions.len());
    println!("{}", "=".repeat(60));

    for (i, region) in result.text_regions.iter().enumerate() {
        let text = region.text.as_deref().unwrap_or("[no text]");
        let conf = region.confidence.unwrap_or(0.0);

        let bbox = &region.bounding_box;
        let pts = &bbox.points;
        let x_min = pts.iter().map(|p| p.x).fold(f32::INFINITY, f32::min) as i32;
        let y_min = pts.iter().map(|p| p.y).fold(f32::INFINITY, f32::min) as i32;
        let x_max = pts.iter().map(|p| p.x).fold(f32::NEG_INFINITY, f32::max) as i32;
        let y_max = pts.iter().map(|p| p.y).fold(f32::NEG_INFINITY, f32::max) as i32;

        println!("[{}] \"{}\" (conf: {:.2}) @ [{}, {}, {}, {}]",
            i + 1, text, conf, x_min, y_min, x_max, y_max);
    }

    println!("{}", "=".repeat(60));
    println!("Done!");

    Ok(())
}
