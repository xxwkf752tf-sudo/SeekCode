/* ============================================
   SeekCode 官网 - 交互与动画脚本
   GSAP + ScrollTrigger 驱动
   ============================================ */

// 等待 GSAP 加载完成
document.addEventListener("DOMContentLoaded", function () {
  // ============ 注册 GSAP 插件 ============
  gsap.registerPlugin(ScrollTrigger);

  // ============ 导航栏交互 ============
  const navbar = document.querySelector(".navbar");
  const navToggle = document.querySelector(".nav-toggle");
  const navLinks = document.querySelector(".nav-links");

  // 滚动时添加阴影和边框
  ScrollTrigger.create({
    start: "top -10",
    end: 99999,
    toggleClass: { className: "scrolled", targets: navbar },
  });

  // 移动端菜单切换
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", function () {
      navToggle.classList.toggle("open");
      navLinks.classList.toggle("open");
    });

    // 点击链接后关闭菜单
    navLinks.querySelectorAll(".nav-link").forEach(function (link) {
      link.addEventListener("click", function () {
        navToggle.classList.remove("open");
        navLinks.classList.remove("open");
      });
    });
  }

  // ============ 主题切换 ============
  const themeToggle = document.querySelector(".theme-toggle");
  const root = document.documentElement;

  // 读取本地存储的主题
  const savedTheme = localStorage.getItem("seekcode-theme");
  if (savedTheme === "dark") {
    root.classList.add("dark");
    updateThemeIcon(true);
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      const isDark = root.classList.toggle("dark");
      localStorage.setItem("seekcode-theme", isDark ? "dark" : "light");
      updateThemeIcon(isDark);
      ScrollTrigger.refresh();
    });
  }

  function updateThemeIcon(isDark) {
    if (!themeToggle) return;
    const sunIcon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
    const moonIcon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    themeToggle.innerHTML = isDark ? sunIcon : moonIcon;
  }

  // ============ Hero 入场动画 ============
  const heroElements = document.querySelectorAll("[data-hero]");
  if (heroElements.length > 0) {
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    heroElements.forEach(function (el, i) {
      const delay = parseFloat(el.dataset.heroDelay || (i * 0.12));
      tl.fromTo(el, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.7 }, delay);
    });
  }

  // ============ 滚动入场动画 (batch) ============
  const animateElements = document.querySelectorAll("[data-animate]");
  if (animateElements.length > 0) {
    ScrollTrigger.batch("[data-animate]", {
      start: "top 85%",
      onEnter: function (batch) {
        gsap.to(batch, {
          opacity: 1,
          y: 0,
          x: 0,
          scale: 1,
          duration: 0.6,
          stagger: 0.12,
          ease: "power2.out",
          overwrite: true,
        });
      },
      onLeaveBack: function (batch) {
        gsap.set(batch, { opacity: 0, y: 30, overwrite: true });
      },
    });
  }

  // ============ 统计数字滚动计数 ============
  const statNums = document.querySelectorAll("[data-count]");
  statNums.forEach(function (el) {
    const target = parseInt(el.dataset.count, 10);
    const suffix = el.dataset.suffix || "";
    const obj = { val: 0 };

    ScrollTrigger.create({
      trigger: el,
      start: "top 80%",
      once: true,
      onEnter: function () {
        gsap.to(obj, {
          val: target,
          duration: 2,
          ease: "power2.out",
          onUpdate: function () {
            el.textContent = Math.floor(obj.val) + suffix;
          },
        });
      },
    });
  });

  // ============ FAQ 手风琴 ============
  const faqItems = document.querySelectorAll(".faq-item");
  faqItems.forEach(function (item) {
    const question = item.querySelector(".faq-question");
    if (question) {
      question.addEventListener("click", function () {
        const isOpen = item.classList.contains("open");
        faqItems.forEach(function (other) { other.classList.remove("open"); });
        if (!isOpen) item.classList.add("open");
      });
    }
  });

  // ============ 联系表单提交 ============
  const contactForm = document.querySelector("#contactForm");
  if (contactForm) {
    contactForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const btn = contactForm.querySelector('button[type="submit"]');
      const originalText = btn.textContent;
      btn.textContent = "发送中...";
      btn.disabled = true;

      setTimeout(function () {
        btn.textContent = "已发送 ✓";
        contactForm.reset();
        setTimeout(function () {
          btn.textContent = originalText;
          btn.disabled = false;
        }, 2000);
      }, 1200);
    });
  }

  // ============ 终端打字动画 (首页 Hero) ============
  const terminalBody = document.querySelector("[data-terminal]");
  if (terminalBody) {
    const lines = [
      { html: '<span class="prompt">seekcode&gt;</span> <span class="cmd">把桌面所有 PNG 压缩到 80%</span>', delay: 800 },
      { html: '<span class="ai">[AI] 正在分析任务...</span>', delay: 600 },
      { html: '<span class="ai">[AI] 找到 23 个 PNG 文件，开始压缩</span>', delay: 700 },
      { html: '<span class="output">Processing: img_001.png ... <span class="success">done</span></span>', delay: 400 },
      { html: '<span class="output">Processing: screenshot.png ... <span class="success">done</span></span>', delay: 400 },
      { html: '<span class="output">Processing: banner.png ... <span class="success">done</span></span>', delay: 400 },
      { html: '<span class="ai">[AI] 全部完成！23 个文件已压缩到 D:\\backup</span>', delay: 500 },
    ];

    let lineIndex = 0;
    const originalContent = terminalBody.innerHTML;
    terminalBody.innerHTML = "";

    function typeNextLine() {
      if (lineIndex >= lines.length) {
        setTimeout(function () {
          terminalBody.innerHTML = "";
          lineIndex = 0;
          typeNextLine();
        }, 3000);
        return;
      }

      const line = lines[lineIndex];
      const div = document.createElement("div");
      div.style.opacity = "0";
      div.innerHTML = line.html;
      terminalBody.appendChild(div);

      gsap.to(div, {
        opacity: 1,
        duration: 0.3,
        ease: "power2.out",
        onComplete: function () {
          terminalBody.scrollTop = terminalBody.scrollHeight;
        },
      });

      lineIndex++;
      setTimeout(typeNextLine, line.delay);
    }

    // 当终端进入视口时开始播放
    ScrollTrigger.create({
      trigger: terminalBody,
      start: "top 90%",
      once: true,
      onEnter: typeNextLine,
    });
  }

  // ============ 视差效果 ============
  const parallaxElements = document.querySelectorAll("[data-parallax]");
  parallaxElements.forEach(function (el) {
    const speed = parseFloat(el.dataset.parallax) || 0.3;
    gsap.to(el, {
      y: function () { return -(window.innerHeight * speed); },
      ease: "none",
      scrollTrigger: {
        trigger: el,
        start: "top bottom",
        end: "bottom top",
        scrub: 1,
      },
    });
  });

  // ============ 平滑锚点滚动 ============
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener("click", function (e) {
      const target = this.getAttribute("href");
      if (target === "#") return;
      const el = document.querySelector(target);
      if (el) {
        e.preventDefault();
        const offset = 80;
        const top = el.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: top, behavior: "smooth" });
      }
    });
  });

  // ============ 当前页面高亮导航 ============
  const currentPage = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-link").forEach(function (link) {
    const href = link.getAttribute("href");
    if (href === currentPage || (currentPage === "" && href === "index.html")) {
      link.classList.add("active");
    }
  });

  // ============ 客服悬浮组件 ============
  var csFab = document.querySelector("#csFab");
  var csWindow = document.querySelector("#csWindow");
  var csOverlay = document.querySelector("#csOverlay");
  var csBadge = document.querySelector("#csFabBadge");
  var csClose = document.querySelector("#csClose");
  var csInput = document.querySelector("#csInput");
  var csSendBtn = document.querySelector("#csSendBtn");
  var csSentNotice = document.querySelector("#csSentNotice");

  if (csFab && csWindow) {
    var csIsOpen = false;
    var csBody = csWindow.querySelector(".cs-body");
    var csHistory = [];

    function csOpen() {
      csIsOpen = true;
      csWindow.classList.add("open");
      csFab.classList.add("active");
      if (csOverlay) csOverlay.classList.add("open");
      // 清除未读标识
      if (csBadge) csBadge.classList.add("hidden");
      // 聚焦输入框
      setTimeout(function () { if (csInput) csInput.focus(); }, 300);
    }

    function csCloseWindow() {
      csIsOpen = false;
      csWindow.classList.remove("open");
      csFab.classList.remove("active");
      if (csOverlay) csOverlay.classList.remove("open");
    }

    function csToggle() {
      if (csIsOpen) csCloseWindow(); else csOpen();
    }

    // 按钮点击切换
    csFab.addEventListener("click", csToggle);

    // 关闭按钮
    if (csClose) csClose.addEventListener("click", csCloseWindow);

    // 移动端遮罩点击关闭
    if (csOverlay) csOverlay.addEventListener("click", csCloseWindow);

    // Escape 键关闭
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && csIsOpen) csCloseWindow();
    });

    // FAQ 快捷入口展开/收起
    var csFaqItems = document.querySelectorAll(".cs-faq-item");
    csFaqItems.forEach(function (item) {
      item.addEventListener("click", function () {
        var isOpen = item.classList.contains("open");
        csFaqItems.forEach(function (other) { other.classList.remove("open"); });
        if (!isOpen) item.classList.add("open");
      });
    });

    // 留言发送（真实接入 AI 客服后端，流式渲染回复）
    if (csSendBtn && csInput) {
      // 生成一条消息气泡，返回气泡元素以便后续更新
      function csAddMessage(role, text) {
        var msg = document.createElement("div");
        msg.className = "cs-msg " + role;
        if (role === "ai") {
          var av = document.createElement("div");
          av.className = "cs-msg-avatar";
          av.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1v-7h3zM3 19a2 2 0 0 0 2 2h1v-7H3z"/></svg>';
          msg.appendChild(av);
        }
        var bubble = document.createElement("div");
        bubble.className = "cs-msg-bubble";
        bubble.textContent = text;
        msg.appendChild(bubble);
        if (csBody) csBody.appendChild(msg);
        return bubble;
      }

      function csScrollToBottom() {
        if (csBody) csBody.scrollTop = csBody.scrollHeight;
      }

      // 调用后端 /api/customer-service，流式读取 SSE 并渲染
      async function csStream(userText) {
        csAddMessage("user", userText);
        var aiBubble = csAddMessage("ai", "");
        aiBubble.innerHTML =
          '<div class="cs-typing"><span></span><span></span><span></span></div>';
        csScrollToBottom();

        var fullText = "";
        try {
          var resp = await fetch("/api/customer-service", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: userText, history: csHistory }),
          });

          if (!resp.ok) {
            var errData = await resp.json().catch(function () { return {}; });
            aiBubble.textContent =
              errData.message || "客服暂时不可用，请通过邮箱 wuhongzheng2026@outlook.com 联系我们。";
            csHistory.push({ role: "user", content: userText });
            csHistory.push({ role: "assistant", content: aiBubble.textContent });
            return;
          }

          if (!resp.body || !window.ReadableStream) {
            aiBubble.textContent = "当前浏览器不支持流式回复，请刷新后重试。";
            return;
          }

          var reader = resp.body.getReader();
          var decoder = new TextDecoder("utf-8");
          var buffer = "";
          while (true) {
            var r = await reader.read();
            if (r.done) break;
            buffer += decoder.decode(r.value, { stream: true });
            var parts = buffer.split("\n\n");
            buffer = parts.pop();
            for (var i = 0; i < parts.length; i++) {
              var line = parts[i].trim();
              if (!line.startsWith("data:")) continue;
              var payload = line.slice(5).trim();
              if (payload === "[DONE]") continue;
              var obj;
              try {
                obj = JSON.parse(payload);
              } catch (e) {
                continue;
              }
              if (obj.token) {
                fullText += obj.token;
                aiBubble.textContent = fullText;
                csScrollToBottom();
              } else if (obj.error) {
                aiBubble.textContent = obj.message || "客服服务出错，请稍后重试。";
              }
            }
          }
          if (!fullText) aiBubble.textContent = "（未收到回复，请稍后再试）";
        } catch (e) {
          aiBubble.textContent =
            "网络异常，留言未能发送。你也可以通过邮箱 wuhongzheng2026@outlook.com 联系我们。";
        } finally {
          csHistory.push({ role: "user", content: userText });
          csHistory.push({ role: "assistant", content: fullText || aiBubble.textContent });
          csSendBtn.disabled = false;
        }
      }

      function csSendMessage() {
        var text = csInput.value.trim();
        if (!text) return;
        csSendBtn.disabled = true;
        csInput.value = "";
        csInput.style.height = "auto";
        csStream(text);
      }

      csSendBtn.addEventListener("click", csSendMessage);

      // Enter 发送，Shift+Enter 换行
      csInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          csSendMessage();
        }
      });

      // 自适应高度
      csInput.addEventListener("input", function () {
        csInput.style.height = "auto";
        csInput.style.height = Math.min(csInput.scrollHeight, 80) + "px";
      });
    }

    // 页面加载 3 秒后显示未读消息提示
    setTimeout(function () {
      if (!csIsOpen && csBadge) {
        csBadge.classList.remove("hidden");
      }
    }, 3000);
  }

  // ============ 刷新 ScrollTrigger (字体加载后) ============
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () {
      ScrollTrigger.refresh();
    });
  }

  // 窗口加载后刷新
  window.addEventListener("load", function () {
    ScrollTrigger.refresh();
  });
});
