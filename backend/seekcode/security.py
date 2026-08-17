"""SeekCode 命令安全校验与危险操作识别模块。"""

import re
from pathlib import Path

from .errors import SeekCodeError

# 危险命令正则列表（不区分大小写）
DANGEROUS_PATTERNS = [
    r"\brm\b",
    r"-Recurse",
    r"-Force",
    r"\bdel\b",
    r"\berase\b",
    r"rd\s+/s",
    r"rmdir\s+/s",
    r"format\b",
    r"diskpart",
    r"reg\s+delete",
    r"reg\s+add",
    r"Invoke-Expression",
    r"\biex\b",
    r"bitsadmin",
    r"certutil",
    r"net\s+user",
    r"takeown",
    r"icacls\s+/grant",
    r"icacls\s+/deny",
]

DANGEROUS_PATTERN = re.compile("|".join(DANGEROUS_PATTERNS), re.IGNORECASE)

# 删除命令识别正则
DELETE_PATTERNS = [
    # Windows cmd: rd /s /q <dir>
    re.compile(r"^\s*rd\s+(?:/s\s+|/q\s+|/s\s+/q\s+|/q\s+/s\s+)(.+)$", re.IGNORECASE),
    # Windows cmd: rmdir /s /q <dir>
    re.compile(r"^\s*rmdir\s+(?:/s\s+|/q\s+|/s\s+/q\s+|/q\s+/s\s+)(.+)$", re.IGNORECASE),
    # Windows cmd: del <file>
    re.compile(r"^\s*del\s+(.+)$", re.IGNORECASE),
    # PowerShell: Remove-Item -Recurse -Force <path>
    re.compile(r"^\s*Remove-Item\s+.*?-Recurse.*?(?:-Force)?\s+(.+)$", re.IGNORECASE),
    re.compile(r"^\s*Remove-Item\s+.*?-Force.*?(?:-Recurse)?\s+(.+)$", re.IGNORECASE),
    # PowerShell alias rm
    re.compile(r"^\s*rm\s+(?:-Recurse\s+|-Force\s+|-rf\s+|-r\s+)+(.+)$", re.IGNORECASE),
]


def is_dangerous(command: str):
    """判断命令是否包含危险关键字，返回 (bool, reason)。"""
    match = DANGEROUS_PATTERN.search(command)
    if match:
        return True, f"检测到危险关键字：{match.group(0)}"
    return False, ""


def validate_command(command: str, permission: str):
    """根据权限模式校验命令是否允许执行。

    chat 模式一律拒绝；standard/full 允许普通命令，危险标记由调用方进一步处理。
    返回 dangerous 布尔值。
    """
    dangerous, reason = is_dangerous(command)
    if permission == "chat":
        raise SeekCodeError(
            "permission_denied",
            "权限不足",
            "当前为对话模式，无法执行终端命令。",
        )
    return dangerous, reason


def is_delete_command(command: str) -> bool:
    """判断命令是否为删除/递归删除命令。"""
    for pattern in DELETE_PATTERNS:
        if pattern.search(command):
            return True
    return False


def collect_delete_targets(command: str, cwd: Path) -> list[Path]:
    """从删除命令中提取目标路径，用于 full 模式下的备份逻辑。

    仅解析显式指定的路径，不展开通配符，返回绝对路径列表。
    """
    targets = []
    for pattern in DELETE_PATTERNS:
        match = pattern.search(command)
        if not match:
            continue
        raw = match.group(1).strip()
        # 去除常见引号
        raw = raw.strip('"').strip("'")
        # 忽略明显是选项或空的内容
        if not raw or raw.startswith("-"):
            continue
        target = Path(raw)
        if not target.is_absolute():
            target = cwd / target
        targets.append(target.resolve())
    return targets
