"""SeekCode 配置管理模块。"""

import base64
import ctypes
import json
import os
import sys
from pathlib import Path
from tempfile import mkstemp

from pydantic import BaseModel

from .paths import app_dir

_ENCRYPT_PREFIX = "dpapi:"


class _DataBlob(ctypes.Structure):
    """Windows DATA_BLOB 结构，用于 DPAPI 加解密。"""

    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _dpapi_encrypt(plaintext: str) -> str:
    """使用 Windows DPAPI 加密文本；非 Windows 环境使用兼容性标记。"""
    if not plaintext:
        return ""
    encoded = plaintext.encode("utf-8")
    if sys.platform != "win32":
        # 非 Windows 环境仅做 base64 标记，避免开发测试时完全无法运行
        return f"{_ENCRYPT_PREFIX}plaintext:{base64.b64encode(encoded).decode('ascii')}"

    blob_in = _DataBlob()
    blob_out = _DataBlob()
    buffer_in = ctypes.create_string_buffer(encoded)
    blob_in.cbData = len(encoded)
    blob_in.pbData = ctypes.cast(buffer_in, ctypes.POINTER(ctypes.c_char))
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return f"{_ENCRYPT_PREFIX}{base64.b64encode(encrypted).decode('ascii')}"


def _dpapi_decrypt(value: str) -> str:
    """使用 Windows DPAPI 解密文本；兼容旧版本明文。"""
    if not value:
        return ""
    if not value.startswith(_ENCRYPT_PREFIX):
        # 旧版本明文，自动迁移到加密存储
        return value

    payload = value[len(_ENCRYPT_PREFIX) :]
    if payload.startswith("plaintext:"):
        # 非 Windows 兼容性标记
        return base64.b64decode(payload[len("plaintext:") :]).decode("utf-8")

    encrypted = base64.b64decode(payload)
    if sys.platform != "win32":
        # Windows 加密的数据在非 Windows 环境无法解密
        return ""

    blob_in = _DataBlob()
    blob_out = _DataBlob()
    buffer_in = ctypes.create_string_buffer(encrypted)
    blob_in.cbData = len(encrypted)
    blob_in.pbData = ctypes.cast(buffer_in, ctypes.POINTER(ctypes.c_char))
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return decrypted.decode("utf-8")

DEFAULT_SYSTEM_PROMPT = """你是 SeekCode，一名基于 DeepSeek 模型的交互式终端助手，专门通过 Windows 命令行帮助用户完成软件工程任务。

## 核心身份
- 你是 Anthropic Claude Code 系统提示词的自由适配版本，已针对中文用户与 SeekCode 应用做本地化。
- 你的职责是理解用户意图，通过执行命令完成代码、文件、系统相关任务，同时保持安全与克制。

## 权限模式（由用户在界面中选择）
1. 对话模式：只能与用户聊天，不能执行任何命令或操作电脑。
2. 标准模式：可执行本地、可逆的命令；删除、批量文件操作、高危系统命令等需要用户二次确认。
3. 完全访问模式：可执行更多操作，但删除类命令仍会先压缩备份到临时目录，且单次最多处理 1000 个文件。

## 执行原则（参考 Claude Code）
- 评估可逆性与影响范围：本地、可逆的操作（如读取、编辑文件、运行测试）可自由执行；难以撤销、影响共享系统或具有破坏性的操作必须先请求确认。
- 先读再改：不要对你没有读过的文件提出修改建议；如需修改，先读取内容并理解上下文。
- 避免过度工程：只做用户明确要求或当前任务真正必需的改动，保持方案简单聚焦。
- 不添加不必要内容：不要顺手清理周边代码、不要给未修改的代码补注释或类型注解、不要为不可能发生的场景加冗余错误处理。
- 最小化文件创建：优先编辑已有文件，而非新建文件。
- 不给时间估计：专注“做什么”，不预测耗时。
- 安全编码：避免命令注入、XSS、SQL 注入等常见漏洞。
- 受阻时换方案：不要对同一失败命令反复重试，应思考替代方案或询问用户。
- 被拒绝后调整：如果用户取消或拒绝某个操作，不要立即重复执行，思考原因并调整策略。

## 输出格式
你必须严格按以下 JSON 输出，不要包含 JSON 以外的任何文字：

{
  "thought": "完整、逐步的思考过程（中文）。这部分只会在专门的思维链区域展示，不会作为最终回复。",
  "reply": "面向用户的最终回复主内容（中文）。简洁、自然，不要包含原始命令。",
  "command": "单条可执行的 Windows cmd 命令。如果当前不需要执行命令，请留空。",
  "dangerous": false,
  "done": false,
  "memory_updates": {}
}

## 输出规则
- thought 必须是完整的思考过程，不要省略中间步骤。
- reply 是用户真正看到的内容，应简洁、自然。
- command 必须是单行命令；避免交互式命令；路径含空格时请用引号包裹。
- 如果命令可能删除、修改系统或用户数据，或影响本地环境之外，将 dangerous 设为 true。
- 任务已完成、无需继续执行命令时，将 done 设为 true。
- memory_updates 用于更新本地记忆状态，没有则留空 {}。"""


class Config(BaseModel):
    """SeekCode 应用配置模型。"""

    api_key: str = ""
    api_base: str = "https://api.deepseek.com/v1"
    model_pro: str = "deepseek-v4-pro"
    model_flash: str = "deepseek-v4-flash"
    auto_mode: bool = True
    permission: str = "standard"  # chat / standard / full
    timeout_seconds: int = 60
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    max_delete_files: int = 1000
    working_dir: str = ""  # 空表示用户主目录


def config_path() -> Path:
    """返回配置文件路径。"""
    return app_dir() / "config.json"


def load_config() -> Config:
    """加载本地配置，若不存在则返回默认配置。"""
    path = config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_key = data.get("api_key", "")
            try:
                data["api_key"] = _dpapi_decrypt(raw_key)
            except Exception:
                # 解密失败（如配置文件被复制到其他用户）时清空 API Key，保留其余配置
                data["api_key"] = ""
            return Config(**data)
        except Exception:
            # 配置文件损坏时回退到默认配置
            return Config()
    return Config()


async def save_config(config: Config) -> None:
    """异步原子保存配置到本地文件。"""
    path = config_path()
    data = config.model_dump()
    data["api_key"] = _dpapi_encrypt(data["api_key"])
    fd, tmp = mkstemp(dir=path.parent, prefix="config_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
