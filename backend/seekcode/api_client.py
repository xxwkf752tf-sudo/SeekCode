"""SeekCode AI API 客户端模块。"""

import json

import httpx

from .errors import ERROR_MESSAGES, SeekCodeError


def classify_error(exc: Exception, response_status: int = None) -> str:
    """根据异常类型与 HTTP 状态码返回内部错误码。"""
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.NetworkError):
        return "network_error"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401 or status == 403:
            return "invalid_api_key"
        if status == 429:
            return "rate_limit"
        if status == 402 or status == 529:
            return "insufficient_quota"
        return "network_error"
    if response_status:
        if response_status == 401 or response_status == 403:
            return "invalid_api_key"
        if response_status == 429:
            return "rate_limit"
        if response_status == 402 or response_status == 529:
            return "insufficient_quota"
    return "network_error"


def _make_client(api_base: str, timeout: float) -> httpx.AsyncClient:
    """创建配置好的 httpx 异步客户端。"""
    return httpx.AsyncClient(
        base_url=api_base.rstrip("/"),
        timeout=timeout,
        headers={"Content-Type": "application/json"},
    )


async def stream_completion(
    messages: list,
    model: str,
    api_key: str,
    api_base: str,
    timeout: float = 60,
    stop_event=None,
):
    """向 /chat/completions 发送流式请求，逐字 yield 文本片段。

    参数：
        messages: OpenAI 格式消息列表。
        model: 模型名称。
        api_key: API Key。
        api_base: API 基础地址。
        timeout: 超时秒数。
        stop_event: asyncio.Event，设置后提前终止流式读取。

    生成：
        字符串片段（choices[0].delta.content）。
    """
    if not api_key:
        info = ERROR_MESSAGES["invalid_api_key"]
        raise SeekCodeError("invalid_api_key", info["title"], info["message"])

    client = _make_client(api_base, timeout)
    try:
        async with client:
            async with client.stream(
                "POST",
                "/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                if response.status_code != 200:
                    try:
                        body = await response.aread()
                    except Exception:
                        body = b""
                    code = classify_error(None, response.status_code)
                    info = ERROR_MESSAGES.get(code, {"title": "请求失败", "message": f"状态码 {response.status_code}"})
                    raise SeekCodeError(code, info["title"], f"{info['message']} ({response.status_code})")

                async for line in response.aiter_lines():
                    if stop_event is not None and stop_event.is_set():
                        break
                    if not line.strip():
                        continue
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: "):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
    except SeekCodeError:
        raise
    except Exception as exc:
        code = classify_error(exc)
        info = ERROR_MESSAGES.get(code, {"title": "网络错误", "message": str(exc)})
        raise SeekCodeError(code, info["title"], info["message"], detail=str(exc))


async def judge_complexity(
    user_text: str,
    history_summary: str,
    config,
) -> str:
    """调用轻量模型判定任务复杂度。

    返回 "simple" | "medium" | "complex" 之一。
    """
    if not config.api_key:
        info = ERROR_MESSAGES["invalid_api_key"]
        raise SeekCodeError("invalid_api_key", info["title"], info["message"])

    prompt = f"""请判断下面用户任务的复杂度，只能返回以下三者之一：simple、medium、complex。

历史摘要：{history_summary or "无"}
用户任务：{user_text}

复杂度定义：
- simple：单次查询、简单解释、无需多步骤操作。
- medium：需要多步命令或简单文件操作。
- complex：涉及大量推理、多文件编辑、复杂工程任务。

请只输出一个单词（simple/medium/complex），不要解释。"""

    client = _make_client(config.api_base, config.timeout_seconds)
    try:
        async with client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {config.api_key}"},
                json={
                    "model": config.model_flash,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip().lower()
            if "complex" in content:
                return "complex"
            if "medium" in content:
                return "medium"
            return "simple"
    except SeekCodeError:
        raise
    except Exception as exc:
        code = classify_error(exc)
        info = ERROR_MESSAGES.get(code, {"title": "网络错误", "message": str(exc)})
        raise SeekCodeError(code, info["title"], info["message"], detail=str(exc))
