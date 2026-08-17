"""SeekCode 启动器

双击运行后：
1. 在终端显示中文启动提示。
2. 自动启动后端服务。
3. 检测到服务就绪后自动打开系统默认浏览器。
4. 保持运行，关闭本窗口即停止服务。
"""

import os
import re
import signal
import socket
import subprocess
import sys
import time
import webbrowser


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
PYTHON = sys.executable
START_PORT = 54082
MAX_PORT = 54090


def is_port_open(host: str, port: int) -> bool:
    """检查指定端口是否已被占用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    """等待服务端口就绪。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False


def main():
    print("=" * 40)
    print("  SeekCode 启动器")
    print("=" * 40)
    print("正在启动本地服务，请稍候...")
    print("提示：首次使用会弹出 API Key 输入框。")
    print("      关闭本窗口将同时停止 SeekCode 服务。")
    print("-" * 40)

    env = os.environ.copy()
    env["PYTHONPATH"] = BACKEND_DIR

    proc = None
    chosen_port = None
    url = None

    for port in range(START_PORT, MAX_PORT + 1):
        if is_port_open("127.0.0.1", port):
            continue
        chosen_port = port
        env["SEEKCODE_PORT"] = str(chosen_port)
        url = f"http://127.0.0.1:{chosen_port}/"

        try:
            proc = subprocess.Popen(
                [PYTHON, "-m", "seekcode"],
                cwd=BACKEND_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        except Exception as e:
            print(f"启动服务时出错：{e}")
            sys.exit(1)

        # 读取 stdout 直到出现 SEEKCODE_READY，同时把日志打印到终端
        ready = False
        try:
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                if "SEEKCODE_READY" in line and url in line:
                    ready = True
                    break
        except Exception as e:
            print(f"读取服务日志时出错：{e}")

        if ready or wait_for_port("127.0.0.1", chosen_port, timeout=3.0):
            break

        # 该端口启动失败，尝试下一个
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=2)
        chosen_port = None
        url = None

    if not chosen_port or not url:
        print("\n无法启动服务，请检查上面的日志。")
        if proc and proc.poll() is None:
            proc.terminate()
        sys.exit(1)

    print(f"\n服务已就绪：{url}")
    print("正在打开浏览器...")
    webbrowser.open(url)
    print("你现在可以最小化本窗口，但请不要关闭它。")
    print("按 Ctrl+C 可以停止服务。\n")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n正在停止 SeekCode 服务...")
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    finally:
        if proc.poll() is None:
            proc.kill()
        print("服务已停止。")


if __name__ == "__main__":
    main()
