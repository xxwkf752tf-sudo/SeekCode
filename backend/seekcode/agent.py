"""SeekCode Agent 核心调度模块。"""

import asyncio
import json
import os
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .api_client import judge_complexity, stream_completion
from .config import Config
from .errors import SeekCodeError, error_to_event
from .executor import execute_command
from .memory import apply_updates, load_memory
from .paths import app_dir
from .security import collect_delete_targets, is_delete_command, validate_command
from .session import load_session, save_session

# 全局 Agent 状态
active_queues: dict[str, asyncio.Queue] = {}
pending_confirms: dict[str, asyncio.Future] = {}
stop_events: dict[str, asyncio.Event] = {}
active_tasks: dict[str, asyncio.Task] = {}


def register_queue(session_id: str) -> asyncio.Queue:
    """为会话注册 SSE 事件队列。"""
    queue = asyncio.Queue()
    active_queues[session_id] = queue
    return queue


def unregister_queue(session_id: str) -> None:
    """注销会话的事件队列。"""
    active_queues.pop(session_id, None)


def request_stop(session_id: str) -> None:
    """请求停止指定会话的正在运行的任务。"""
    event = stop_events.get(session_id)
    if event:
        event.set()


def submit_confirm(request_id: str, confirmed: bool) -> None:
    """提交危险命令的用户确认结果。"""
    future = pending_confirms.get(request_id)
    if future and not future.done():
        future.set_result(confirmed)


def _working_dir(config: Config) -> Path:
    """返回当前工作目录配置，空值则使用用户主目录。"""
    if config.working_dir:
        return Path(config.working_dir)
    return Path.home()


def _extract_json(text: str) -> dict:
    """从 AI 返回文本中提取 JSON 对象。"""
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_match:
        candidate = code_match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("未找到 JSON 对象")
        candidate = text[start : end + 1]
    return json.loads(candidate)


def _count_files(targets: list[Path]) -> int:
    """统计目标路径涉及的文件数量（目录递归计算）。"""
    total = 0
    for target in targets:
        if not target.exists():
            continue
        if target.is_file():
            total += 1
        elif target.is_dir():
            for _root, _dirs, files in os.walk(target):
                total += len(files)
    return total


def _backup_targets(targets: list[Path], session_id: str, max_files: int) -> dict:
    """将要删除的文件/目录压缩备份到临时区，并返回备份信息。

    如果目标数量超过 max_files，则抛出 backup_limit_exceeded 错误。
    """
    backup_root = app_dir() / "backups" / session_id
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    zip_path = backup_root / f"{timestamp}.zip"

    existing = [t for t in targets if t.exists()]
    file_count = _count_files(existing)
    if file_count > max_files:
        raise SeekCodeError(
            "backup_limit_exceeded",
            "单次删除文件超过上限",
            f"本次删除涉及 {file_count} 个文件，超过上限 {max_files}。",
        )

    manifest = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for target in existing:
            if target.is_file():
                arcname = target.name
                zf.write(target, arcname)
                manifest.append({"source": str(target), "arcname": arcname})
            elif target.is_dir():
                for root, _dirs, files in os.walk(target):
                    for file in files:
                        full = Path(root) / file
                        rel = full.relative_to(target.parent)
                        zf.write(full, str(rel))
                        manifest.append({"source": str(full), "arcname": str(rel)})

    manifest_path = backup_root / f"{timestamp}_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"created_at": timestamp, "files": manifest}, f, ensure_ascii=False, indent=2)

    return {"zip_path": str(zip_path), "file_count": file_count, "manifest_path": str(manifest_path)}


async def _put_event(session_id: str, event: str, payload: dict):
    """向会话队列发送事件。"""
    queue = active_queues.get(session_id)
    if queue:
        await queue.put({"event": event, "payload": payload})


def _build_messages(session: dict, config: Config, attached_file: Path = None) -> list:
    """构建发送给 LLM 的消息列表。"""
    messages = [{"role": "system", "content": config.system_prompt}]

    memory = load_memory(session.get("session_id", ""))
    if memory.get("facts") or memory.get("preferences"):
        memory_text = json.dumps(memory, ensure_ascii=False, indent=2)
        messages.append({"role": "system", "content": f"当前记忆文件内容：\n{memory_text}"})

    for msg in session.get("messages", []):
        role = msg.get("role")
        content = msg.get("content", "")
        if role in ("user", "assistant", "system"):
            messages.append({"role": role, "content": content})
    return messages


