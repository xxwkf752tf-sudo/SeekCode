"""SeekCode 终端命令执行模块。"""

import asyncio
import os
import time
from pathlib import Path

# 可能进入交互式 REPL 的命令前缀黑名单
INTERACTIVE_PATTERNS = [
    "python",
    "python3",
    "py",
    "cmd",
    "powershell",
    "pwsh",
    "bash",
    "sh",
    "node",
    "irb",
    "psql",
    "mysql",
]


def _is_interactive(command: str) -> bool:
    """判断命令是否为可能进入 REPL 的交互式命令。"""
    stripped = command.strip()
    first = stripped.split()[0] if stripped else ""
    first_lower = first.lower()

    # 允许 python -c、powershell -Command 等非交互式用法
    if first_lower in ("python", "python3", "py") and "-c" in stripped:
        return False
    if first_lower in ("powershell", "pwsh") and "-Command" in stripped:
        return False

    return first_lower in [p.lower() for p in INTERACTIVE_PATTERNS]


async def execute_command(
    command: str,
    cwd: Path = None,
    timeout: float = 60,
    stop_event: asyncio.Event = None,
) -> dict:
    """异步执行单条 Windows 终端命令。

    参数：
        command: 要执行的命令字符串。
        cwd: 工作目录，默认当前进程目录。
        timeout: 超时秒数。
        stop_event: 当设置时主动终止子进程。

    返回：
        {"stdout": str, "stderr": str, "exit_code": int, "duration_ms": int}
    """
    if _is_interactive(command):
        return {
            "stdout": "",
            "stderr": "检测到交互式命令，已被拒绝执行。",
            "exit_code": -1,
            "duration_ms": 0,
        }

    work_dir = str(cwd) if cwd else os.getcwd()
    shell_cmd = f'cmd.exe /c {command}'

    start = time.time()
    try:
        proc = await asyncio.create_subprocess_shell(
            shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
        )
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": f"创建子进程失败：{exc}",
            "exit_code": -1,
            "duration_ms": int((time.time() - start) * 1000),
        }

    communicate_task = asyncio.create_task(proc.communicate())
    wait_tasks: list[asyncio.Task] = [communicate_task]

    if stop_event is not None:
        wait_tasks.append(asyncio.create_task(stop_event.wait()))

    try:
        done, pending = await asyncio.wait(
            wait_tasks,
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        for task in wait_tasks:
            if not task.done():
                task.cancel()
        return {
            "stdout": "",
            "stderr": f"命令执行超时（超过 {timeout} 秒）。",
            "exit_code": -1,
            "duration_ms": int((time.time() - start) * 1000),
        }

    # 用户主动停止
    if stop_event is not None and stop_event.is_set():
        await _kill_process_tree(proc)
        for task in wait_tasks:
            if not task.done():
                task.cancel()
        return {
            "stdout": "",
            "stderr": "任务已被用户停止。",
            "exit_code": -1,
            "duration_ms": int((time.time() - start) * 1000),
        }

    # 正常完成：从 communicate_task 获取结果
    if communicate_task in done:
        stdout_bytes, stderr_bytes = await communicate_task
    else:
        # 理论上不会发生，若发生则安全清理
        await _kill_process_tree(proc)
        for task in wait_tasks:
            if not task.done():
                task.cancel()
        return {
            "stdout": "",
            "stderr": "命令执行异常中断。",
            "exit_code": -1,
            "duration_ms": int((time.time() - start) * 1000),
        }

    # 取消仍在等待的 stop_event 任务
    for task in wait_tasks:
        if not task.done():
            task.cancel()

    duration_ms = int((time.time() - start) * 1000)
    return {
        "stdout": stdout_bytes.decode("utf-8", errors="replace"),
        "stderr": stderr_bytes.decode("utf-8", errors="replace"),
        "exit_code": proc.returncode,
        "duration_ms": duration_ms,
    }


async def _kill_process_tree(proc) -> None:
    """终止子进程及其子进程树。"""
    try:
        if proc.pid:
            await asyncio.create_subprocess_shell(
                f'taskkill /PID {proc.pid} /T /F',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass
    try:
        await proc.wait()
    except Exception:
        pass
