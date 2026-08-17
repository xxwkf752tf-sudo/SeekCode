"""SeekCode 记忆文件管理模块。"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .paths import app_dir


def memory_dir() -> Path:
    """返回记忆文件目录。"""
    path = app_dir() / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def memory_path(session_id: str) -> Path:
    """返回指定会话的记忆文件路径。"""
    return memory_dir() / f"{session_id}.json"


def _default_memory(session_id: str) -> dict:
    """返回默认记忆结构。"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "session_id": session_id,
        "facts": {},
        "preferences": {},
    }


def load_memory(session_id: str) -> dict:
    """加载指定会话的记忆，不存在则返回默认结构。"""
    path = memory_path(session_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 确保关键字段存在
            data.setdefault("version", 1)
            data.setdefault("facts", {})
            data.setdefault("preferences", {})
            data.setdefault("session_id", session_id)
            return data
        except Exception:
            return _default_memory(session_id)
    return _default_memory(session_id)


def save_memory(session_id: str, data: dict) -> None:
    """保存记忆文件，并自动更新 updated_at 时间戳。"""
    path = memory_path(session_id)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["session_id"] = session_id
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def apply_updates(session_id: str, updates: dict) -> dict:
    """将 memory_updates 合并到记忆文件中并保存。"""
    data = load_memory(session_id)
    if not updates:
        return data
    facts = updates.get("facts", {})
    preferences = updates.get("preferences", {})
    if isinstance(facts, dict):
        data["facts"].update(facts)
    if isinstance(preferences, dict):
        data["preferences"].update(preferences)
    save_memory(session_id, data)
    return data
