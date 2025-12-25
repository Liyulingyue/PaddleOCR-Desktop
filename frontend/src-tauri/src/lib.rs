// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, api::process::{Command, CommandEvent, CommandChild}};
use std::sync::{Arc, Mutex};
use std::io::Write;

struct AppState {
    backend_port: Arc<Mutex<Option<u16>>>,
    backend_child: Arc<Mutex<Option<CommandChild>>>,
}

// 从日志行中解析端口号
fn parse_port_from_line(line: &str) -> Option<u16> {
    println!("[调试] parse_port_from_line 输入: {}", line);

    // 优先检查 [PORT] 标记
    if line.contains("[PORT]") {
        // 提取 [PORT] 后面的数字
        if let Some(start) = line.find("[PORT]") {
            let after_tag = &line[start..];
            let numbers: String = after_tag.chars().filter(|c| c.is_numeric()).collect();
            if let Ok(port) = numbers.parse::<u16>() {
                if port > 1024 && port < 65535 {
                    println!("[调试] 从 [PORT] 标记找到有效端口: {}", port);
                    return Some(port);
                }
            }
        }
    }

    // 使用正则表达式的替代方案:提取所有连续的数字
    let mut numbers = Vec::new();
    let mut current_num = String::new();

    for ch in line.chars() {
        if ch.is_numeric() {
            current_num.push(ch);
        } else {
            if !current_num.is_empty() {
                if let Ok(num) = current_num.parse::<u16>() {
                    numbers.push(num);
                }
                current_num.clear();
            }
        }
    }
    // 处理最后一个数字
    if !current_num.is_empty() {
        if let Ok(num) = current_num.parse::<u16>() {
            numbers.push(num);
        }
    }

    println!("[调试] 提取到的所有数字: {:?}", numbers);

    // 查找有效的端口号(1024-65535)
    // 优先选择关键字明确的端口
    for num in &numbers {
        if *num > 1024 && *num < 65535 {
            if line.contains("port") || line.contains("端口") || line.contains("://127.0.0.1") {
                println!("[调试] 找到有效端口: {}", num);
                return Some(*num);
            }
        }
    }

    // 如果没有关键字,选择最后一个有效的端口号(通常是最相关的)
    for num in numbers.iter().rev() {
        if *num > 1024 && *num < 65535 {
            println!("[调试] 找到有效端口: {}", num);
            return Some(*num);
        }
    }

    println!("[调试] 未能从此行解析出有效端口");
    None
}

// 将日志追加到磁盘，并可选地推送到前端
fn append_log_message_and_emit(app_handle: Option<tauri::AppHandle>, msg: &str) {
    // 追加到文件
    if let Some(mut data_dir) = dirs::data_local_dir() {
        data_dir.push("PaddleOCRDesktop");
        let _ = std::fs::create_dir_all(&data_dir);
        data_dir.push("logs");
        let _ = std::fs::create_dir_all(&data_dir);
        data_dir.push("app.log");
        let now = std::time::SystemTime::now();
        let timestamp = match now.duration_since(std::time::UNIX_EPOCH) {
            Ok(d) => format!("{}", d.as_secs()),
            Err(_) => "0".to_string(),
        };
        let entry = format!("{} {}\n", timestamp, msg);
        let _ = std::fs::OpenOptions::new().create(true).append(true).open(&data_dir).and_then(|mut f| f.write_all(entry.as_bytes()));
    }

    // 发事件到前端
    if let Some(app) = app_handle {
        let _ = app.emit_all("backend-log", msg.to_string());
    }
}

