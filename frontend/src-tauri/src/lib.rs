use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};
use tauri::command;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
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
    .invoke_handler(tauri::generate_handler![start_backend])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

#[command]
async fn start_backend() -> Result<u16, String> {
  // 获取当前可执行文件的目录，然后找到resources目录
  let exe_path = std::env::current_exe()
    .map_err(|e| format!("Failed to get current exe path: {}", e))?;

  let exe_dir = exe_path.parent()
    .ok_or("Failed to get exe directory")?;

  // 在开发模式下，从src-tauri目录查找
  // 在生产模式下，从resources目录查找
  let backend_exe = if cfg!(debug_assertions) {
    exe_dir.join("paddleocr_backend.exe")
  } else {
    exe_dir.join("resources").join("paddleocr_backend.exe")
  };

  if !backend_exe.exists() {
    return Err(format!("Backend executable not found at: {:?}", backend_exe));
  }

  // 启动后端进程
  let mut command = Command::new(&backend_exe);
  if !cfg!(debug_assertions) {
    command.env("PRODUCTION", "1");
  }
  let mut child = command
    .stdout(Stdio::piped())
    .stderr(Stdio::piped())
    .spawn()
    .map_err(|e| format!("Failed to start backend process: {}", e))?;

  // 读取stdout，查找PORT:xxxx格式的输出
  if let Some(stdout) = child.stdout.take() {
    let reader = BufReader::new(stdout);
    for line in reader.lines() {
      match line {
        Ok(line) => {
          if line.starts_with("PORT:") {
            if let Some(port_str) = line.strip_prefix("PORT:") {
              if let Ok(port) = port_str.trim().parse::<u16>() {
                // 在后台继续运行进程
                std::thread::spawn(move || {
                  let _ = child.wait();
                });
                return Ok(port);
              }
            }
          }
        }
        Err(_) => break,
      }
    }
  }

  Err("Failed to get port from backend process".to_string())
}
