pub use oar_ocr::prelude::*;

mod download;
mod registry;

pub struct OcrDownloader {
    models_dir: std::path::PathBuf,
    verbose: bool,
}

impl OcrDownloader {
    pub fn new(models_dir: std::path::PathBuf) -> Self {
        Self { models_dir, verbose: true }
    }

    pub fn verbose(mut self, v: bool) -> Self {
        self.verbose = v;
        self
    }

    pub fn ensure_models(&self) -> Result<(std::path::PathBuf, std::path::PathBuf, std::path::PathBuf), Box<dyn std::error::Error>> {
        std::fs::create_dir_all(&self.models_dir)?;

        let det = self.models_dir.join(registry::default_detection().filename);
        let rec = self.models_dir.join(registry::default_recognition().filename);
        let dict = self.models_dir.join(registry::default_dict().filename);

        if self.verbose {
            println!("Models directory: {}", self.models_dir.display());
        }

        for (info, path) in [
            (registry::default_detection(), &det),
            (registry::default_recognition(), &rec),
            (registry::default_dict(), &dict),
        ] {
            if !path.exists() {
                println!("Downloading {} ({:.1} MB)...", info.filename, info.size_mb);
                download::download_file(info.url, path, self.verbose)?;
                println!("  -> {}", path.display());
            } else if self.verbose {
                println!("  [exists] {} ({:.1} MB)", info.filename, info.size_mb);
            }
        }

        Ok((det, rec, dict))
    }
}
