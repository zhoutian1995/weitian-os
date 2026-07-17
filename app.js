(() => {
  "use strict";

  const tabs = ["home", "workflow", "system"];
  const pillNav = document.querySelector("#pillNav");
  const desktop = document.querySelector("#desktop");
  const heroJourney = document.querySelector("#heroJourney");
  const heroCopy = document.querySelector("#heroCopy");
  const portalScene = document.querySelector("#portalScene");
  const heroZoom = document.querySelector("#heroZoom");
  const windowLayer = document.querySelector("#windowLayer");
  const systemFrame = document.querySelector("#systemFrame");
  const clock = document.querySelector("#clock");
  let systemLoaded = false;
  let zIndex = 20;

  const windows = {
    start: {
      title: "START-HERE.md",
      html: `
        <span class="eyebrow">SYSTEM GUIDE</span>
        <h2>欢迎进入维天 OS。</h2>
        <p class="intro">这里是我用 AI 学习、实践、输出的运行记录。你可以从下面四条路径开始。</p>
        <div class="path-list">
          <div class="path-item"><b>01 · 想认识我</b><span>打开「关于维天」</span></div>
          <div class="path-item"><b>02 · 想看我怎么使用 AI</b><span>打开「AI 内容工作流」和「Skill 工具箱」</span></div>
          <div class="path-item"><b>03 · 想解决一个具体问题</b><span>进入「知识库」或「软硬件实验室」</span></div>
          <div class="path-item"><b>04 · 想看系统怎么进化</b><span>打开「升级日志」</span></div>
        </div>
        <div class="recent-box"><b>精选文章 · 待更新</b><small>你后续提供正式标题和公开链接后，这里展示三篇精选内容。</small></div>`
    },
    about: {
      title: "关于维天.md",
      html: `
        <div class="identity-grid">
          <img src="wille-portrait.jpg" alt="维天说真人照片">
          <div>
            <span class="eyebrow">PROFILE · WEITIAN</span>
            <h2>我是维天说。</h2>
            <p class="intro">INFP，三只猫的铲屎官。软硬件都玩，也习惯和 Agent 一起工作。</p>
          </div>
        </div>
        <div class="system-tags"><span>HARDWARE</span><span>SOFTWARE</span><span>LINUX</span><span>AI</span><span>AGENTS</span></div>
        <p>曾就职于大华股份、海康威视。以前研究 Linux 操作系统，现在用 AI 给自己的人生操作系统持续升级。</p>
        <h3>我现在主要做三件事</h3>
        <div class="path-list">
          <div class="path-item"><b>学习</b><span>用 AI 帮我理解新知识，但不让它替我思考。</span></div>
          <div class="path-item"><b>实践</b><span>把零散想法变成能运行的工具、Skill 和工作流。</span></div>
          <div class="path-item"><b>输出</b><span>把实践整理成文章、口播和长期知识资产。</span></div>
        </div>
        <p>这里会持续更新我正在使用的 AI 工作流、Skill、知识库方法和真实实践，你可以直接拿去试。</p>`
    },
    workflow: {
      title: "AI内容工作流.md",
      html: `
        <span class="eyebrow">CONTENT WORKFLOW</span>
        <h2>一个想法<br>→ 一份可以发布的内容<br>→ 一条能反复运行的工作流</h2>
        <p class="intro">不从工具清单开始，从你真正想表达的东西开始。</p>
        <button class="inline-action" type="button" data-switch="workflow">开始运行 →</button>`
    },
    skills: {
      title: "Skill工具箱/",
      html: `
        <span class="eyebrow">SKILLS · SELECT BY TASK</span>
        <h2>先选你要完成什么。</h2>
        <p>每个 Skill 最终都会说明：解决什么、需要什么、产出什么、怎么开始。</p>
        <div class="skill-groups">
          <section class="skill-category"><h3>01 · 做内容</h3><div class="skill-list"><span class="skill-item">选题 Skill</span><span class="skill-item">观点提炼</span><span class="skill-item">口播稿</span><span class="skill-item">标题</span><span class="skill-item">图文改写</span><span class="skill-item">长文写作</span></div></section>
          <section class="skill-category"><h3>02 · 做发布</h3><div class="skill-list"><span class="skill-item">平台适配</span><span class="skill-item">发布检查</span><span class="skill-item">小红书卡片</span><span class="skill-item">公众号排版</span><span class="skill-item">字幕</span></div></section>
          <section class="skill-category"><h3>03 · 做知识资产</h3><div class="skill-list"><span class="skill-item">知识库</span><span class="skill-item">网页收藏</span><span class="skill-item">拆书</span><span class="skill-item">内容归档</span><span class="skill-item">复盘</span></div></section>
          <section class="skill-category"><h3>04 · 搭自己的系统</h3><div class="skill-list"><span class="skill-item">个人品牌</span><span class="skill-item">网站生成</span><span class="skill-item">工作流设计</span><span class="skill-item">Skill 创建</span><span class="skill-item">Agent 配置</span></div></section>
        </div>`
    },
    knowledge: {
      title: "知识库.md",
      html: `
        <span class="eyebrow">KNOWLEDGE BASE</span>
        <h2>知识库不是收藏夹。</h2>
        <div class="path-list">
          <div class="path-item"><b>01</b><span>把有价值的内容收进来</span></div>
          <div class="path-item"><b>02</b><span>需要时能快速找到</span></div>
          <div class="path-item"><b>03</b><span>把知识重新变成内容和行动</span></div>
        </div>
        <div class="recent-box"><b>相关文章 · 待接入</b><small>《给 AI 搭一个维基百科：我的知识库搭建之路》</small></div>`
    },
    lab: {
      title: "软硬件实验室/",
      html: `
        <span class="eyebrow">HARDWARE × SOFTWARE</span>
        <h2>你现在想解决哪个问题？</h2>
        <div class="question-list">
          <div class="question-item"><b>想搭自己的 AI Agent</b><span>自建 AI Agent 放在哪里？</span></div>
          <div class="question-item"><b>想让 AI 有长期记忆</b><span>查看我的四层记忆系统</span></div>
          <div class="question-item"><b>想把 AI 跑在本地设备</b><span>查看 PicoClaw 移植实践</span></div>
          <div class="question-item"><b>想让多个 Agent 一起工作</b><span>查看多 Agent 团队实践</span></div>
        </div>`
    },
    cats: {
      title: "三只猫/",
      html: `
        <span class="eyebrow">SYSTEM ADMINISTRATORS</span>
        <h2>这里住着三位系统管理员。</h2>
        <p>猫咪姓名、照片和性格参数等待你提供。</p>
        <div class="cat-grid">
          <article class="cat-card"><strong>CAT-01</strong><p>姓名：待录入<br>系统职位：管理员<br>当前状态：待机</p></article>
          <article class="cat-card"><strong>CAT-02</strong><p>姓名：待录入<br>系统职位：管理员<br>当前状态：待机</p></article>
          <article class="cat-card"><strong>CAT-03</strong><p>姓名：待录入<br>系统职位：管理员<br>当前状态：待机</p></article>
        </div>`
    },
    log: {
      title: "升级日志.md",
      html: `
        <span class="eyebrow">WEITIAN OS · UPGRADE LOG</span>
        <h2>每次升级，都要留下能复用的东西。</h2>
        <div class="log-list">
          <div class="log-item"><b>v0.1</b><p><strong>搭建 AI 记忆系统</strong><br>让 Agent 不再每次从零开始。</p></div>
          <div class="log-item"><b>v0.2</b><p><strong>搭建 Skill 工具箱</strong><br>把重复方法变成可调用流程。</p></div>
          <div class="log-item"><b>v0.3</b><p><strong>搭建内容工作流</strong><br>从一个想法走到一份内容。</p></div>
          <div class="log-item"><b>v0.4</b><p><strong>建立个人网站</strong><br>把文章、工具和实践连接起来。</p></div>
        </div>`
    },
    now: {
      title: "当前运行.status",
      html: `
        <span class="eyebrow">RUNNING PROCESSES</span>
        <h2>当前运行</h2>
        <div class="path-list">
          <div class="path-item"><b>维天说内容体系</b><span>RUNNING</span></div>
          <div class="path-item"><b>AI 内容工作流</b><span>BUILDING</span></div>
          <div class="path-item"><b>Skill 工具箱</b><span>UPDATING</span></div>
          <div class="path-item"><b>个人知识库</b><span>RUNNING</span></div>
          <div class="path-item"><b>维天 OS 网站</b><span>PREVIEW</span></div>
        </div>`
    }
  };

  function launch() {
    desktop?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function updateHeroProgress() {
    if (!heroJourney || !portalScene || window.matchMedia("(max-width: 900px)").matches) return;
    const rect = heroJourney.getBoundingClientRect();
    const distance = Math.max(1, heroJourney.offsetHeight - innerHeight);
    const progress = Math.min(1, Math.max(0, -rect.top / distance));
    const eased = 1 - Math.pow(1 - progress, 3);
    const scale = 1 + eased * 2.15;
    portalScene.style.transform = `translate(-50%, -50%) scale(${scale})`;
    portalScene.style.filter = `saturate(${1 - progress * .12})`;
    heroCopy.style.opacity = String(Math.max(0, 1 - progress * 1.75));
    heroCopy.style.transform = `translateY(calc(-53% - ${progress * 35}px))`;
    heroZoom.textContent = `${Math.round(scale * 100)}%`;
  }

  let heroTicking = false;
  addEventListener("scroll", () => {
    if (heroTicking) return;
    heroTicking = true;
    requestAnimationFrame(() => { updateHeroProgress(); heroTicking = false; });
  }, { passive: true });
  addEventListener("resize", updateHeroProgress);

  function switchTab(tab) {
    if (!tabs.includes(tab)) tab = "home";
    document.querySelectorAll(".tab-page").forEach(page => page.classList.toggle("active", page.dataset.page === tab));
    pillNav.querySelectorAll("button").forEach(button => button.classList.toggle("active", button.dataset.tab === tab));
    if (tab === "system" && !systemLoaded) {
      systemFrame.src = systemFrame.dataset.src;
      systemLoaded = true;
    }
    history.replaceState(null, "", tab === "home" ? location.pathname : `#${tab}`);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  function makeDraggable(windowElement) {
    const handle = windowElement.querySelector("header");
    let originX = 0, originY = 0, startLeft = 0, startTop = 0;
    handle.addEventListener("pointerdown", event => {
      if (event.target.closest("button") || window.matchMedia("(max-width: 900px)").matches) return;
      const rect = windowElement.getBoundingClientRect();
      originX = event.clientX; originY = event.clientY; startLeft = rect.left; startTop = rect.top;
      windowElement.style.transform = "none";
      const move = moveEvent => {
        windowElement.style.left = `${Math.max(0, startLeft + moveEvent.clientX - originX)}px`;
        windowElement.style.top = `${Math.max(38, startTop + moveEvent.clientY - originY)}px`;
      };
      const up = () => { document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); };
      document.addEventListener("pointermove", move);
      document.addEventListener("pointerup", up);
    });
  }

  function openWindow(key) {
    const content = windows[key];
    if (!content) return;
    const existing = document.querySelector(`[data-window-key="${key}"]`);
    if (existing) { existing.style.zIndex = ++zIndex; return; }
    const fragment = document.querySelector("#window-shell").content.cloneNode(true);
    const windowElement = fragment.querySelector(".os-window");
    windowElement.dataset.windowKey = key;
    windowElement.style.zIndex = ++zIndex;
    windowElement.querySelector("header strong").textContent = content.title;
    windowElement.querySelector(".window-content").innerHTML = content.html;
    windowElement.querySelector("header button").addEventListener("click", () => windowElement.remove());
    windowElement.addEventListener("pointerdown", () => windowElement.style.zIndex = ++zIndex);
    const host = window.matchMedia("(max-width: 900px)").matches ? document.body : windowLayer;
    host.append(windowElement);
    makeDraggable(windowElement);
    windowElement.querySelector("[data-switch]")?.addEventListener("click", event => switchTab(event.currentTarget.dataset.switch));
  }

  const mobileItems = [
    ["01", "START-HERE", "start"], ["02", "关于维天", "about"], ["03", "AI 内容工作流", "workflow"],
    ["04", "Skill 工具箱", "skills"], ["05", "知识库", "knowledge"], ["06", "软硬件实验室", "lab"],
    ["07", "三只猫", "cats"], ["08", "升级日志", "log"]
  ];
  const mobileModules = document.querySelector("#mobileModules");
  mobileItems.forEach(([number, title, key]) => {
    const button = document.createElement("button");
    button.type = "button"; button.className = "mobile-module";
    button.innerHTML = `<b>${number}</b><span>${title}</span><i>→</i>`;
    button.addEventListener("click", () => openWindow(key));
    mobileModules.append(button);
  });

  pillNav.addEventListener("click", event => {
    const button = event.target.closest("button[data-tab]");
    if (button) switchTab(button.dataset.tab);
  });
  document.addEventListener("click", event => {
    const opener = event.target.closest("[data-window]");
    if (opener) openWindow(opener.dataset.window);
    const homeOpener = event.target.closest("[data-open-home]");
    if (homeOpener) { switchTab("home"); launch(); setTimeout(() => openWindow(homeOpener.dataset.openHome), 50); }
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") document.querySelector(".os-window:last-child")?.remove();
  });

  document.querySelectorAll(".workflow-card").forEach(card => {
    card.addEventListener("pointermove", event => {
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const rect = card.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const rotateY = ((x / rect.width) - .5) * 3.2;
      const rotateX = ((y / rect.height) - .5) * -3.2;
      card.style.setProperty("--mx", `${x}px`);
      card.style.setProperty("--my", `${y}px`);
      card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-5px)`;
    });
    card.addEventListener("pointerleave", () => { card.style.transform = ""; });
  });

  function updateClock() {
    clock.textContent = new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
  }
  updateClock(); setInterval(updateClock, 30000);

  updateHeroProgress();
  const initialTab = location.hash.slice(1);
  if (tabs.includes(initialTab)) switchTab(initialTab);
})();