def _fallback_reply(full_text: str) -> dict:
    """当 AI 没有按 JSON 输出时，把它当作普通回复。"""
    text = full_text.strip()
    return {
        "thought": text,
        "reply": text,
        "command": "",
        "dangerous": False,
        "done": True,
        "memory_updates": {},
    }


async def run_task(
    session_id: str,
    user_text: str,
    mode: str,
    model: str,
    permission: str,
    config: Config,
    attached_file: Path = None,
):
    """Agent 任务主循环。

    参数：
        session_id: 会话 ID。
        user_text: 用户输入文本。
        mode: "auto" 或 "manual"。
        model: manual 模式下指定的模型（pro/flash）。
        permission: 权限模式（chat/standard/full）。
        config: 应用配置。
        attached_file: 可选附件路径。
    """
    stop_event = asyncio.Event()
    stop_events[session_id] = stop_event
    max_steps = 20

    try:
        session = load_session(session_id)
        session["messages"].append({
            "role": "user",
            "content": user_text,
            "meta": {"attached_file": str(attached_file)} if attached_file else {},
        })
        await _put_event(session_id, "status", {"text": "判定中"})

        # 对话模式：直接以聊天方式回复，不调用命令执行
        if permission == "chat":
            await _put_event(session_id, "assistant", {
                "text": "当前处于**对话模式**，我只能陪你聊天，无法执行任何命令或操作电脑。如需执行任务，请切换到**标准模式**或**完全访问模式**。"
            })
            await _put_event(session_id, "done", {"summary": ""})
            save_session(session)
            return

        # 自动模式：先判定复杂度
        if mode == "auto":
            recent = session["messages"][-6:]
            history_summary = "\n".join(
                f"{m.get('role')}: {m.get('content', '')[:100]}" for m in recent
            )
            try:
                level = await judge_complexity(user_text, history_summary, config)
            except SeekCodeError as exc:
                await _put_event(session_id, "error", {
                    "code": exc.code,
                    "title": exc.title,
                    "message": exc.message,
                })
                save_session(session)
                return
            chosen = config.model_pro if level == "complex" else config.model_flash
            await _put_event(session_id, "status", {"text": f"使用 {chosen} 执行"})
            await _put_event(session_id, "system", {"text": f"任务复杂度判定为 {level}，使用 {chosen}"})
        else:
            chosen = config.model_pro if model == "pro" else config.model_flash
            await _put_event(session_id, "status", {"text": f"使用 {chosen} 执行"})

        cwd = _working_dir(config)

        for step in range(max_steps):
            if stop_event.is_set():
                await _put_event(session_id, "system", {"text": "任务已停止。"})
                break

            await _put_event(session_id, "status", {"text": "执行中"})

            messages = _build_messages(session, config, attached_file)

            full_text = ""
            try:
                async for chunk in stream_completion(
                    messages,
                    chosen,
                    config.api_key,
                    config.api_base,
                    timeout=config.timeout_seconds,
                    stop_event=stop_event,
                ):
                    full_text += chunk
            except SeekCodeError as exc:
                await _put_event(session_id, "error", {
                    "code": exc.code,
                    "title": exc.title,
                    "message": exc.message,
                })
                save_session(session)
                return

            # 用户中途停止：把已收集的内容当作普通回复结束
            if stop_event.is_set():
                if full_text.strip():
                    await _put_event(session_id, "assistant", {"text": full_text.strip()})
                    session["messages"].append({"role": "assistant", "content": full_text.strip(), "meta": {"stopped": True}})
                await _put_event(session_id, "done", {"summary": ""})
                save_session(session)
                return

            # 解析 AI 返回。如果解析失败，当作普通聊天回复处理，不再报错
            try:
                result = _extract_json(full_text)
            except Exception:
                result = _fallback_reply(full_text)

            thought = result.get("thought", "")
            reply = result.get("reply", "")
            command = result.get("command", "")
            dangerous_flag = result.get("dangerous", False)
            done = result.get("done", False)
            memory_updates = result.get("memory_updates", {})

            # 发送完整思考链（思维链）
            if thought:
                await _put_event(session_id, "thought", {"text": thought})

            # 发送最终回复主内容
            display_reply = reply or thought
            if display_reply:
                await _put_event(session_id, "assistant", {"text": display_reply})

            # 保存完整原始 JSON，同时把 thought/reply 放入 meta 便于前端恢复
            session["messages"].append({
                "role": "assistant",
                "content": full_text,
                "meta": {
                    "thought": thought,
                    "reply": reply,
                    "command": command,
                    "dangerous": dangerous_flag,
                    "done": done,
                    "memory_updates": memory_updates,
                },
            })

            # 没有命令或任务已完成：直接结束
            if done or not command:
                if memory_updates:
                    apply_updates(session_id, memory_updates)
                save_session(session)
                await _put_event(session_id, "done", {"summary": reply or thought})
                return

            await _put_event(session_id, "command", {"command": command, "dangerous": dangerous_flag})

            # 权限与命令校验
            try:
                dangerous, reason = validate_command(command, permission)
            except SeekCodeError as exc:
                await _put_event(session_id, "error", {"code": exc.code, "title": exc.title, "message": exc.message})
                save_session(session)
                return

            # standard 模式危险命令确认
            if (dangerous or dangerous_flag) and permission == "standard":
                request_id = str(uuid.uuid4())
                future = asyncio.get_running_loop().create_future()
                pending_confirms[request_id] = future
                await _put_event(session_id, "danger_confirm", {
                    "request_id": request_id,
                    "command": command,
                    "reason": reason,
                })
                try:
                    confirmed = await asyncio.wait_for(future, timeout=300)
                except asyncio.TimeoutError:
                    confirmed = False
                finally:
                    pending_confirms.pop(request_id, None)
                if not confirmed:
                    await _put_event(session_id, "system", {"text": "用户取消了危险命令的执行。"})
                    save_session(session)
                    await _put_event(session_id, "done", {"summary": thought})
                    return

            # full 模式：对删除命令进行备份
            if permission == "full" and is_delete_command(command):
                targets = collect_delete_targets(command, cwd)
                if targets:
                    try:
                        backup_info = _backup_targets(targets, session_id, config.max_delete_files)
                        await _put_event(session_id, "system", {
                            "text": f"已启用安全备份：{backup_info['file_count']} 个文件已压缩到临时备份区。"
                        })
                    except SeekCodeError as exc:
                        await _put_event(session_id, "error", {"code": exc.code, "title": exc.title, "message": exc.message})
                        save_session(session)
                        return

            exec_result = await execute_command(
                command,
                cwd=cwd,
                timeout=config.timeout_seconds,
                stop_event=stop_event,
            )
            await _put_event(session_id, "terminal", {
                "command": command,
                "stdout": exec_result["stdout"],
                "stderr": exec_result["stderr"],
                "exit_code": exec_result["exit_code"],
                "duration_ms": exec_result["duration_ms"],
            })

            session["messages"].append({
                "role": "terminal",
                "content": f"命令：{command}\n{exec_result['stdout']}\n{exec_result['stderr']}",
                "meta": {
                    "command": command,
                    "stdout": exec_result["stdout"],
                    "stderr": exec_result["stderr"],
                    "exit_code": exec_result["exit_code"],
                },
            })

            if stop_event.is_set():
                await _put_event(session_id, "system", {"text": "任务已停止。"})
                break

            if memory_updates:
                apply_updates(session_id, memory_updates)
            save_session(session)

        # 达到最大步数仍未结束
        await _put_event(session_id, "done", {"summary": "已达到最大执行步数，任务已自动结束。"})

    except SeekCodeError as exc:
        await _put_event(session_id, "error", {"code": exc.code, "title": exc.title, "message": exc.message})
    except Exception as exc:
        await _put_event(session_id, "error", {
            "code": "execution_error",
            "title": "执行错误",
            "message": str(exc),
        })
    finally:
        stop_events.pop(session_id, None)
