use std::path::PathBuf;
use std::process::Stdio;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::RwLock;
use tokio::time::timeout;

use crate::error::Result;
use crate::models::LlamaModelInfo;

const LLAMA_SERVER_STARTUP_TIMEOUT: Duration = Duration::from_secs(30);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlamaServerConfig {
    pub model_path: PathBuf,
    pub mmproj_path: Option<PathBuf>,
    pub host: String,
    pub port: u16,
    pub ctx_size: u32,
    pub n_gpu_layers: Option<i32>,
    pub n_threads: Option<u32>,
    pub batch_size: Option<u32>,
    pub flash_attention: bool,
    pub additional_args: Vec<String>,
}

impl Default for LlamaServerConfig {
    fn default() -> Self {
        Self {
            model_path: PathBuf::new(),
            mmproj_path: None,
            host: "127.0.0.1".to_string(),
            port: 8080,
            ctx_size: 8192,
            n_gpu_layers: None,
            n_threads: None,
            batch_size: None,
            flash_attention: true,
            additional_args: Vec::new(),
        }
    }
}

impl LlamaServerConfig {
    pub fn from_model(model: &LlamaModelInfo, port: u16) -> Self {
        Self {
            model_path: model.path.clone(),
            mmproj_path: model.mmproj_path.clone(),
            port,
            ..Default::default()
        }
    }

