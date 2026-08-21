"""SeekCode 官网本地服务器（静态托管 + AI 客服代理）。

职责：
  1. 托管 website/ 下的静态文件（首页、产品页、关于页、联系页、客服组件等）。
  2. 提供 POST /api/customer-service 作为 AI 客服后端，把访客消息转发到 Agnes，
     并以 cs_knowledge.md 作为 system prompt 注入产品知识。

安全约束：
  - Agnes API Key 仅由服务端读取：优先取环境变量 AGNES_API_KEY，
    其次读取同目录受保护的 .agnes_key 文件（该文件已被 .gitignore 忽略，
    且静态路由拒绝以 "." 开头的隐藏文件，不会被直接下载）。
  - 密钥绝不写入前端或任何静态文件。

运行：
  （方式一）设置环境变量后启动：
      set AGNES_API_KEY=sk-xxxx          (Windows)
      export AGNES_API_KEY=sk-xxxx       (Linux/macOS)
  （方式二）把密钥写入 website/.agnes_key 文件，直接启动即可：
      uvicorn serve:app --host 0.0.0.0 --port 8080
  或：python serve.py
"""

import json
import os
import pathlib

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

BASE_DIR = pathlib.Path(__file__).resolve().parent
KB_PATH = BASE_DIR / "cs_knowledge.md"

AGNES_BASE = os.environ.get("AGNES_API_BASE", "https://apihub.agnes-ai.com/v1").rstrip("/")
AGNES_MODEL = os.environ.get("AGNES_MODEL", "agnes-2.0-flash")

SYSTEM_PROMPT = None


def load_system_prompt() -> str:
    """读取知识库，构建客服 system prompt。"""
    kb = KB_PATH.read_text(encoding="utf-8")
    return (
        "你是 SeekCode 官方网站的 AI 客服助手。请严格基于下面的知识回答用户问题，"
        "使用简体中文，回答简洁、专业、友好。\n"
        "对于知识中没有、或你无法确认的内容，如实说明，并礼貌引导用户通过官方邮箱 "
        "wuhongzheng2026@outlook.com 或 GitHub 仓库联系团队，不要编造信息。\n"
        "你是一个咨询/售前支持助手，不能代替 SeekCode 桌面程序执行命令或操作用户电脑。\n\n"
        "【知识开始】\n" + kb + "\n【知识结束】"
    )


def get_api_key() -> str:
    """读取 Agnes Key：优先环境变量，其次受保护的 .agnes_key 文件。"""
    env_key = os.environ.get("AGNES_API_KEY", "").strip()
    if env_key:
        return env_key
    key_file = BASE_DIR / ".agnes_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


app = FastAPI(title="SeekCode Website")
SYSTEM_PROMPT = load_system_prompt()


@app.post("/api/customer-service")
async def customer_service(request: Request):
    body = await request.json()
    user_msg = (body.get("message") or "").strip()
    history = body.get("history") or []

    if not user_msg:
        return Response(
            json.dumps({"error": "empty"}, ensure_ascii=False),
            media_type="application/json",
            status_code=400,
        )

    api_key = get_api_key()
    if not api_key:
        # 未配置密钥：返回结构化提示，前端降级展示
        return Response(
            json.dumps(
                {
                    "error": "no_key",
                    "message": "客服 AI 暂未配置，请通过邮箱 wuhongzheng2026@outlook.com 联系我们。",
                },
                ensure_ascii=False,
            ),
            media_type="application/json",
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-8:]:
        role = h.get("role")
        content = h.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_msg})

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    AGNES_BASE + "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": AGNES_MODEL,
                        "messages": messages,
                        "stream": True,
                        "max_tokens": 900,
                    },
                ) as resp:
                    if resp.status_code != 200:
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "error": "upstream",
                                    "message": "客服服务暂时不可用，请稍后再试或通过邮箱联系我们。",
                                },
                                ensure_ascii=False,
                            )
                            + "\n\n"
                        )
                        return
                    async for line in resp.aiter_lines():
                        if not line.strip() or not line.startswith("data:"):
                            continue
                        data = line[len("data:") :].strip()
                        if data == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        token = choices[0].get("delta", {}).get("content")
                        if token:
                            yield "data: " + json.dumps({"token": token}, ensure_ascii=False) + "\n\n"
        except Exception:
            yield (
                "data: "
                + json.dumps(
                    {"error": "exception", "message": "连接客服服务出错，请稍后重试。"},
                    ensure_ascii=False,
                )
                + "\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------- 静态文件托管（拒绝隐藏/密钥文件） ----------------
@app.get("/")
async def serve_root():
    return FileResponse(str(BASE_DIR / "index.html"))


@app.get("/{path:path}")
async def serve_static(path: str):
    if path.startswith(".") or "/." in path:
        return Response("Not found", status_code=404)

    target = (BASE_DIR / path).resolve()
    # 防目录穿越
    if not str(target).startswith(str(BASE_DIR)):
        return Response("Not found", status_code=404)

    if target.is_dir():
        target = target / "index.html"
    if not target.exists():
        # 未知路径回退到首页（SPA 风格）
        target = BASE_DIR / "index.html"

    return FileResponse(str(target))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
