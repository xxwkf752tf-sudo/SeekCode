"""SeekCode 路径工具模块。"""

import os
import sys
from pathlib import Path


def app_dir() -> Path:
    """返回 SeekCode 应用数据目录，默认使用 %APPDATA%/seekcode。"""
    appdata = os.environ.get("APPDATA")
    if appdata:
        path = Path(appdata) / "seekcode"
    else:
        path = Path.home() / "seekcode"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(relative: str) -> Path:
    """返回运行时资源路径，兼容 PyInstaller 打包与普通开发环境。

    打包后使用 sys._MEIPASS 作为基目录；开发时以本文件上三级目录为项目根目录。
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / relative