    pub fn build_args(&self) -> Vec<String> {
        let mut args = vec![
            "-m".to_string(),
            self.model_path.to_string_lossy().to_string(),
            "--host".to_string(),
            self.host.clone(),
            "--port".to_string(),
            self.port.to_string(),
            "-c".to_string(),
            self.ctx_size.to_string(),
            "--log-disable".to_string(),
        ];

        if let Some(ref mmproj) = self.mmproj_path {
            args.push("--mmproj".to_string());
            args.push(mmproj.to_string_lossy().to_string());
        }

        if let Some(n_gpu) = self.n_gpu_layers {
            args.push("--n-gpu-layers".to_string());
            args.push(n_gpu.to_string());
        }

        if let Some(n_threads) = self.n_threads {
            args.push("-t".to_string());
            args.push(n_threads.to_string());
        }

        if let Some(bs) = self.batch_size {
            args.push("-b".to_string());
            args.push(bs.to_string());
        }

        if self.flash_attention {
            args.push("-fa".to_string());
        }

        args.extend(self.additional_args.iter().cloned());
        args
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerStatus {
    pub running: bool,
    pub server_url: Option<String>,
    pub pid: Option<u32>,
    pub model_name: Option<String>,
    pub model_path: Option<String>,
    pub config: Option<LlamaServerConfig>,
}

impl Default for ServerStatus {
    fn default() -> Self {
        Self {
            running: false,
            server_url: None,
            pid: None,
            model_name: None,
            model_path: None,
            config: None,
        }
    }
}

pub struct LlamaServerManager {
    process: RwLock<Option<Child>>,
    status: RwLock<ServerStatus>,
    llama_server_path: RwLock<Option<PathBuf>>,
}

impl LlamaServerManager {
    pub fn new() -> Self {
        Self {
            process: RwLock::new(None),
            status: RwLock::new(ServerStatus::default()),
            llama_server_path: RwLock::new(None),
        }
    }

    pub async fn find_llama_server(&self) -> Result<PathBuf> {
        {
            let guard = self.llama_server_path.read().await;
            if let Some(ref path) = *guard {
                return Ok(path.clone());
            }
        }

        if let Ok(env_path) = std::env::var("LLAMA_SERVER_PATH") {
            if !env_path.is_empty() {
                let path = PathBuf::from(&env_path);
                if path.exists() && path.is_file() {
                    let mut guard = self.llama_server_path.write().await;
                    *guard = Some(path.clone());
                    return Ok(path);
                }
            }
        }

        if let Ok(env_path) = std::env::var("LLAMA_MANAGER_LLAMA_SERVER_PATH") {
            let path = PathBuf::from(&env_path);
            if path.exists() && path.is_file() {
                let mut guard = self.llama_server_path.write().await;
                *guard = Some(path.clone());
                return Ok(path);
            }
        }

        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let project_root = manifest_dir.parent().and_then(|p| p.parent()).unwrap_or(&manifest_dir);
        let bin_dir = if cfg!(target_os = "windows") { "build/Release/bin" } else { "build/bin" };
        let submodule_path = project_root
            .join("third_party")
            .join("llama.cpp")
            .join(bin_dir)
            .join(if cfg!(target_os = "windows") { "llama-server.exe" } else { "llama-server" });

        if submodule_path.exists() && submodule_path.is_file() {
            let mut guard = self.llama_server_path.write().await;
            *guard = Some(submodule_path.clone());
            return Ok(submodule_path);
        }

        let search_paths = if cfg!(target_os = "windows") {
            vec![
                PathBuf::from("../../third_party/llama.cpp/build/Release/bin/llama-server.exe"),
                PathBuf::from("../../../third_party/llama.cpp/build/Release/bin/llama-server.exe"),
                PathBuf::from("llama-server.exe"),
            ]
        } else {
            vec![
                PathBuf::from("../../third_party/llama.cpp/build/bin/llama-server"),
                PathBuf::from("../../../third_party/llama.cpp/build/bin/llama-server"),
                PathBuf::from("./llama-server"),
            ]
        };

        for path in &search_paths {
            if path.exists() && path.is_file() {
                let mut guard = self.llama_server_path.write().await;
                *guard = Some(path.clone());
                return Ok(path.clone());
            }
        }

        Err(crate::error::LlamaManagerError::ConfigError(
            "llama-server binary not found. Build it with: cd third_party/llama.cpp && cmake -B build && cmake --build build --config Release --target llama-server".to_string(),
        ))
    }

    pub async fn set_llama_server_path(&self, path: PathBuf) {
        let mut guard = self.llama_server_path.write().await;
        *guard = Some(path);
    }

    pub async fn start(&self, config: LlamaServerConfig) -> Result<String> {
        {
            let status = self.status.read().await;
            if status.running {
                return Err(crate::error::LlamaManagerError::AlreadyRunning(
                    status.server_url.clone().unwrap_or_default(),
                ));
            }
        }

        let server_path = self.find_llama_server().await?;
        let args = config.build_args();

        tracing::info!("Starting llama-server: {:?} {:?}", server_path, args);

        let mut child = Command::new(&server_path)
            .args(&args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true)
            .spawn()
            .map_err(|e| crate::error::LlamaManagerError::ProcessError(e.to_string()))?;

        let stdout = child.stdout.take().ok_or_else(|| {
            crate::error::LlamaManagerError::ProcessError("Failed to capture stdout".to_string())
        })?;

        let server_url = format!("http://{}:{}", config.host, config.port);
        let pid = child.id();

        tokio::spawn(Self::log_output(stdout, server_url.clone()));

        let check_url = server_url.clone();
        let result: std::result::Result<(), tokio::time::error::Elapsed> =
            timeout(LLAMA_SERVER_STARTUP_TIMEOUT, async move {
                loop {
                    match reqwest::get(&format!("{}/health", check_url)).await {
                        Ok(resp) if resp.status().is_success() => {
                            tracing::info!("llama-server is ready at {}", check_url);
                            return;
                        }
                        _ => {
                            tokio::time::sleep(Duration::from_millis(500)).await;
                        }
                    }
                }
            })
            .await;

        if let Err(e) = result {
            let _ = child.kill().await;
            return Err(crate::error::LlamaManagerError::ServerError(format!(
                "llama-server failed to start within {}s: {}",
                LLAMA_SERVER_STARTUP_TIMEOUT.as_secs(),
                e
            )));
        }

        let mut status = self.status.write().await;
        *status = ServerStatus {
            running: true,
            server_url: Some(server_url.clone()),
            pid,
            model_name: config.model_path.file_name().map(|s| s.to_string_lossy().to_string()),
            model_path: Some(config.model_path.to_string_lossy().to_string()),
            config: Some(config),
        };

        let mut process_guard = self.process.write().await;
        *process_guard = Some(child);

        Ok(server_url)
    }

    pub async fn stop(&self) -> Result<()> {
        let mut process_guard = self.process.write().await;
        if let Some(ref mut child) = *process_guard {
            tracing::info!("Stopping llama-server (PID: {:?})", child.id());
            child.kill().await.map_err(|e| {
                crate::error::LlamaManagerError::ProcessError(format!("Failed to kill process: {}", e))
            })?;
            let _ = child.wait().await;
        }
        *process_guard = None;

        let mut status = self.status.write().await;
        *status = ServerStatus::default();

        Ok(())
    }

    pub async fn get_status(&self) -> ServerStatus {
        let status = self.status.read().await;
        status.clone()
    }

    pub async fn get_server_url(&self) -> Option<String> {
        let status = self.status.read().await;
        if status.running {
            status.server_url.clone()
        } else {
            None
        }
    }

    pub async fn is_ready(&self) -> bool {
        let url = match self.get_server_url().await {
            Some(url) => url,
            None => return false,
        };
        matches!(
            reqwest::get(&format!("{}/health", url)).await,
            Ok(resp) if resp.status().is_success()
        )
    }

    async fn log_output(stdout: tokio::process::ChildStdout, url: String) {
        let mut reader = BufReader::new(stdout).lines();
        while let Ok(Some(line)) = reader.next_line().await {
            tracing::debug!("[llama-server {}] {}", url, line);
        }
    }
}

impl Default for LlamaServerManager {
    fn default() -> Self {
        Self::new()
    }
}
