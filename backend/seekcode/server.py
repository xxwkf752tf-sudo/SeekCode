"""SeekCode FastAPI 后端服务模块。"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("seekcode")

from .agent import (
    active_queues,
    active_tasks,
    register_queue,
    request_stop,
    run_task,
    submit_confirm,
    unregister_queue,
)
from .config import load_config, save_config
from .paths import app_dir, resource_path
from .session import create_session, export_session, list_sessions, load_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时创建应用数据目录。"""
    app_dir().mkdir(parents=True, exist_ok=True)
    (app_dir() / "memory").mkdir(exist_ok=True)
    (app_dir() / "sessions").mkdir(exist_ok=True)
    (app_dir() / "backups").mkdir(exist_ok=True)
    yield


app = FastAPI(title="SeekCode Backend", lifespan=lifespan)

# 开发环境 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# 静态文件禁止缓存，确保更新后的 JS/CSS 在常用浏览器里立即生效
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


@app.get("/api/config")
async def get_config():
    """获取当前配置，API Key 做掩码处理。"""
    config = load_config()
    data = config.model_dump()
    key = data.get("api_key", "")
    data["masked_key"] = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ""
    return data


@app.post("/api/config")
async def update_config(request: Request):
    """保存配置字段，仅更新传入的字段。"""
    body = await request.json()
    logger.info(f"收到配置更新请求: {list(body.keys())}")
    config = load_config()
    fields = config.model_dump().keys()
    updated = False
    for key, value in body.items():
        if key in fields:
            if key == "api_key":
                logger.info(f"API Key 更新: 更新前长度 {len(config.api_key)}, 更新后长度 {len(str(value))}")
            setattr(config, key, value)
            updated = True
    if updated:
        await save_config(config)
        logger.info("配置已写入本地文件")
    data = config.model_dump()
    key = data.get("api_key", "")
    data["masked_key"] = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ""
    return {"ok": True, "config": data}


@app.get("/api/sessions")
async def get_sessions():
    """返回会话列表。"""
    return {"sessions": list_sessions()}


@app.post("/api/sessions")
async def new_session():
    """创建新会话。"""
    session = create_session()
    return {"session": session}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """加载指定会话。"""
    session = load_session(session_id)
    return {"session": session}


@app.post("/api/sessions/{session_id}/export")
async def export_chat(session_id: str, request: Request):
    """导出会话为 Markdown 或 JSON。"""
    body = await request.json()
    fmt = body.get("format", "markdown")
    content = export_session(session_id, fmt)
    if fmt == "json":
        return PlainTextResponse(content, media_type="application/json")
    return PlainTextResponse(content, media_type="text/markdown")


@app.get("/api/stream")
async def stream_events(session_id: str = Query(..., description="会话 ID")):
    """SSE 事件流端点。"""
    queue = register_queue(session_id)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
                if event.get("event") in ("done", "error"):
                    break
        finally:
            unregister_queue(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/send")
async def send_message(request: Request):
    """接收用户消息并启动 Agent 任务。"""
    body = await request.json()
    session_id = body.get("session_id")
    text = body.get("text", "").strip()
    auto_mode = body.get("auto_mode", True)
    model = body.get("model", "flash")
    permission = body.get("permission", "standard")

    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 session_id")
    if not text:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    config = load_config()
    mode = "auto" if auto_mode else "manual"

    # 确保队列存在
    if session_id not in active_queues:
        register_queue(session_id)

    task = asyncio.create_task(
        run_task(session_id, text, mode, model, permission, config)
    )
    active_tasks[session_id] = task

    def cleanup(t):
        active_tasks.pop(session_id, None)

    task.add_done_callback(cleanup)
    return {"ok": True, "session_id": session_id}


@app.post("/api/confirm-danger")
async def confirm_danger(request: Request):
    """提交危险命令确认结果。"""
    body = await request.json()
    request_id = body.get("request_id")
    confirmed = body.get("confirmed", False)
    submit_confirm(request_id, confirmed)
    return {"ok": True}


@app.post("/api/stop")
async def stop_task(request: Request):
    """请求停止当前会话任务。"""
    body = await request.json()
    session_id = body.get("session_id")
    request_stop(session_id)
    return {"ok": True}


@app.post("/api/restore")
async def restore_backup(request: Request):
    """列出/还原备份（MVP 占位实现）。"""
    raw = await request.body()
    body = await request.json() if raw else {}
    action = body.get("action", "list")
    if action == "list":
        backups = []
        backup_root = app_dir() / "backups"
        if backup_root.exists():
            for p in backup_root.iterdir():
                backups.append({"name": p.name, "path": str(p)})
        return {"backups": backups, "todo": "还原功能在后续版本实现"}
    return {"ok": True, "todo": "还原功能在后续版本实现"}


# 首页与 index.html 显式返回，并强制禁用缓存
@app.get("/")
@app.get("/index.html")
async def serve_index():
    path = resource_path("ui/index.html")
    return FileResponse(
        str(path),
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# 挂载前端静态文件到根路径（API 路由定义完成后挂载，避免覆盖）
app.mount("/", NoCacheStaticFiles(directory=str(resource_path("ui"))), name="ui")
