"""
Tauri 模式启动脚本
用途：在 Tauri 打包环境中启动后端，支持：
1. 自动启动使用随机可用端口
2. 将端口号输出给 Tauri 读取
3. 设置 Tauri 模式的环境变量
"""
import uvicorn
import socket
import json
import os
import sys
import random
from pathlib import Path


def find_random_available_port(min_port=1024, max_port=65535):
    """随机查找可用的端口，避免固定端口范围"""
    # 随机打乱端口顺序
    ports = list(range(min_port, max_port + 1))
    random.shuffle(ports)

    for port in ports[:100]:  # 只尝试前100个随机端口
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError("No available ports found in random selection")


def save_port_info(port):
    """保存端口信息到文件，供前端读取（备用方案）"""
    port_file = Path(__file__).parent / 'port.json'
    with open(port_file, 'w') as f:
        json.dump({'port': port}, f)
    return port_file


def main():
    # 设置 Tauri 模式标记
    os.environ['TAURI_MODE'] = 'true'

    # 查找可用端口
    backend_port = find_random_available_port(1024, 65535)

    print(f"[INFO] Starting PaddleOCR backend on port {backend_port}")
    print(f"[PORT] Backend port allocated: {backend_port}", flush=True)
    sys.stderr.write(f"[PORT] Backend port allocated: {backend_port}\n")
    sys.stderr.flush()
    sys.stderr.flush()

    # 保存端口信息到文件（备用方案）
    try:
        port_file = save_port_info(backend_port)
        print(f"[INFO] Port info saved to: {port_file}")
    except Exception as e:
        print(f"[WARNING] Failed to save port info: {e}")

    # 启动服务器
    try:
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=backend_port,
            reload=False,  # 在生产环境中不使用重载
            log_level="info"
        )
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()