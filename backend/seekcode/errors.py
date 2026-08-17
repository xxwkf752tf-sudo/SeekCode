"""SeekCode 全局错误定义与事件转换。"""

from typing import Any


class SeekCodeError(Exception):
    """SeekCode 业务异常基类。"""

    def __init__(self, code: str, title: str = "", message: str = "", detail: Any = None):
        self.code = code
        self.title = title
        self.message = message
        self.detail = detail
        super().__init__(f"[{code}] {title}: {message}")


ERROR_MESSAGES = {
    "insufficient_quota": {"title": "余额不足", "message": "API 账户余额不足，请充值后再试。"},
    "rate_limit": {"title": "请求过于频繁", "message": "触发了接口速率限制，请稍等片刻再试。"},
    "network_error": {"title": "网络请求失败", "message": "无法连接到 AI 服务，请检查网络。"},
    "timeout": {"title": "请求超时", "message": "AI 响应时间过长，请检查网络或稍后重试。"},
    "invalid_api_key": {"title": "API Key 无效", "message": "请检查设置中的 API Key 是否正确。"},
    "parse_error": {"title": "命令解析失败", "message": "AI 返回的格式不正确，已终止当前任务。"},
    "execution_error": {"title": "命令执行失败", "message": "终端命令执行出错，请查看详细输出。"},
    "permission_denied": {"title": "权限不足", "message": "当前模式下无法执行该操作，请切换到更高权限。"},
    "backup_limit_exceeded": {"title": "单次删除文件超过上限", "message": "本次删除操作涉及的文件数量过多，请分批处理或手动操作。"},
}


def error_to_event(code: str, detail: Any = None) -> dict:
    """将错误码转换为前端可识别的错误事件字典。"""
    info = ERROR_MESSAGES.get(code, {"title": "未知错误", "message": f"发生未知错误：{code}"})
    payload = {"code": code, "title": info["title"], "message": info["message"]}
    if detail is not None:
        payload["detail"] = detail
    return {"event": "error", "payload": payload}
