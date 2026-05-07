use std::io;
use std::path::Path;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum OcrError {
    #[error("Download error: {0}")]
    Download(String),
    #[error("IO error: {0}")]
    Io(#[from] io::Error),
}

pub fn download_file(url: &str, dest: &Path, verbose: bool) -> Result<(), OcrError> {
    let client = reqwest::blocking::Client::builder()
        .proxy(reqwest::Proxy::https("http://127.0.0.1:7890").unwrap())
        .proxy(reqwest::Proxy::http("http://127.0.0.1:7890").unwrap())
        .build()
        .map_err(|e| OcrError::Download(e.to_string()))?;

    let mut response = client.get(url)
        .send()
        .map_err(|e| OcrError::Download(format!("Failed to send request: {}", e)))?;

    if !response.status().is_success() {
        return Err(OcrError::Download(format!("HTTP {}", response.status())));
    }

    let total_size = response.content_length().unwrap_or(0);
    if verbose {
        println!("  Size: {:.1} MB", total_size as f64 / 1_048_576.0);
    }

    let mut dest_file = std::fs::File::create(dest)?;

    std::io::copy(&mut response, &mut dest_file)?;

    if verbose {
        println!("  Download complete: {} bytes", total_size);
    }

    Ok(())
}
