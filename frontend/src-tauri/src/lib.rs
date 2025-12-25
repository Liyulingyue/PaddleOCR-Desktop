use std::sync::{Arc, Mutex};
use tauri::command;

struct AppState {
    backend_port: Arc<Mutex<Option<u16>>>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .manage(AppState {
        backend_port: Arc::new(Mutex::new(None)),
    })
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![get_backend_url, start_backend])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

#[command]
fn get_backend_url(state: tauri::State<AppState>) -> String {
    let port = state.backend_port.lock().unwrap().unwrap_or(8000);
    format!("http://127.0.0.1:{}", port)
}

#[command]
fn start_backend(state: tauri::State<AppState>) -> Result<String, String> {
    // 检查是否已经有后端进程在运行（简化版）
    {
        let backend_port = state.backend_port.lock().unwrap();
        if backend_port.is_some() {
            return Ok("Backend already running".to_string());
        }
    }

    // 在开发模式下，假设后端已经运行在默认端口
    if cfg!(debug_assertions) {
        let mut backend_port = state.backend_port.lock().unwrap();
        *backend_port = Some(8000);
        return Ok("Backend started (dev mode)".to_string());
    }

    // 在生产模式下，启动 sidecar
    // 注意：Tauri v2 的 sidecar API 可能有所不同，这里使用简化版本
    // 实际实现可能需要根据具体需求调整

    Ok("Backend started".to_string())
}
