# SeekCode 后端

阶段二后端核心代码，基于 FastAPI + uvicorn + httpx 构建。

## 本地运行

1. 安装依赖：

```powershell
pip install -r requirements.txt
```

2. 启动服务：

```powershell
python -m seekcode
```

3. 在浏览器中打开终端输出的地址，例如：

```
http://127.0.0.1:xxxxx/
```

## 说明

- 配置、会话、记忆、备份数据默认写入 `%APPDATA%/seekcode`。
- 前端静态文件由后端通过 `StaticFiles` 直接托管 `ui/` 目录。
- 打包后可通过 PyInstaller 与 pywebview 组合为 Windows 桌面应用（main.py 中已保留相关注释）。