// 清理 PyInstaller 临时文件
fn cleanup_pyinstaller_temp() {
    #[cfg(target_os = "windows")]
    {
        // 清理 PyInstaller --onefile 创建的 _MEI* 临时目录
        std::thread::sleep(std::time::Duration::from_millis(500));
        if let Ok(temp_dir) = std::env::var("TEMP") {
            #[cfg(debug_assertions)]
            println!("🔍 检查临时目录: {}", temp_dir);

            if let Ok(entries) = std::fs::read_dir(&temp_dir) {
                let mut cleaned = 0;
                for entry in entries.flatten() {
                    if let Ok(metadata) = entry.metadata() {
                        if metadata.is_dir() {
                            if let Some(file_name) = entry.file_name().to_str() {
                                if file_name.starts_with("_MEI") {
                                    let path = entry.path();
                                    #[cfg(debug_assertions)]
                                    println!("🗑️ 尝试删除 PyInstaller 临时目录: {}", file_name);
                                    match std::fs::remove_dir_all(&path) {
                                        Ok(_) => {
                                            cleaned += 1;
                                            #[cfg(debug_assertions)]
                                            println!("✅ 已删除: {}", file_name);
                                        }
                                        Err(e) => {
                                            #[cfg(debug_assertions)]
                                            println!("⚠️ 无法删除 {} (可能仍在使用): {}", file_name, e);
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                #[cfg(debug_assertions)]
                if cleaned > 0 {
                    println!("✅ 共清理了 {} 个 PyInstaller 临时目录", cleaned);
                }
            }
        }
    }
}

// 清理函数：清理后端状态并终止后端进程
fn cleanup_backend(app_handle: &tauri::AppHandle) {
    append_log_message_and_emit(Some(app_handle.clone()), "🔴 应用关闭中,终止后端进程...");

    let state: tauri::State<AppState> = app_handle.state();
    let mut backend_child = state.backend_child.lock().unwrap();

    if let Some(child) = backend_child.take() {
        #[cfg(debug_assertions)]
        println!("🔴 正在杀死后端进程及其子进程...");

        // 在Windows上，使用taskkill /F /T来杀死整个进程树
        #[cfg(target_os = "windows")]
        {
            let pid = child.pid();
            #[cfg(debug_assertions)]
            println!("🔴 后端进程PID: {}", pid);

            // 使用taskkill强制终止进程树
            let output = std::process::Command::new("taskkill")
                .args(&["/F", "/T", "/PID", &pid.to_string()])
                .output();

            match output {
                Ok(result) => {
                    if result.status.success() {
                        #[cfg(debug_assertions)]
                        println!("✅ 后端进程树已成功终止 (taskkill)");
                    } else {
                        #[cfg(debug_assertions)]
                        eprintln!("⚠️ taskkill 返回非零状态");
                        // 备用方案：直接kill
                        let _ = child.kill();
                    }
                }
                Err(_e) => {
                    #[cfg(debug_assertions)]
                    eprintln!("❌ taskkill 执行失败, 尝试直接kill");
                    let _ = child.kill();
                }
            }
        }

        // 非Windows平台使用默认kill
        #[cfg(not(target_os = "windows"))]
        {
            match child.kill() {
                Ok(_) => {
                    #[cfg(debug_assertions)]
                    println!("✅ 后端进程已终止");
                }
                Err(_e) => {
                    #[cfg(debug_assertions)]
                    eprintln!("❌ 终止后端进程失败");
                }
            }
        }
    } else {
        #[cfg(debug_assertions)]
        println!("⚠️ 没有找到后端进程句柄");
    }

    // 清理 PyInstaller 临时文件
    #[cfg(debug_assertions)]
    println!("🗑️ 清理 PyInstaller 临时文件...");
    cleanup_pyinstaller_temp();
    #[cfg(debug_assertions)]
    println!("✅ 临时文件清理完成");
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            backend_port: Arc::new(Mutex::new(None)),
            backend_child: Arc::new(Mutex::new(None)),
        })
        .setup(|app| {
            // 仅在调试模式下打印启动信息
            #[cfg(debug_assertions)]
            println!("=== 应用启动中 ===");

            let app_handle = app.handle();
            let state: tauri::State<AppState> = app_handle.state();
            let backend_port = state.backend_port.clone();

            // 检查是否已经有后端进程在运行
            {
                let backend_child = state.backend_child.lock().unwrap();
                if backend_child.is_some() {
                    #[cfg(debug_assertions)]
                    println!("⚠️ 后端进程已经在运行，跳过启动");
                    return Ok(());
                }
            }

            // 启动后端 sidecar
            #[cfg(debug_assertions)]
            println!("启动后端服务...");
            #[cfg(debug_assertions)]
            println!("[调试] 准备启动 backend sidecar");

            // 使用 Tauri sidecar 启动后端
            match Command::new_sidecar("paddleocr_backend") {
                Ok(command) => {
                    #[cfg(debug_assertions)]
                    println!("[调试] Sidecar 命令创建成功");
                    match command.spawn() {
                        Ok((mut rx, child)) => {
                            // 保存后端进程句柄以便后续终止
                            let backend_child_arc = state.backend_child.clone();
                            *backend_child_arc.lock().unwrap() = Some(child);

                            // 将 app_handle 克隆给异步任务用于 emit
                            let app_handle_for_events = app_handle.clone();

                            append_log_message_and_emit(Some(app_handle.clone()), "✅ 后端进程已启动并保存句柄");

                            // 为异步任务克隆一份
                            let backend_port_async = backend_port.clone();

                            // 异步读取后端输出
                            tauri::async_runtime::spawn(async move {
                                let mut port_found = false;
                                append_log_message_and_emit(Some(app_handle_for_events.clone()), "[调试] 异步任务已启动,开始接收后端事件");

                                while let Some(event) = rx.recv().await {
                                    match event {
                                        CommandEvent::Stdout(line) => {
                                            // 写日志并推送到前端
                                            append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("[后端 stdout] {}", line));

                                            // 尝试从输出中解析端口号
                                            if !port_found {
                                                if let Some(port) = parse_port_from_line(&line) {
                                                    append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("✅ 从 stdout 检测到后端端口: {}", port));
                                                    *backend_port_async.lock().unwrap() = Some(port);
                                                    port_found = true;
                                                }
                                            }
                                        }
                                        CommandEvent::Stderr(line) => {
                                            append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("[后端 stderr] {}", line));

                                            // 也尝试从 stderr 解析端口(uvicorn 输出在这里)
                                            if !port_found {
                                                if let Some(port) = parse_port_from_line(&line) {
                                                    append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("✅ 从 stderr 检测到后端端口: {}", port));
                                                    *backend_port_async.lock().unwrap() = Some(port);
                                                    port_found = true;
                                                }
                                            }
                                        }
                                        CommandEvent::Error(err) => {
                                            append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("[后端进程错误] {}", err));
                                        }
                                        CommandEvent::Terminated(payload) => {
                                            append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("[后端] 进程终止，退出码: {:?}", payload.code));
                                        }
                                        _ => {}
                                    }
                                }

                                // 如果后端进程退出后仍未获取到端口,尝试从文件读取
                                if backend_port_async.lock().unwrap().is_none() {
                                    append_log_message_and_emit(Some(app_handle_for_events.clone()), "后端退出,尝试从文件读取端口信息...");
                                    if let Some(data_dir) = dirs::data_local_dir() {
                                        let port_file = data_dir.join("PaddleOCRDesktop").join("server_info.json");
                                        if port_file.exists() {
                                            if let Ok(content) = std::fs::read_to_string(&port_file) {
                                                if let Ok(info) = serde_json::from_str::<serde_json::Value>(&content) {
                                                    if let Some(port) = info["backend_port"].as_u64() {
                                                        append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("✅ 从文件读取到端口: {}", port));
                                                        *backend_port_async.lock().unwrap() = Some(port as u16);
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            });

                            // 立即返回,不阻塞窗口 - 前端会通过轮询检查端口
                            #[cfg(debug_assertions)]
                            println!("✅ 后端启动任务已提交到后台,主线程立即返回以保持窗口响应");
                        }
                        Err(e) => {
                            #[cfg(debug_assertions)]
                            eprintln!("❌ 启动后端进程失败: {}", e);
                        }
                    }
                }
                Err(e) => {
                    #[cfg(debug_assertions)]
                    eprintln!("❌ 创建后端命令失败: {}", e);
                }
            }

            #[cfg(debug_assertions)]
            println!("=== 应用初始化完成 ===");
            Ok(())
        })
        .on_window_event(|event| {
            // 监听窗口关闭事件
            match event.event() {
                tauri::WindowEvent::CloseRequested { api, .. } => {
                    let window = event.window().clone();
                    #[cfg(debug_assertions)]
                    println!("🔴 窗口关闭请求,发送事件到前端并开始清理...");

                    // 阻止默认关闭行为
                    api.prevent_close();

                    // 发送关闭请求事件到前端
                    let _ = window.emit("tauri://close-requested", ());

                    // 在新线程中执行清理,避免阻塞事件循环
                    let window_for_thread = window.clone();
                    std::thread::spawn(move || {
                        #[cfg(debug_assertions)]
                        println!("🔴 开始清理后端进程...");

                        // 在闭包内部获取 app_handle，避免生命周期问题
                        let app_handle = window_for_thread.app_handle();
                        cleanup_backend(&app_handle);

                        #[cfg(debug_assertions)]
                        println!("✅ 清理完成,关闭窗口");

                        // 清理完成后关闭窗口
                        let _ = window_for_thread.close();
                    });
                }
                _ => {}
            }
        })
        .invoke_handler(tauri::generate_handler![get_backend_url, start_backend, read_backend_logs])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

#[tauri::command]
fn start_backend(app_handle: tauri::AppHandle, state: tauri::State<AppState>) -> Result<String, String> {
    // 如果已经有后端进程则直接返回
    {
        let backend_child = state.backend_child.lock().unwrap();
        if backend_child.is_some() {
            return Ok("already_running".into());
        }
    }

    // 复制需要移动到异步任务中的 state
    let backend_port_arc = state.backend_port.clone();
    let backend_child_arc = state.backend_child.clone();

    match Command::new_sidecar("paddleocr_backend") {
        Ok(command) => match command.spawn() {
            Ok((mut rx, child)) => {
                // 保存句柄
                *backend_child_arc.lock().unwrap() = Some(child);

                append_log_message_and_emit(Some(app_handle.clone()), "start_backend: sidecar started");

                // 异步监听输出，尝试解析端口
                let app_handle_for_events = app_handle.clone();
                tauri::async_runtime::spawn(async move {
                    let mut port_found = false;
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) => {
                                append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("[后端] {}", line));
                                if !port_found {
                                    if let Some(port) = parse_port_from_line(&line) {
                                        *backend_port_arc.lock().unwrap() = Some(port);
                                        port_found = true;
                                    }
                                }
                            }
                            CommandEvent::Stderr(line) => {
                                append_log_message_and_emit(Some(app_handle_for_events.clone()), &format!("[后端错误] {}", line));
                                if !port_found {
                                    if let Some(port) = parse_port_from_line(&line) {
                                        *backend_port_arc.lock().unwrap() = Some(port);
                                        port_found = true;
                                    }
                                }
                            }
                            _ => {}
                        }
                    }
                });

                Ok("started".into())
            }
            Err(e) => {
                append_log_message_and_emit(Some(app_handle.clone()), &format!("spawn failed: {}", e));
                Err(format!("spawn failed: {}", e))
            }
        },
        Err(e) => {
            append_log_message_and_emit(Some(app_handle.clone()), &format!("create failed: {}", e));
            Err(format!("create failed: {}", e))
        },
    }
}

#[tauri::command]
fn get_backend_url(state: tauri::State<AppState>) -> String {
    append_log_message_and_emit(None, "[调试] get_backend_url 被调用");
    let port = state.backend_port.lock().unwrap();
    append_log_message_and_emit(None, &format!("[调试] 当前后端端口状态: {:?}", *port));
    match *port {
        Some(p) => {
            append_log_message_and_emit(None, &format!("✅ 返回后端地址: http://127.0.0.1:{}", p));
            format!("http://127.0.0.1:{}", p)
        },
        None => {
            append_log_message_and_emit(None, "⚠️  后端端口未设置，使用默认地址 http://localhost:8002");
            "http://localhost:8002".to_string()
        }
    }
}

// 读取磁盘日志内容, 返回字符串
#[tauri::command]
fn read_backend_logs() -> Result<String, String> {
    if let Some(mut data_dir) = dirs::data_local_dir() {
        data_dir.push("PaddleOCRDesktop");
        data_dir.push("logs");
        data_dir.push("app.log");
        match std::fs::read_to_string(&data_dir) {
            Ok(s) => Ok(s),
            Err(e) => Err(format!("read failed: {}", e)),
        }
    } else {
        Err("no data dir".into())
    }
}


