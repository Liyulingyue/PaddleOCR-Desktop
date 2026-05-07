use oar_ocr::prelude::*;
use std::env;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: {} <image_path>", args[0]);
        return Ok(());
    }

    let image_path = &args[1];
    let models_dir = dirs::data_local_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join("oar-ocr")
        .join("models");

    println!("Initializing oar-ocr with auto-download...");
    println!("Models will be downloaded from GitHub (GreatV/oar-ocr releases v0.3.0)");
    println!();

    let (det_path, rec_path, dict_path) = ocr_wrapper::OcrDownloader::new(models_dir)
        .verbose(true)
        .ensure_models()?;

    println!("\nBuilding OCR pipeline...");
    let ocr = OAROCRBuilder::new(&det_path, &rec_path, &dict_path).build()?;

    println!("Loading image: {}", image_path);
    let img = oar_ocr::utils::load_image(std::path::Path::new(image_path))?;
    println!("Image loaded");

    println!("Running OCR inference...");
    let start = std::time::Instant::now();
    let results = ocr.predict(vec![img])?;
    let elapsed = start.elapsed();
    println!("Inference time: {:.2}s", elapsed.as_secs_f64());

    let result = &results[0];
    println!("\nDetected {} text regions:", result.text_regions.len());
    println!("{}", "=".repeat(60));

    for (i, region) in result.text_regions.iter().enumerate() {
        let text = region.text.as_deref().unwrap_or("[no text]");
        let conf = region.confidence.unwrap_or(0.0);
        println!("[{}] \"{}\" (conf: {:.2})", i + 1, text, conf);
    }

    println!("{}", "=".repeat(60));
    println!("Done!");

    Ok(())
}
