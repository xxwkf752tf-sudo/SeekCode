"""SeekCode 后端启动入口。"""

import logging
import os
import socket
import threading

import uvicorn


def find_free_port(host: str = "127.0.0.1") -> int:
    """在指定主机上寻找可用端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def run_server(port: int) -> None:
    """在子线程中启动 uvicorn 服务器。"""
    uvicorn.run(
        "seekcode.server:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
    )


def main() -> None:
    """主入口：启动后端服务器并保持主线程存活。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    raw_port = os.environ.get("SEEKCODE_PORT")
    if raw_port and raw_port.isdigit():
        port = int(raw_port)
    else:
        port = find_free_port()

    logging.info(f"SeekCode backend started at http://127.0.0.1:{port}")
    # 这一行会被启动器识别，请不要修改格式
    print(f"SEEKCODE_READY http://127.0.0.1:{port}/", flush=True)

    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # 保持主线程运行
    stop_event = threading.Event()
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        logging.info("SeekCode backend stopped.")
