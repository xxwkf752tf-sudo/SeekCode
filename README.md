# SeekCode

一个让 AI 通过自然语言帮你操作电脑的 Windows 桌面助手。

SeekCode 把 DeepSeek 大模型和本地命令行连接起来：你描述想做的事，AI 会自己决定该说什么、该执行什么命令，并在一个简洁的网页界面里完成交互。

---

## 它能做什么

- **自然语言驱动任务**

  用大白话描述需求，比如“帮我把桌面所有 PNG 图片压缩到 80% 质量并放到 D:\\backup”，AI 会拆解步骤并调用终端命令执行。

- **双模型自动切换**

  支持 DeepSeek V4 Pro 与 V4 Flash。打开自动模式后，系统会先判断任务复杂度，再选择更快的 Flash 或更强的 Pro。

- **三级权限控制**

  | 模式 | 说明 |
  |---|---|
  | 对话模式 | 只能聊天，不会执行任何命令 |
  | 标准模式 | 可执行命令，但删除、批量文件等高危操作需要二次确认 |
  | 完全访问模式 | 允许 AI 自动执行命令，但删除类操作会先压缩备份，且单次最多处理 1000 个文件 |

- **本地优先，密钥不落地到仓库**

  API Key 只保存在 `%APPDATA%\\seekcode\\config.json`，输入框采用密码圆点 + 显示/隐藏切换，可随时删除。

- **对话管理**

  左侧可折叠面板支持新建、加载、导出历史会话。

---

## 快速开始

1. 克隆仓库到本地。
2. 双击 `start.py`。
3. 首次启动会弹出 API Key 输入框，填入你的 DeepSeek API Key。
4. 在浏览器里输入任务，开始对话。

关闭运行 `start.py` 的黑色终端窗口，即可停止服务。

---

## 环境要求

- Windows 10 / 11
- Python 3.10 或更高版本
- 依赖会在首次启动时自动安装（`fastapi`、`uvicorn`、`httpx`）

如果自动安装失败，可以手动运行：

```powershell
python -m pip install -r backend/requirements.txt
```

---

## 项目结构

```
SeekCode/
├── start.py              # 双击启动器
├── backend/              # Python 后端
│   ├── seekcode/
│   │   ├── main.py       # 服务入口
│   │   ├── server.py     # FastAPI 路由
│   │   ├── agent.py      # AI 执行循环
│   │   ├── executor.py   # 命令执行器
│   │   ├── security.py   # 权限与危险命令识别
│   │   └── config.py     # 配置与系统提示词
│   └── requirements.txt
├── ui/                   # 前端页面
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── docs/                 # 阶段文档与自查清单
```

---

## 安全提示

- 完全访问模式虽然方便，但请只在可信环境和明确需求下开启。
- 删除类命令会先进入 `%APPDATA%\\seekcode\\backups` 的压缩备份，后续版本会开放回收站还原。
- 所有命令执行都有超时保护，你可以随时点击停止按钮中断任务。

---

## 开发状态

当前已完成第一阶段：可工作的前后端原型，支持对话、命令执行、权限切换、配置持久化与一键启动。

第二阶段重点：更稳定的 Agent 循环、长任务恢复、插件化工具扩展。

---

## License

MIT
