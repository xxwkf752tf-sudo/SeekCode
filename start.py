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
import threading
import time
import webbrowser


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
PYTHON = sys.executable
START_PORT = 55000
MAX_PORT = 55010


def is_port_open(host: str, port: int) -> bool:
    """检查指定端口是否已有服务在监听。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def can_bind_port(host: str, port: int) -> bool:
    """检查当前进程是否可以绑定到该端口（排除已被占用或被系统保留的端口）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True
    except OSError:
        return False


def wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    """等待服务端口就绪。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False


def check_dependencies():
    """检查并尝试安装依赖。"""
    required = ["fastapi", "uvicorn", "httpx"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"检测到缺少依赖：{', '.join(missing)}")
        print("正在尝试自动安装，请稍候...")
        req_file = os.path.join(BACKEND_DIR, "requirements.txt")
        try:
            result = subprocess.run(
                [PYTHON, "-m", "pip", "install", "-r", req_file],
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print("自动安装依赖失败，错误信息：")
                print(result.stderr or result.stdout)
                print("\n请手动运行：")
                print(f"  {PYTHON} -m pip install -r {req_file}")
                input("\n按 Enter 键退出...")
                sys.exit(1)
        except Exception as e:
            print(f"安装依赖时出错：{e}")
            print(f"\n请手动运行：{PYTHON} -m pip install -r {req_file}")
            input("\n按 Enter 键退出...")
            sys.exit(1)


def drain_output(stream):
    """在后台持续读取子进程输出，防止管道缓冲区满导致服务卡住。"""
    try:
        for line in stream:
            sys.stdout.write(line)
            sys.stdout.flush()
    except Exception:
        pass


def main():
    print("=" * 40)
    print("  SeekCode 启动器")
    print("=" * 40)
    print("正在检查依赖...")

    check_dependencies()

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
            print(f"端口 {port} 已被占用，尝试下一个...")
            continue
        if not can_bind_port("127.0.0.1", port):
            print(f"端口 {port} 被系统保留或无法绑定，尝试下一个...")
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
            input("\n按 Enter 键退出...")
            sys.exit(1)

        # 读取 stdout 直到出现 SEEKCODE_READY
        ready = False
        try:
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                if "SEEKCODE_READY" in line and url in line:
                    ready = True
                    break
                if proc.poll() is not None:
                    break
        except Exception as e:
            print(f"读取服务日志时出错：{e}")

        if ready:
            # 启动后台线程持续读取输出，防止子进程因管道阻塞而卡死
            threading.Thread(target=drain_output, args=(proc.stdout,), daemon=True).start()
            break

        if wait_for_port("127.0.0.1", chosen_port, timeout=3.0):
            threading.Thread(target=drain_output, args=(proc.stdout,), daemon=True).start()
            break

        # 该端口启动失败，尝试下一个
        print(f"端口 {port} 启动未就绪，尝试下一个...")
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        chosen_port = None
        url = None

    if not chosen_port or not url:
        print("\n无法启动服务，请检查上面的日志。")
        if proc and proc.poll() is None:
            proc.terminate()
        input("\n按 Enter 键退出...")
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
