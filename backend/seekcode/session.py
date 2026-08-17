"""SeekCode 会话持久化模块。"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .memory import load_memory, save_memory
from .paths import app_dir


def sessions_dir() -> Path:
    """返回会话文件目录。"""
    path = app_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_path(session_id: str) -> Path:
    """返回指定会话文件路径。"""
    return sessions_dir() / f"{session_id}.json"


def _new_id() -> str:
    """生成新的会话 ID，格式为年月日时分秒加微秒前四位。"""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:-2]


def _default_session(session_id: str, title: str) -> dict:
    """返回默认会话结构，并同步创建记忆文件。"""
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "session_id": session_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    # 同时初始化记忆文件
    load_memory(session_id)
    return session


def create_session(title: str = "新对话") -> dict:
    """创建新会话并持久化。"""
    session_id = _new_id()
    session = _default_session(session_id, title)
    save_session(session)
    return session


def list_sessions() -> list:
    """列出所有会话摘要，按更新时间倒序。"""
    results = []
    for path in sessions_dir().glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "session_id": data.get("session_id", path.stem),
                "title": data.get("title", "未命名对话"),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
            })
        except Exception:
            continue
    results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return results


def load_session(session_id: str) -> dict:
    """加载指定会话，不存在则创建默认会话。"""
    path = session_path(session_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("session_id", session_id)
            data.setdefault("messages", [])
            return data
        except Exception:
            return _default_session(session_id, "新对话")
    return _default_session(session_id, "新对话")


def save_session(session: dict) -> None:
    """保存会话并更新时间戳。"""
    session["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = session_path(session["session_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)


def delete_session(session_id: str) -> bool:
    """删除指定会话及其记忆文件。"""
    path = session_path(session_id)
    removed = False
    if path.exists():
        path.unlink()
        removed = True
    mem_path = Path(str(path).replace("/sessions/", "/memory/"))
    mem_path = app_dir() / "memory" / f"{session_id}.json"
    if mem_path.exists():
        mem_path.unlink()
    return removed


def export_session(session_id: str, fmt: str = "markdown") -> str:
    """导出会话为 Markdown 或原始 JSON。"""
    session = load_session(session_id)
    if fmt.lower() == "json":
        return json.dumps(session, ensure_ascii=False, indent=2)

    lines = [f"# {session.get('title', '未命名对话')}", ""]
    lines.append(f"- 会话 ID: {session.get('session_id', '')}")
    lines.append(f"- 创建时间: {session.get('created_at', '')}")
    lines.append(f"- 导出时间: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    for msg in session.get("messages", []):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"## 用户\n\n{content}\n")
        elif role == "assistant":
            lines.append(f"## AI\n\n{content}\n")
        elif role == "system":
            lines.append(f"## 系统\n\n{content}\n")
        elif role == "terminal":
            meta = msg.get("meta", {})
            cmd = meta.get("command", "")
            stdout = meta.get("stdout", "")
            lines.append(f"## 终端命令 `{cmd}`\n\n```\n{stdout}\n```\n")
    return "\n".join(lines)
