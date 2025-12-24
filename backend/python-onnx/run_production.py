import uvicorn
import socket
import json
import os
import sys
import random


def find_random_available_port(min_port=1024, max_port=65535):
    """随机查找可用的端口，避免固定端口范围"""
    # 随机打乱端口顺序
    ports = list(range(min_port, max_port + 1))
    random.shuffle(ports)

    for port in ports[:100]:  # 只尝试前100个随机端口
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports found in random selection")


def save_port_info(port):
    """保存端口信息到文件，供前端读取（备用方案）"""
    port_file = os.path.join(os.path.dirname(__file__), 'port.json')
    with open(port_file, 'w') as f:
        json.dump({'port': port}, f)
    return port_file


def main():
    # 生产环境：随机查找可用端口
    port = find_random_available_port(1024, 65535)

    # 输出端口信息到控制台，供Tauri捕获
    print(f"PORT:{port}", file=sys.stdout)
    sys.stdout.flush()  # 确保输出立即被刷新

    print(f"Starting server on port {port}", file=sys.stderr)

    # 保存端口信息到文件（备用方案）
    port_file = save_port_info(port)
    print(f"Port info saved to: {port_file}", file=sys.stderr)

    # 启动服务器
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()