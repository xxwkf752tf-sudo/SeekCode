/**
 * SeekCode 前端 UI 交互逻辑（阶段二后端对接版）
 * 通过 SSE 与 FastAPI 后端通信，实现对话、命令执行与危险命令确认。
 */

(function () {
  "use strict";

  // DOM 元素
  const elements = {
    sidebar: document.getElementById("sidebar"),
    sidebarOverlay: document.getElementById("sidebarOverlay"),
    sidebarToggleBtn: document.getElementById("sidebarToggleBtn"),
    newChatBtn: document.getElementById("newChatBtn"),
    chatListToday: document.getElementById("chatListToday"),
    chatListYesterday: document.getElementById("chatListYesterday"),
    loadChatBtn: document.getElementById("loadChatBtn"),
    exportChatBtn: document.getElementById("exportChatBtn"),

    messages: document.getElementById("messages"),
    chatArea: document.getElementById("chatArea"),
    composerInput: document.getElementById("composerInput"),
    sendBtn: document.getElementById("sendBtn"),
    stopBtn: document.getElementById("stopBtn"),
    clearChatBtn: document.getElementById("clearChatBtn"),

    autoModelToggle: document.getElementById("autoModelToggle"),
    modelSelect: document.getElementById("modelSelect"),
    modelSelectRow: document.getElementById("modelSelectRow"),
    modelActiveLabel: document.getElementById("modelActiveLabel"),

    statusPill: document.getElementById("statusPill"),
    statusText: document.getElementById("statusText"),
    inputStatus: document.getElementById("inputStatus"),

    permissionTrigger: document.getElementById("permissionTrigger"),
    permissionMenu: document.getElementById("permissionMenu"),
    permissionIcon: document.getElementById("permissionIcon"),
    permissionLabel: document.getElementById("permissionLabel"),
    permissionOptions: document.querySelectorAll(".permission-option"),

    themeBtn: document.getElementById("themeBtn"),
    settingsBtn: document.getElementById("settingsBtn"),
    settingsModal: document.getElementById("settingsModal"),
    settingsClose: document.getElementById("settingsClose"),
    promptEditor: document.getElementById("promptEditor"),
    apiKeyInput: document.getElementById("apiKeyInput"),
    apiKeyHint: document.getElementById("apiKeyHint"),
    apiKeyToggle: document.getElementById("apiKeyToggle"),
    apiKeyClearBtn: document.getElementById("apiKeyClearBtn"),
    savePromptBtn: document.getElementById("savePromptBtn"),
    resetPromptBtn: document.getElementById("resetPromptBtn"),

    apiKeyModal: document.getElementById("apiKeyModal"),
    firstApiKeyInput: document.getElementById("firstApiKeyInput"),
    firstApiKeyToggle: document.getElementById("firstApiKeyToggle"),
    apiKeySaveBtn: document.getElementById("apiKeySaveBtn"),
    apiKeyLaterBtn: document.getElementById("apiKeyLaterBtn"),

    dangerModal: document.getElementById("dangerModal"),
    dangerCommand: document.getElementById("dangerCommand"),
    dangerCancelBtn: document.getElementById("dangerCancelBtn"),
    dangerConfirmBtn: document.getElementById("dangerConfirmBtn"),

    fullAccessModal: document.getElementById("fullAccessModal"),
    fullAccessCancelBtn: document.getElementById("fullAccessCancelBtn"),
    fullAccessConfirmBtn: document.getElementById("fullAccessConfirmBtn"),

    attachBtn: document.getElementById("attachBtn"),
    fileInput: document.getElementById("fileInput"),
    fileChip: document.getElementById("fileChip"),
    fileChipName: document.getElementById("fileChipName"),
    fileChipRemove: document.getElementById("fileChipRemove"),

    toastContainer: document.getElementById("toastContainer"),
  };

  // 后端基地址（同源）
  const backendBase = "";

  // 默认系统提示词
  console.log("[SeekCode] UI v2.2 loaded");

  const DEFAULT_SYSTEM_PROMPT = `你是 SeekCode，一名通过 Windows 终端帮助用户完成任务的 AI 助手。

请严格按以下 JSON 格式输出，不要包含其他说明文字：

{
  "thought": "面向用户的思考说明（中文）",
  "command": "要执行的终端命令",
  "dangerous": false,
  "done": false,
  "memory_updates": {}
}

规则：
- command 必须是单条可执行命令，避免交互式命令。
- 如果命令可能删除、修改系统或用户数据，将 dangerous 设为 true。
- 任务完成时，将 done 设为 true，并给出总结。
- memory_updates 用于更新本地记忆文件中的关键状态。`;

  // 错误码到自然语言的映射
  const ERROR_MESSAGES = {
    insufficient_quota: { title: "余额不足", message: "API 账户余额不足，请充值后再试。" },
    rate_limit: { title: "请求过于频繁", message: "触发了接口速率限制，请稍等片刻再试。" },
    network_error: { title: "网络请求失败", message: "无法连接到 AI 服务，请检查网络。" },
    timeout: { title: "请求超时", message: "AI 响应时间过长，请检查网络或稍后重试。" },
    invalid_api_key: { title: "API Key 无效", message: "请检查设置中的 API Key 是否正确。" },
    parse_error: { title: "命令解析失败", message: "AI 返回的格式不正确，已终止当前任务。" },
    execution_error: { title: "命令执行失败", message: "终端命令执行出错，请查看详细输出。" },
    permission_denied: { title: "权限不足", message: "当前模式下无法执行该操作，请切换到更高权限。" },
    backup_limit_exceeded: { title: "单次删除文件超过上限", message: "本次删除操作涉及的文件数量过多，请分批处理或手动操作。" },
  };

  // 权限模式配置
  const PERMISSIONS = {
    chat: {
      name: "对话模式",
      icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
      color: "#6b9bd1",
    },
    standard: {
      name: "标准模式",
      icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
      color: "var(--success)",
    },
    full: {
      name: "完全访问模式",
      icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
      color: "var(--error)",
    },
  };

  // 状态
  let state = {
    sessionId: null,
    autoModel: true,
    selectedModel: "flash",
    activeModel: null,
    permission: "standard",
    isRunning: false,
    systemPrompt: DEFAULT_SYSTEM_PROMPT,
    attachedFile: null,
    messages: [],
    commandCount: 0,
    tokenCount: 0,
    memorySizeKB: 0,
    pendingDangerCommand: null,
    pendingPermissionChange: null,
    theme: "light",
    hasApiKey: false,
    maskedKey: "",
  };

  let eventSource = null;

  /**
   * 初始化
   */
  async function init() {
    bindEvents();
    autoResizeTextarea();
    animateIntro();
    await initBackend();
  }

  /**
   * 初始化后端连接：加载配置，复用最近的会话（没有才新建），连接 SSE。
   */
  async function initBackend() {
    try {
      const configRes = await fetch(`${backendBase}/api/config`);
      if (configRes.ok) {
        const config = await configRes.json();
        state.autoModel = config.auto_mode !== false;
        state.permission = config.permission || "standard";
        state.systemPrompt = config.system_prompt || DEFAULT_SYSTEM_PROMPT;
        state.hasApiKey = !!config.masked_key;
        state.maskedKey = config.masked_key || "";
        elements.autoModelToggle.checked = state.autoModel;
        elements.promptEditor.value = state.systemPrompt;
        updateApiKeyHint();
        updatePermissionUI();
        updateModelDisplay();
        if (!state.hasApiKey) {
          openApiKeyModal();
        }
      }
    } catch (err) {
      showToast("error", "后端连接失败", "无法连接到 SeekCode 后端，请确认服务已启动。");
      return;
    }

    try {
      const listRes = await fetch(`${backendBase}/api/sessions`);
      let sessionId = null;
      if (listRes.ok) {
        const listData = await listRes.json();
        const sessions = listData.sessions || [];
        if (sessions.length > 0) {
          sessionId = sessions[0].session_id;
        }
      }

      if (!sessionId) {
        const createRes = await fetch(`${backendBase}/api/sessions`, { method: "POST" });
        if (createRes.ok) {
          const data = await createRes.json();
          sessionId = data.session.session_id;
        } else {
          showToast("error", "会话创建失败", "无法创建默认会话。");
          return;
        }
      }

      state.sessionId = sessionId;
      connectEventSource();
      loadSessionList();
    } catch (err) {
      showToast("error", "会话初始化失败", err.message);
    }
  }

  /**
   * 连接 SSE 事件流
   */
  function connectEventSource() {
    if (!state.sessionId) return;
    if (eventSource) {
      eventSource.close();
    }
    eventSource = new EventSource(`${backendBase}/api/stream?session_id=${state.sessionId}`);

    eventSource.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        handleServerEvent(msg);
      } catch (err) {
        console.error("SSE 消息解析失败", e.data);
      }
    };

    eventSource.onerror = () => {
      // 后端重启或网络波动时自动重连
      setTimeout(() => connectEventSource(), 2000);
    };
  }

  /**
   * 处理服务端事件
   */
  function handleServerEvent(msg) {
    const event = msg.event;
    const payload = msg.payload || {};

    switch (event) {
      case "status":
        setStatus("running", payload.text || "执行中");
        break;
      case "thought":
        // 思维链先创建占位消息，完整展示思考过程
        addAssistantMessage("", payload.text || "");
        break;
      case "assistant":
        // 最终回复主内容
        addAssistantMessage(payload.text || "");
        break;
      case "command":
        appendCommandToLastAssistant(payload.command || "", payload.dangerous);
        break;
      case "terminal":
        addTerminalMessage(payload.command || "", payload.stdout || "", payload.stderr || "", payload.exit_code);
        state.commandCount += 1;
        break;
      case "danger_confirm":
        showDangerConfirm(payload.command || "").then((confirmed) => {
          fetch(`${backendBase}/api/confirm-danger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ request_id: payload.request_id, confirmed }),
          });
        });
        break;
      case "error":
        showToast("error", payload.title || "错误", payload.message || JSON.stringify(payload));
        finishRun();
        break;
      case "done":
        // 只有当总结与最后一条 AI 主回复明显不同时才额外展示，避免重复
        if (payload.summary) {
          const lastAssistant = elements.chatArea.querySelector(".assistant-message:last-child .assistant-reply");
          const lastText = lastAssistant ? lastAssistant.textContent.trim() : "";
          if (payload.summary.trim() && payload.summary.trim() !== lastText) {
            addAssistantMessage(payload.summary);
          }
        }
        finishRun();
        break;
      case "system":
        addSystemMessage(payload.text || "");
        break;
      default:
        break;
    }
  }

  /**
   * 将配置同步到后端
   */
  async function updateBackendConfig(updates) {
    try {
      await fetch(`${backendBase}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
    } catch (err) {
      console.error("同步配置失败", err);
    }
  }

  /**
   * 绑定事件
   */
  function bindEvents() {
    elements.sendBtn.addEventListener("click", handleSend);
    elements.stopBtn.addEventListener("click", handleStop);
    elements.composerInput.addEventListener("keydown", handleInputKeydown);
    elements.composerInput.addEventListener("input", autoResizeTextarea);
    elements.clearChatBtn.addEventListener("click", clearChat);

    // 侧边栏
    elements.sidebarToggleBtn.addEventListener("click", toggleSidebar);
    elements.sidebarOverlay.addEventListener("click", closeSidebar);
    elements.newChatBtn.addEventListener("click", createNewChat);
    elements.chatListToday.addEventListener("click", handleChatItemClick);
    elements.chatListYesterday.addEventListener("click", handleChatItemClick);
    elements.loadChatBtn.addEventListener("click", () => showToast("info", "加载对话", "请在侧边栏点击已有会话进行切换。"));
    elements.exportChatBtn.addEventListener("click", exportCurrentChat);

    // 模型选择
    elements.autoModelToggle.addEventListener("change", handleAutoModelToggle);
    elements.modelSelect.addEventListener("change", handleModelChange);

    // 权限模式
    elements.permissionTrigger.addEventListener("click", togglePermissionMenu);
    elements.permissionOptions.forEach((option) => {
      option.addEventListener("click", () => handlePermissionChange(option.dataset.permission));
    });
    document.addEventListener("click", closePermissionMenuOnOutside);

    // 设置弹窗
    elements.settingsBtn.addEventListener("click", openSettings);
    elements.settingsClose.addEventListener("click", closeSettings);
    elements.settingsModal.addEventListener("click", (e) => {
      if (e.target === elements.settingsModal) closeSettings();
    });
    elements.savePromptBtn.addEventListener("click", savePrompt);
    elements.resetPromptBtn.addEventListener("click", resetPrompt);
    elements.apiKeyToggle.addEventListener("click", () => togglePasswordVisibility(elements.apiKeyInput, elements.apiKeyToggle));
    elements.apiKeyClearBtn.addEventListener("click", clearApiKey);

    // API Key 弹窗
    elements.apiKeySaveBtn.addEventListener("click", saveApiKeyFromModal);
    elements.apiKeyLaterBtn.addEventListener("click", closeApiKeyModal);
    elements.firstApiKeyToggle.addEventListener("click", () => togglePasswordVisibility(elements.firstApiKeyInput, elements.firstApiKeyToggle));
    elements.firstApiKeyInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") saveApiKeyFromModal();
    });
    elements.apiKeyModal.addEventListener("click", (e) => {
      if (e.target === elements.apiKeyModal) closeApiKeyModal();
    });

    // 危险命令确认
    elements.dangerCancelBtn.addEventListener("click", cancelDanger);
    elements.dangerConfirmBtn.addEventListener("click", confirmDanger);
    elements.dangerModal.addEventListener("click", (e) => {
      if (e.target === elements.dangerModal) cancelDanger();
    });

    // 完全访问模式确认
    elements.fullAccessCancelBtn.addEventListener("click", cancelFullAccess);
    elements.fullAccessConfirmBtn.addEventListener("click", confirmFullAccess);
    elements.fullAccessModal.addEventListener("click", (e) => {
      if (e.target === elements.fullAccessModal) cancelFullAccess();
    });

    // 附件
    elements.attachBtn.addEventListener("click", () => elements.fileInput.click());
    elements.fileInput.addEventListener("change", handleFileAttach);
    elements.fileChipRemove.addEventListener("click", removeAttachedFile);

    // 主题
    elements.themeBtn.addEventListener("click", toggleTheme);

    // 监听系统主题变化
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addEventListener("change", (e) => {
      if (!localStorage.getItem("seekcode-theme")) {
        setTheme(e.matches ? "dark" : "light");
      }
    });

    // 窗口变化时关闭侧边栏
    window.addEventListener("resize", () => {
      if (window.innerWidth > 900) closeSidebar();
    });
  }

  /**
   * 开场动画
   */
  function animateIntro() {
    if (typeof gsap === "undefined") return;

    gsap.from(".title-bar", { y: -12, opacity: 0, duration: 0.45, ease: "power2.out" });
    gsap.from(".sidebar", { x: -24, opacity: 0, duration: 0.5, delay: 0.1, ease: "power2.out" });
    gsap.from(".chat-area", { opacity: 0, duration: 0.5, delay: 0.15, ease: "power2.out" });
    gsap.from(".input-area", { y: 16, opacity: 0, duration: 0.45, delay: 0.25, ease: "power2.out" });
  }

  /**
   * 发送消息
   */
  async function handleSend() {
    const text = elements.composerInput.value.trim();
    if (!text || state.isRunning) return;

    if (!state.hasApiKey) {
      openApiKeyModal();
      return;
    }

    addUserMessage(text);
    elements.composerInput.value = "";
    autoResizeTextarea();

    if (state.permission === "chat") {
      addAssistantMessage("当前处于**对话模式**，我只能陪你聊天，无法执行任何命令或操作电脑。如需执行任务，请切换到**标准模式**或**完全访问模式**。");
      return;
    }

    state.isRunning = true;
    updateInputState();
    setStatus("running", "请求中");

    try {
      const res = await fetch(`${backendBase}/api/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          text: text,
          auto_mode: state.autoModel,
          model: state.selectedModel,
          permission: state.permission,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "请求失败" }));
        showToast("error", "发送失败", err.detail || "无法发送消息");
        finishRun();
      }
    } catch (err) {
      showToast("error", "发送失败", err.message);
      finishRun();
    }
  }

  /**
   * 停止当前任务
   */
  async function handleStop() {
    try {
      await fetch(`${backendBase}/api/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: state.sessionId }),
      });
    } catch (err) {
      console.error("停止任务失败", err);
    }
    state.isRunning = false;
    addSystemMessage("任务已停止。");
    finishRun();
  }

  /**
   * 完成任务运行
   */
  function finishRun() {
    state.isRunning = false;
    setStatus("idle", "就绪");
    updateInputState();
  }

  /**
   * 添加用户消息
   */
  function addUserMessage(text) {
    const messageEl = createMessageElement("user", text);
    elements.messages.appendChild(messageEl);
    scrollToBottom();
  }

  /**
   * 添加 AI 消息
   */
  function addAssistantMessage(text, thought = "") {
    const last = elements.chatArea.lastElementChild;
    // 如果上一条是刚由 thought 创建的占位消息且主回复为空，就把回复填充进去
    if (last && last.classList.contains("assistant-message") && last.dataset.emptyReply === "true" && text) {
      const replyP = last.querySelector(".assistant-reply");
      if (replyP) {
        replyP.innerHTML = renderMarkdownLite(text);
        last.dataset.emptyReply = "false";
        scrollToBottom();
        return;
      }
    }
    const messageEl = createMessageElement("assistant", text, thought);
    elements.chatArea.appendChild(messageEl);
    scrollToBottom();
  }

  /**
   * 将命令追加到最后一条 AI 消息下方
   */
  function appendCommandToLastAssistant(command, dangerous) {
    const lastAssistant = elements.messages.querySelector(".assistant-message:last-child");
    if (!lastAssistant) {
      addAssistantMessage(`要执行的命令：\`\`\`${command}\`\`\``);
      return;
    }
    const content = lastAssistant.querySelector(".message-content");
    const note = dangerous ? "（危险命令，需确认后执行）" : "";
    const p = document.createElement("p");
    p.innerHTML = `<br>命令：${note}<br><code>${escapeHtml(command)}</code>`;
    content.appendChild(p);
    scrollToBottom();
  }

  /**
   * 添加系统消息
   */
  function addSystemMessage(text) {
    const messageEl = createMessageElement("system", text);
    elements.messages.appendChild(messageEl);
    scrollToBottom();
  }

  /**
   * 创建消息元素
   */
  function createMessageElement(type, content, thought = "") {
    const messageEl = document.createElement("div");
    messageEl.className = `message ${type}-message`;

    // 系统提示使用居中轻量样式，减少视觉干扰
    if (type === "system") {
      messageEl.innerHTML = `<div class="system-hint">${escapeHtml(content)}</div>`;
      if (typeof gsap !== "undefined") {
        gsap.from(messageEl, { y: 8, opacity: 0, duration: 0.3, ease: "power2.out" });
      }
      return messageEl;
    }

    let avatarHtml = "";
    if (type === "user") {
      avatarHtml = `<div class="message-avatar" aria-hidden="true">我</div>`;
    } else if (type === "assistant") {
      avatarHtml = `<div class="message-avatar ai-avatar" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
          <path d="M16 6L8 11v10l8 5 8-5V11l-8-5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          <path d="M16 16l-6-3.5v7L16 22l6-3.5v-7L16 16z" fill="currentColor"/>
        </svg>
      </div>`;
    }

    // 思维链 HTML（仅 AI 消息）
    let chainHtml = "";
    if (type === "assistant" && thought) {
      chainHtml = `
        <details class="chain-of-thought">
          <summary>思维链</summary>
          <pre>${escapeHtml(thought)}</pre>
        </details>`;
    }

    if (type === "assistant") {
      messageEl.dataset.emptyReply = (!content).toString();
    }

    messageEl.innerHTML = `
      ${avatarHtml}
      <div class="message-content">
        ${chainHtml}
        <p class="assistant-reply">${type === "user" ? escapeHtml(content) : renderMarkdownLite(content)}</p>
      </div>
    `;

    if (typeof gsap !== "undefined") {
      gsap.from(messageEl, { y: 12, opacity: 0, duration: 0.35, ease: "power2.out" });
    }

    return messageEl;
  }

  /**
   * 添加终端消息
   */
  function addTerminalMessage(command, output, stderr, exitCode) {
    const messageEl = document.createElement("div");
    messageEl.className = "message terminal-message";
    const fullOutput = [output, stderr].filter(Boolean).join("\n") || "命令执行成功，无输出。";
    messageEl.innerHTML = `
      <div class="terminal-header">
        <span class="terminal-badge">终端</span>
        <span>退出码 ${exitCode !== undefined ? exitCode : 0}</span>
      </div>
      <div class="terminal-block">
        <button class="copy-btn" title="复制输出">复制</button>
        <pre><code>${escapeHtml(fullOutput)}</code></pre>
      </div>
    `;

    const copyBtn = messageEl.querySelector(".copy-btn");
    copyBtn.addEventListener("click", () => copyToClipboard(fullOutput));

    elements.messages.appendChild(messageEl);
    scrollToBottom();

    if (typeof gsap !== "undefined") {
      gsap.from(messageEl, { y: 10, opacity: 0, duration: 0.3, ease: "power2.out" });
    }
  }

  /**
   * 清空对话
   */
  function clearChat() {
    elements.messages.innerHTML = "";
    state.commandCount = 0;
    state.tokenCount = 0;
  }

  /**
   * 侧边栏切换
   */
  function toggleSidebar() {
    const isOpen = elements.sidebar.classList.toggle("open");
    elements.sidebarOverlay.classList.toggle("open", isOpen);
  }

  function closeSidebar() {
    elements.sidebar.classList.remove("open");
    elements.sidebarOverlay.classList.remove("open");
  }

  /**
   * 新建对话
   */
  async function createNewChat() {
    try {
      const res = await fetch(`${backendBase}/api/sessions`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        state.sessionId = data.session.session_id;
        clearChat();
        addAssistantMessage("新建了一个对话。告诉我你想完成什么任务？");
        connectEventSource();
        loadSessionList();
      } else {
        showToast("error", "新建失败", "无法创建新会话。");
      }
    } catch (err) {
      showToast("error", "新建失败", err.message);
    }
    closeSidebar();
  }

  /**
   * 加载会话列表
   */
  async function loadSessionList() {
    try {
      const res = await fetch(`${backendBase}/api/sessions`);
      if (!res.ok) return;
      const data = await res.json();
      const sessions = data.sessions || [];
      renderSessionList(sessions);
    } catch (err) {
      console.error("加载会话列表失败", err);
    }
  }

  /**
   * 渲染会话列表
   */
  function renderSessionList(sessions) {
    elements.chatListToday.innerHTML = "";
    elements.chatListYesterday.innerHTML = "";

    sessions.forEach((session) => {
      const item = document.createElement("li");
      item.className = "chat-item";
      if (session.session_id === state.sessionId) {
        item.classList.add("active");
      }
      item.dataset.id = session.session_id;
      item.innerHTML = `
        <span class="chat-item-icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </span>
        <span class="chat-item-title">${escapeHtml(session.title || "未命名对话")}</span>
      `;
      elements.chatListToday.appendChild(item);
    });
  }

  /**
   * 点击对话项
   */
  async function handleChatItemClick(e) {
    const item = e.target.closest(".chat-item");
    if (!item) return;

    if (e.target.closest(".chat-item-menu")) {
      showToast("info", "更多操作", "重命名、删除等功能将在后续版本实现。");
      return;
    }

    const sessionId = item.dataset.id;
    try {
      const res = await fetch(`${backendBase}/api/sessions/${sessionId}`);
      if (!res.ok) {
        showToast("error", "加载失败", "无法加载该会话。");
        return;
      }
      const data = await res.json();
      state.sessionId = sessionId;
      clearChat();
      // 恢复消息显示：assistant 只显示 thought，不显示原始 JSON
      (data.session.messages || []).forEach((msg) => {
        const role = msg.role;
        const content = msg.content || "";
        if (role === "user") {
          addUserMessage(content);
        } else if (role === "assistant") {
          const meta = msg.meta || {};
          const thought = meta.thought || extractThoughtFromJson(content) || "";
          const displayText = meta.reply || thought || content;
          addAssistantMessage(displayText, thought);
        } else if (role === "system") {
          addSystemMessage(content);
        } else if (role === "terminal") {
          const meta = msg.meta || {};
          addTerminalMessage(meta.command || "", meta.stdout || "", meta.stderr || "", meta.exit_code);
        }
      });
      connectEventSource();
      loadSessionList();
      closeSidebar();
    } catch (err) {
      showToast("error", "加载失败", err.message);
    }
  }

  /**
   * 导出当前会话
   */
  async function exportCurrentChat() {
    if (!state.sessionId) return;
    try {
      const res = await fetch(`${backendBase}/api/sessions/${state.sessionId}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: "markdown" }),
      });
      if (!res.ok) {
        showToast("error", "导出失败", "无法导出当前会话。");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `seekcode-${state.sessionId}.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showToast("success", "导出成功", "会话已下载为 Markdown 文件。");
    } catch (err) {
      showToast("error", "导出失败", err.message);
    }
  }

  /**
   * 自动模型切换
   */
  function handleAutoModelToggle(e) {
    state.autoModel = e.target.checked;
    updateModelDisplay();
    updateBackendConfig({ auto_mode: state.autoModel });
  }

  /**
   * 切换模型
   */
  function handleModelChange(e) {
    state.selectedModel = e.target.value;
    if (!state.autoModel) {
      state.activeModel = state.selectedModel;
    }
    updateModelDisplay();
  }

  /**
   * 更新模型显示
   */
  function updateModelDisplay() {
    elements.modelSelectRow.classList.toggle("disabled", state.autoModel);
    elements.modelSelect.disabled = state.autoModel;

    if (state.autoModel) {
      const name = state.activeModel ? translateModel(state.activeModel) : "等待判定";
      elements.modelActiveLabel.textContent = `实际使用：${name}`;
      elements.modelActiveLabel.classList.toggle("active", !!state.activeModel);
    } else {
      elements.modelActiveLabel.textContent = `已指定：${translateModel(state.selectedModel)}`;
      elements.modelActiveLabel.classList.add("active");
    }

    if (typeof gsap !== "undefined") {
      gsap.fromTo(
        elements.modelActiveLabel,
        { scale: 1 },
        { scale: 1.05, duration: 0.15, yoyo: true, repeat: 1, ease: "power2.out" }
      );
    }
  }

  /**
   * 权限模式菜单
   */
  function togglePermissionMenu() {
    elements.permissionMenu.classList.toggle("hidden");
  }

  function closePermissionMenuOnOutside(e) {
    if (!elements.permissionTrigger.contains(e.target) && !elements.permissionMenu.contains(e.target)) {
      elements.permissionMenu.classList.add("hidden");
    }
  }

  /**
   * 处理权限模式切换
   */
  function handlePermissionChange(permission) {
    if (permission === "full") {
      state.pendingPermissionChange = permission;
      elements.fullAccessModal.classList.remove("hidden");
      elements.permissionMenu.classList.add("hidden");
      return;
    }

    state.permission = permission;
    updatePermissionUI();
    elements.permissionMenu.classList.add("hidden");
    updateBackendConfig({ permission: state.permission });

    if (permission === "chat") {
      showToast("info", "已切换为对话模式", "AI 将仅进行文字对话，不会执行任何操作。");
    }
  }

  /**
   * 更新权限 UI
   */
  function updatePermissionUI() {
    const config = PERMISSIONS[state.permission];
    elements.permissionIcon.innerHTML = config.icon;
    elements.permissionIcon.style.color = config.color;
    elements.permissionLabel.textContent = config.name;

    elements.permissionOptions.forEach((option) => {
      option.classList.toggle("active", option.dataset.permission === state.permission);
    });
  }

  /**
   * 更新 API Key 提示文本
   */
  function updateApiKeyHint() {
    if (state.hasApiKey) {
      elements.apiKeyHint.textContent = `已保存：${state.maskedKey}`;
      elements.apiKeyHint.classList.add("configured");
      if (elements.apiKeyClearBtn) elements.apiKeyClearBtn.classList.remove("hidden");
    } else {
      elements.apiKeyHint.textContent = "未配置 API Key";
      elements.apiKeyHint.classList.remove("configured");
      if (elements.apiKeyClearBtn) elements.apiKeyClearBtn.classList.add("hidden");
    }
  }

  /**
   * 切换密码输入框的明文/密文显示
   */
  function togglePasswordVisibility(input, btn) {
    const isPassword = input.type === "password";
    input.type = isPassword ? "text" : "password";
    btn.setAttribute("aria-label", isPassword ? "隐藏密钥" : "显示密钥");
    const openEye = btn.querySelector(".eye-open");
    const closedEye = btn.querySelector(".eye-closed");
    if (openEye) openEye.classList.toggle("hidden", isPassword);
    if (closedEye) closedEye.classList.toggle("hidden", !isPassword);
  }

  /**
   * 清除已保存的 API Key
   */
  async function clearApiKey() {
    try {
      const res = await fetch(`${backendBase}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: "" }),
      });
      if (!res.ok) throw new Error(`清除失败 (${res.status})`);
      const data = await res.json();
      state.hasApiKey = !!data.config.masked_key;
      state.maskedKey = data.config.masked_key || "";
      updateApiKeyHint();
      showToast("warning", "密钥已删除", "本地保存的 API Key 已被清除，下次启动会重新提示输入。");
    } catch (err) {
      console.error("[SeekCode] 清除密钥失败:", err);
      showToast("error", "删除失败", err.message);
    }
  }

  /**
   * 重新拉取配置并更新本地状态
   */
  async function refreshConfig() {
    try {
      const res = await fetch(`${backendBase}/api/config`);
      if (!res.ok) return;
      const config = await res.json();
      state.hasApiKey = !!config.masked_key;
      state.maskedKey = config.masked_key || "";
      state.autoModel = config.auto_mode !== false;
      state.permission = config.permission || "standard";
      state.systemPrompt = config.system_prompt || DEFAULT_SYSTEM_PROMPT;
      updateApiKeyHint();
    } catch (err) {
      // 静默忽略，避免打扰用户
    }
  }

  /**
   * 完全访问模式确认
   */
  function cancelFullAccess() {
    state.pendingPermissionChange = null;
    elements.fullAccessModal.classList.add("hidden");
  }

  async function confirmFullAccess() {
    if (state.pendingPermissionChange) {
      state.permission = state.pendingPermissionChange;
      updatePermissionUI();
      state.pendingPermissionChange = null;
    }
    elements.fullAccessModal.classList.add("hidden");
    try {
      await updateBackendConfig({ permission: state.permission });
      showToast("warning", "完全访问模式已开启", "AI 获得最高权限，安全限制已启用。");
    } catch (err) {
      showToast("error", "保存失败", "权限模式保存失败，请重试。");
    }
  }

  /**
   * 设置状态
   */
  function setStatus(status, text) {
    elements.statusPill.className = `status-pill status-${status}`;
    elements.statusText.textContent = text;
    elements.inputStatus.textContent = text;
  }

  /**
   * 更新输入区状态
   */
  function updateInputState() {
    elements.sendBtn.classList.toggle("hidden", state.isRunning);
    elements.stopBtn.classList.toggle("hidden", !state.isRunning);
    elements.composerInput.disabled = state.isRunning;

    if (state.isRunning) {
      elements.composerInput.placeholder = "任务执行中，可点击停止按钮中断...";
    } else {
      elements.composerInput.placeholder = state.permission === "chat" ? "随便聊聊..." : "描述你要完成的任务...";
      elements.composerInput.focus();
    }
  }

  /**
   * 打开设置弹窗
   */
  async function openSettings() {
    elements.promptEditor.value = state.systemPrompt;
    elements.apiKeyInput.value = "";
    await refreshConfig();
    updateApiKeyHint();
    elements.settingsModal.classList.remove("hidden");
    elements.promptEditor.focus();
  }

  /**
   * 关闭设置弹窗
   */
  function closeSettings() {
    elements.settingsModal.classList.add("hidden");
  }

  /**
   * 保存提示词
   */
  async function savePrompt() {
    state.systemPrompt = elements.promptEditor.value.trim();
    const updates = { system_prompt: state.systemPrompt };
    const apiKey = elements.apiKeyInput.value.trim();
    if (apiKey) {
      updates.api_key = apiKey;
    }
    console.log("[SeekCode] 保存设置，请求字段:", Object.keys(updates));
    try {
      const res = await fetch(`${backendBase}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      console.log("[SeekCode] 保存设置响应状态:", res.status, res.ok);
      if (res.ok) {
        const data = await res.json();
        console.log("[SeekCode] 保存设置响应:", data.config?.masked_key ? "已配置" : "未配置");
        state.hasApiKey = !!data.config.masked_key;
        state.maskedKey = data.config.masked_key || "";
        updateApiKeyHint();
      }
      closeSettings();
      addSystemMessage("设置已保存，将在下次请求时生效。");
    } catch (err) {
      console.error("[SeekCode] 保存设置失败:", err);
      showToast("error", "保存失败", err.message);
    }
  }

  /**
   * 重置提示词
   */
  function resetPrompt() {
    elements.promptEditor.value = DEFAULT_SYSTEM_PROMPT;
  }

  /**
   * 打开 API Key 输入弹窗
   */
  function openApiKeyModal() {
    elements.firstApiKeyInput.value = "";
    elements.apiKeyModal.classList.remove("hidden");
    setTimeout(() => elements.firstApiKeyInput.focus(), 50);
  }

  /**
   * 关闭 API Key 输入弹窗
   */
  function closeApiKeyModal() {
    elements.apiKeyModal.classList.add("hidden");
  }

  /**
   * 保存 API Key（来自首次弹窗）
   */
  async function saveApiKeyFromModal() {
    const key = elements.firstApiKeyInput.value.trim();
    if (!key) {
      showToast("error", "请输入密钥", "API Key 不能为空。");
      return;
    }
    console.log("[SeekCode] 首次弹窗保存密钥，长度:", key.length);
    try {
      const res = await fetch(`${backendBase}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key }),
      });
      console.log("[SeekCode] 首次弹窗保存响应状态:", res.status, res.ok);
      if (!res.ok) throw new Error(`保存失败 (${res.status})`);
      const data = await res.json();
      console.log("[SeekCode] 首次弹窗保存响应:", data.config?.masked_key ? "已配置" : "未配置");
      state.hasApiKey = !!data.config.masked_key;
      state.maskedKey = data.config.masked_key || "";
      updateApiKeyHint();
      closeApiKeyModal();
      showToast("success", "密钥已保存", "API Key 已保存到本地，下次启动无需重新输入。");
    } catch (err) {
      console.error("[SeekCode] 首次弹窗保存失败:", err);
      showToast("error", "保存失败", err.message);
    }
  }

  /**
   * 显示危险命令确认
   */
  function showDangerConfirm(command) {
    return new Promise((resolve) => {
      state.pendingDangerCommand = { command, resolve };
      elements.dangerCommand.textContent = command;
      elements.dangerModal.classList.remove("hidden");
    });
  }

  function cancelDanger() {
    if (state.pendingDangerCommand) {
      state.pendingDangerCommand.resolve(false);
      state.pendingDangerCommand = null;
    }
    elements.dangerModal.classList.add("hidden");
  }

  function confirmDanger() {
    if (state.pendingDangerCommand) {
      state.pendingDangerCommand.resolve(true);
      state.pendingDangerCommand = null;
    }
    elements.dangerModal.classList.add("hidden");
  }

  /**
   * 处理文件附件
   */
  function handleFileAttach(e) {
    const file = e.target.files[0];
    if (!file) return;

    state.attachedFile = file;
    elements.fileChipName.textContent = file.name;
    elements.fileChip.classList.remove("hidden");
  }

  function removeAttachedFile() {
    state.attachedFile = null;
    elements.fileInput.value = "";
    elements.fileChip.classList.add("hidden");
  }

  /**
   * 切换主题
   */
  function toggleTheme() {
    const newTheme = state.theme === "light" ? "dark" : "light";
    setTheme(newTheme);
    localStorage.setItem("seekcode-theme", newTheme);
  }

  function setTheme(theme) {
    state.theme = theme;
    document.documentElement.classList.toggle("dark", theme === "dark");
  }

  /**
   * 显示 Toast 提示
   */
  function showToast(type, title, message) {
    const toast = document.createElement("div");
    toast.className = `toast ${type === "error" ? "" : type}`;

    let iconSvg = "";
    if (type === "error") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else if (type === "success") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
    } else if (type === "warning") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `
      <span class="toast-icon">${iconSvg}</span>
      <div>
        <strong>${escapeHtml(title)}</strong>
        <div style="font-size:12px;color:var(--foreground-muted);margin-top:2px">${escapeHtml(message)}</div>
      </div>
      <button class="toast-close" aria-label="关闭">×</button>
    `;

    toast.querySelector(".toast-close").addEventListener("click", () => toast.remove());

    elements.toastContainer.appendChild(toast);

    if (typeof gsap !== "undefined") {
      gsap.from(toast, { y: -10, opacity: 0, duration: 0.3, ease: "power2.out" });
    }

    setTimeout(() => {
      if (toast.parentNode) {
        if (typeof gsap !== "undefined") {
          gsap.to(toast, {
            opacity: 0,
            y: -10,
            duration: 0.25,
            ease: "power2.in",
            onComplete: () => toast.remove(),
          });
        } else {
          toast.remove();
        }
      }
    }, 5000);
  }

  /**
   * 键盘事件
   */
  function handleInputKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  /**
   * 自动调整文本框高度
   */
  function autoResizeTextarea() {
    const el = elements.composerInput;
    el.style.height = "auto";
    const newHeight = Math.min(el.scrollHeight, 160);
    el.style.height = newHeight + "px";
  }

  /**
   * 滚动到底部
   */
  function scrollToBottom() {
    elements.messages.scrollTop = elements.messages.scrollHeight;
  }

  /**
   * 复制到剪贴板
   */
  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast("success", "已复制", "终端输出已复制到剪贴板。");
    } catch (err) {
      showToast("error", "复制失败", "无法访问剪贴板。");
    }
  }

  /**
   * 翻译模型名
   */
  function translateModel(model) {
    const map = {
      flash: "DeepSeek V4 Flash",
      pro: "DeepSeek V4 Pro",
    };
    return map[model] || model;
  }

  /**
   * 转义 HTML
   */
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * 极简 Markdown 渲染
   */
  function renderMarkdownLite(text) {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }

  /**
   * 尝试从 AI 原始 JSON 内容中提取 thought 字段
   */
  function extractThoughtFromJson(text) {
    if (!text || !text.trim().startsWith("{")) return "";
    try {
      const codeMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
      const candidate = codeMatch ? codeMatch[1].trim() : text;
      const parsed = JSON.parse(candidate);
      return parsed.thought || "";
    } catch {
      return "";
    }
  }

  // 启动
  init();
})();
