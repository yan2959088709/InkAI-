/* ============================================================
 * InkAI Frontend v2.1 —— 彻底可交互版
 *
 * 修复 v2.0 三大问题：
 *  1. hash 不变时 route 不触发 → 全部跳转走 App.go() 强制刷新
 *  2. 5 阶段时间轴连线乱跑 → 改用 flex + 容器底层伪元素 SVG-like 横线
 *  3. 没有编辑能力 → 加 metadata / characters / storyline / chapter 编辑
 *
 * 路由：
 *   #/                       主页（小说列表 + 新建）
 *   #/novel/:id              单本工作流
 *   #/novel/:id/chapters     章节网格
 *   #/novel/:id/chapter/:n   单章阅读 + 编辑切换
 *   #/novel/:id/audit        全本审计（雷达图）
 *   #/novel/:id/edit         小说信息编辑（meta/角色/storyline）
 * ============================================================ */

const API = "/api";
const State = {
    genres: [],
    novels: [],
    currentNovelId: null,
    currentNovel: null,
    pollers: {},
    chartInstances: {},
    /* v2.2 新增 */
    homeFilter: { q: "", sort: "updated_desc", stage: "all" },
    reader: { fontSize: 17, fullscreen: false },   // 阅读器偏好（启动时从 localStorage 读）
    runningTaskIds: new Set(),                      // 用于 dock 显示
    activeTaskOnNovel: {},                          // novelId -> taskId（防重复跑）
    bp: { expandedVolume: null },                   // 蓝图当前展开的卷
    bpVolumeCards: {},                              // novelId -> volumeIdx -> chapter_cards (缓存)
};

/* 启动时从 localStorage 恢复偏好 */
try {
    const saved = JSON.parse(localStorage.getItem("inkai_reader_prefs") || "{}");
    if (saved.fontSize) State.reader.fontSize = saved.fontSize;
} catch (_) {}

/* ============== 工具 ============== */
const Util = {
    async req(path, opts = {}) {
        const r = await fetch(API + path, {
            headers: { "Content-Type": "application/json", "Cache-Control": "no-cache" },
            ...opts,
        });
        let j;
        try { j = await r.json(); } catch (_) { j = { ok: false, error: `HTTP ${r.status}` }; }
        if (!r.ok || !j.ok) throw new Error(j.error || `请求失败 (HTTP ${r.status})`);
        return j.data;
    },
    get(path) { return this.req(path); },
    post(path, body) { return this.req(path, { method: "POST", body: JSON.stringify(body || {}) }); },
    put(path, body) { return this.req(path, { method: "PUT", body: JSON.stringify(body || {}) }); },
    del(path) { return this.req(path, { method: "DELETE" }); },

    showLoading(msg = "处理中…") {
        document.getElementById("loadingMsg").textContent = msg;
        document.getElementById("loadingOverlay").style.display = "flex";
    },
    hideLoading() { document.getElementById("loadingOverlay").style.display = "none"; },
    toast(msg, type = "info", ttl = 3500) {
        const map = { info: "primary", success: "success", warn: "warning", error: "danger" };
        const icon = { info: "info-circle", success: "check-circle", warn: "exclamation-triangle", error: "exclamation-circle" };
        const id = "toast-" + Date.now() + Math.random().toString(36).slice(2, 6);
        const html = `
            <div class="toast text-bg-${map[type] || "primary"} border-0" role="alert" id="${id}">
                <div class="d-flex">
                    <div class="toast-body"><i class="fas fa-${icon[type] || "info-circle"} me-2"></i>${this.escape(msg)}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>`;
        const c = document.getElementById("toastContainer");
        c.insertAdjacentHTML("beforeend", html);
        const el = document.getElementById(id);
        const t = new bootstrap.Toast(el, { delay: ttl });
        t.show();
        el.addEventListener("hidden.bs.toast", () => el.remove());
    },
    fmtTs(ts) {
        if (!ts) return "";
        const d = new Date(ts * 1000);
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    },
    escape(s) {
        if (s == null) return "";
        return String(s).replace(/[&<>"']/g, c =>
            ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    },
    paragraphize(text) {
        if (!text) return "";
        return text.split(/\n+/).map(p => p.trim()).filter(Boolean)
            .map(p => `<p>${this.escape(p)}</p>`).join("");
    },
    confirm(msg) { return window.confirm(msg); },
    /* 销毁所有 chart 防止残留 canvas 报错 */
    destroyCharts() {
        Object.values(State.chartInstances).forEach(c => { try { c.destroy(); } catch (_) {} });
        State.chartInstances = {};
    },
    /* 关掉所有打开中的 modal（导航前清理） */
    closeAllModals() {
        document.querySelectorAll(".modal.show").forEach(el => {
            const m = bootstrap.Modal.getInstance(el);
            if (m) m.hide();
        });
    },
    /* 给一个元素加保存高亮 */
    flash(selector) {
        const el = document.querySelector(selector);
        if (!el) return;
        el.classList.remove("saved-flash");
        // 强制 reflow 重启动画
        void el.offsetWidth;
        el.classList.add("saved-flash");
        setTimeout(() => el.classList.remove("saved-flash"), 1000);
    },
};

/* ============== 路由 ============== */
function parseHash() {
    const h = (location.hash || "#/").replace(/^#/, "");
    const parts = h.split("/").filter(Boolean);
    if (parts.length === 0) return { name: "home" };
    if (parts[0] === "novel" && parts[1]) {
        if (parts[2] === "chapter" && parts[3]) return { name: "chapter", novelId: parts[1], n: parseInt(parts[3]) };
        if (parts[2] === "chapters") return { name: "chapters", novelId: parts[1] };
        if (parts[2] === "audit") return { name: "audit", novelId: parts[1] };
        if (parts[2] === "edit") return { name: "edit", novelId: parts[1] };
        return { name: "novel", novelId: parts[1] };
    }
    if (parts[0] === "genres") {
        if (parts[1] === "new") return { name: "genre_new" };
        if (parts[1]) return { name: "genre_edit", genreName: parts[1] };
        return { name: "genres" };
    }
    return { name: "home" };
}

async function route() {
    const r = parseHash();
    Util.closeAllModals();
    Util.destroyCharts();
    Util.hideLoading();   // 兜底关掉残留 overlay
    // 离开阅读器：移除滚动监听 + 退出全屏样式
    if (State._onScroll) {
        window.removeEventListener("scroll", State._onScroll);
        State._onScroll = null;
    }
    if (r.name !== "chapter") {
        document.body.classList.remove("reader-fullscreen");
        State.reader.fullscreen = false;
    }
    const root = document.getElementById("mainContainer");
    root.innerHTML = `<div class="text-center text-muted py-5"><div class="spinner-border text-primary"></div></div>`;
    try {
        if (r.name === "home")          await renderHome(root);
        else if (r.name === "novel")    await renderNovel(root, r.novelId);
        else if (r.name === "chapters") await renderChaptersGrid(root, r.novelId);
        else if (r.name === "chapter")  await renderChapter(root, r.novelId, r.n);
        else if (r.name === "audit")    await renderAudit(root, r.novelId);
        else if (r.name === "edit")     await renderEdit(root, r.novelId);
        else if (r.name === "genres")     await renderGenresHome(root);
        else if (r.name === "genre_new")  {
            const preset = State._llmPreset;
            State._llmPreset = null;
            await renderGenreEdit(root, null, preset);
        }
        else if (r.name === "genre_edit") await renderGenreEdit(root, r.genreName);
        else root.innerHTML = `<div class="alert alert-warning">未知路由</div>`;
    } catch (e) {
        root.innerHTML = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-bug me-2"></i>页面加载失败</h5>
                <div class="small">${Util.escape(e.message)}</div>
                <button class="btn btn-sm btn-outline-light mt-2" onclick="App.go('#/')">返回主页</button>
            </div>`;
    }
}

window.addEventListener("hashchange", route);

/* ============================================================
 * 视图 1：主页
 * ============================================================ */
async function renderHome(root) {
    State.novels = await Util.get("/novels");
    if (State.genres.length === 0) State.genres = await Util.get("/genres");
    State.currentNovelId = null;

    root.innerHTML = `
        <div class="hero-section mb-4">
            <div class="row align-items-center">
                <div class="col-lg-8">
                    <h1 class="hero-title mb-2">
                        <i class="fas fa-feather-alt"></i>
                        InkAI <span class="text-muted fs-5 ms-2">智能小说创作系统</span>
                    </h1>
                    <p class="text-muted mb-0">
                        基于 LLM 的多智能体超长篇小说自动写作管道 ·
                        <span class="badge bg-light text-dark">v2.2</span>
                    </p>
                </div>
                <div class="col-lg-4 text-lg-end mt-3 mt-lg-0">
                    <button class="btn btn-primary btn-lg" onclick="App.openCreateModal()">
                        <i class="fas fa-plus-circle me-2"></i>开始一本新小说
                    </button>
                </div>
            </div>
        </div>

        <div class="d-flex flex-wrap gap-2 align-items-end mb-3">
            <h4 class="mb-0 me-3"><i class="fas fa-book-open me-2 text-primary"></i>已有小说</h4>
            <div class="input-group home-filter-search">
                <span class="input-group-text"><i class="fas fa-search"></i></span>
                <input class="form-control" id="homeQ" placeholder="搜索标题 / 主角 / 题材"
                       value="${Util.escape(State.homeFilter.q)}" oninput="App.applyHomeFilter()" />
            </div>
            <select class="form-select home-filter-select" id="homeSort" onchange="App.applyHomeFilter()">
                <option value="updated_desc"  ${State.homeFilter.sort === "updated_desc" ? "selected" : ""}>最近更新</option>
                <option value="updated_asc"   ${State.homeFilter.sort === "updated_asc"  ? "selected" : ""}>最早更新</option>
                <option value="title_asc"     ${State.homeFilter.sort === "title_asc"    ? "selected" : ""}>标题 A→Z</option>
                <option value="progress_desc" ${State.homeFilter.sort === "progress_desc"? "selected" : ""}>进度多→少</option>
                <option value="progress_asc"  ${State.homeFilter.sort === "progress_asc" ? "selected" : ""}>进度少→多</option>
                <option value="audit_desc"    ${State.homeFilter.sort === "audit_desc"   ? "selected" : ""}>审计分高→低</option>
            </select>
            <select class="form-select home-filter-select" id="homeStage" onchange="App.applyHomeFilter()">
                <option value="all"        ${State.homeFilter.stage === "all"        ? "selected" : ""}>全部阶段</option>
                <option value="no_blueprint"${State.homeFilter.stage === "no_blueprint"? "selected" : ""}>未生成蓝图</option>
                <option value="no_chapter" ${State.homeFilter.stage === "no_chapter" ? "selected" : ""}>未开始写章</option>
                <option value="in_progress"${State.homeFilter.stage === "in_progress"? "selected" : ""}>进行中</option>
                <option value="finished"   ${State.homeFilter.stage === "finished"   ? "selected" : ""}>已完成</option>
                <option value="canon_err"  ${State.homeFilter.stage === "canon_err"  ? "selected" : ""}>Canon 异常</option>
            </select>
            <div class="text-muted small ms-auto">
                共 ${State.novels.length} 本 · 题材包 ${State.genres.length} 个
                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="App.go('#/')" title="刷新">
                    <i class="fas fa-rotate"></i>
                </button>
            </div>
        </div>

        <div class="row g-4" id="novelGrid"></div>
    `;
    renderNovelGrid();
}

/** 应用搜索/排序/筛选并重渲染卡片 */
function renderNovelGrid() {
    let list = State.novels.slice();
    const f = State.homeFilter;
    if (f.q.trim()) {
        const q = f.q.trim().toLowerCase();
        list = list.filter(n =>
            (n.title || "").toLowerCase().includes(q) ||
            (n.main_character_name || "").toLowerCase().includes(q) ||
            (n.genre_display || n.genre || "").toLowerCase().includes(q)
        );
    }
    if (f.stage !== "all") {
        list = list.filter(n => {
            const s = n.stage || {};
            const c = n.canon_summary || {};
            const total = n.total_chapters_planned || 0;
            if (f.stage === "no_blueprint") return !s.blueprint;
            if (f.stage === "no_chapter")   return s.blueprint && (s.chapters_done || 0) === 0;
            if (f.stage === "in_progress")  return (s.chapters_done || 0) > 0 && (s.chapters_done || 0) < total;
            if (f.stage === "finished")     return total > 0 && (s.chapters_done || 0) >= total;
            if (f.stage === "canon_err")    return (c.ERROR || 0) > 0;
            return true;
        });
    }
    list.sort((a, b) => {
        if (f.sort === "title_asc")     return (a.title || "").localeCompare(b.title || "");
        if (f.sort === "updated_asc")   return (a.updated_at || "").localeCompare(b.updated_at || "");
        if (f.sort === "progress_desc") return ((b.stage||{}).chapters_done||0) - ((a.stage||{}).chapters_done||0);
        if (f.sort === "progress_asc")  return ((a.stage||{}).chapters_done||0) - ((b.stage||{}).chapters_done||0);
        if (f.sort === "audit_desc")    return (b.audit_overall_score || 0) - (a.audit_overall_score || 0);
        return (b.updated_at || "").localeCompare(a.updated_at || "");
    });
    const grid = document.getElementById("novelGrid");
    if (!grid) return;
    grid.innerHTML = list.map(novelCard).join("") ||
        (State.novels.length === 0 ? emptyState() : `
        <div class="col-12">
            <div class="empty-state text-center py-4">
                <i class="fas fa-filter fa-2x text-muted mb-2"></i>
                <div class="text-muted">没有匹配的小说</div>
                <button class="btn btn-sm btn-link" onclick="App.clearHomeFilter()">清除筛选</button>
            </div>
        </div>`);
}

function emptyState() {
    return `<div class="col-12">
        <div class="empty-state text-center py-5">
            <i class="fas fa-book-dead fa-3x text-muted mb-3"></i>
            <h5 class="text-muted mb-3">还没有小说</h5>
            <button class="btn btn-primary" onclick="App.openCreateModal()">
                <i class="fas fa-plus-circle me-2"></i>开始第一本小说
            </button>
        </div>
    </div>`;
}

function novelCard(n) {
    const stage = n.stage || {};
    const c = n.canon_summary || {};
    const ce = c.ERROR || 0, cw = c.WARNING || 0;
    const audit = (n.audit_overall_score != null) ? `${n.audit_overall_score}` : "—";
    const auditClass = n.audit_overall_score >= 90 ? "high" :
                       n.audit_overall_score >= 70 ? "mid" : "low";
    const stageBadge = (label, ok) =>
        `<span class="stage-pill ${ok ? "done" : "todo"}">
             <i class="fas fa-${ok ? "check" : "circle-dot"} me-1"></i>${label}
         </span>`;

    return `
    <div class="col-md-6 col-xl-4">
        <div class="card novel-card h-100 shadow-sm" onclick="App.go('#/novel/${n.novel_id}')">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="card-title mb-0">${Util.escape(n.title) || "&lt;未命名&gt;"}</h5>
                    <span class="badge bg-light text-dark genre-badge">${Util.escape(n.genre_display || n.genre || "")}</span>
                </div>
                <div class="text-muted small mb-3">
                    <i class="fas fa-user me-1"></i>${Util.escape(n.main_character_name) || "—"}
                    ${n.supporting_character_names && n.supporting_character_names.length
                        ? ` · 配角 ${n.supporting_character_names.length}` : ""}
                </div>
                <div class="progress chapter-progress mb-2" style="height:8px">
                    <div class="progress-bar bg-success"
                         style="width:${(stage.chapters_done / Math.max(1, n.total_chapters_planned)) * 100}%"></div>
                </div>
                <div class="d-flex justify-content-between small text-muted mb-3">
                    <span><i class="fas fa-list-ol me-1"></i>${stage.chapters_done}/${n.total_chapters_planned} 章</span>
                    <span class="audit-score ${auditClass}">
                        <i class="fas fa-gauge-high me-1"></i>审计 ${audit}
                    </span>
                </div>
                <div class="stage-row mb-2">
                    ${stageBadge("Init", true)}
                    ${stageBadge("Storyline", stage.storyline_expanded)}
                    ${stageBadge("Canon", stage.canon_report)}
                    ${stageBadge("Blueprint", stage.blueprint)}
                    ${stageBadge("Chapters", stage.chapters_done > 0)}
                </div>
                ${ce + cw > 0 ? `
                <div class="small text-warning"><i class="fas fa-triangle-exclamation me-1"></i>
                  Canon ERROR=${ce} WARNING=${cw}</div>` : ""}
            </div>
            <div class="card-footer bg-light d-flex justify-content-between align-items-center">
                <span class="text-muted small">${Util.escape(n.novel_id.slice(0, 8))}…</span>
                <div class="btn-group btn-group-sm" onclick="event.stopPropagation()">
                    <button class="btn btn-outline-primary" onclick="App.go('#/novel/${n.novel_id}')">
                        <i class="fas fa-arrow-right"></i> 进入
                    </button>
                    <button class="btn btn-outline-danger" onclick="App.deleteNovel('${n.novel_id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>`;
}

/* ============================================================
 * 视图 2：单本小说工作流
 * ============================================================ */
async function renderNovel(root, novelId) {
    const n = await Util.get(`/novels/${novelId}`);
    State.currentNovelId = novelId;
    State.currentNovel = n;

    const s = n.stage || {};
    const c = n.canon_summary || {};
    const auditScore = n.audit_overall_score;

    root.innerHTML = `
    <div class="d-flex align-items-center mb-4 flex-wrap gap-2">
        <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/')"><i class="fas fa-arrow-left"></i></button>
        <div class="flex-grow-1">
            <h3 class="mb-1">${Util.escape(n.title)}
                <button class="btn btn-sm btn-link p-0 ms-1" onclick="App.openMetaEditor()" title="编辑信息">
                    <i class="fas fa-pen text-muted small"></i>
                </button>
            </h3>
            <div class="text-muted small">
                <span class="badge bg-light text-dark me-2">${Util.escape(n.genre_display || n.genre)}</span>
                主角 ${Util.escape(n.main_character_name)} · 计划 ${n.total_chapters_planned} 章 ·
                已生成 ${s.chapters_done}/${n.total_chapters_planned} 章
            </div>
        </div>
        <div class="text-end">
            <button class="btn btn-outline-secondary me-2" onclick="App.go('#/novel/${novelId}/edit')">
                <i class="fas fa-pen-to-square me-1"></i>编辑档案
            </button>
            <button class="btn btn-outline-primary me-2" onclick="App.go('#/novel/${novelId}/chapters')">
                <i class="fas fa-book me-1"></i>章节库
            </button>
            <button class="btn btn-outline-info" onclick="App.go('#/novel/${novelId}/audit')">
                <i class="fas fa-chart-pie me-1"></i>全本审计
                ${auditScore != null ? `<span class="badge bg-info ms-2">${auditScore}</span>` : ""}
            </button>
        </div>
    </div>

    <!-- 5 阶段时间轴：底层背景线 + 节点居中对齐 -->
    <div class="workflow-timeline mb-4">
        <div class="timeline-track"></div>
        <div class="timeline-track-done" id="timelineDone"></div>
        ${stageStep(1, "Init",       "题材+主角骨架",   true,                                        "fas fa-seedling")}
        ${stageStep(2, "Storyline",  "LLM 展开三幕剧",  s.storyline_expanded,                        "fas fa-scroll")}
        ${stageStep(3, "Canon",      "档案一致性校验",  s.canon_report,                              "fas fa-shield-halved",
                    c.ERROR > 0 ? "warn" : (s.canon_report ? "done" : "todo"))}
        ${stageStep(4, "Blueprint",  "蓝图+章节卡",     s.blueprint,                                 "fas fa-sitemap")}
        ${stageStep(5, "Chapters",   "正文批量生成",    s.chapters_done > 0,                         "fas fa-feather-pointed")}
    </div>

    <div class="row g-4">
        <div class="col-lg-7">
            <div class="card shadow-sm mb-4">
                <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-scroll me-2"></i>Storyline 三幕剧骨架</span>
                    <button class="btn btn-sm btn-light" onclick="App.openStorylineEditor()">
                        <i class="fas fa-pen me-1"></i>编辑
                    </button>
                </div>
                <div class="card-body" id="storylinePane"><div class="text-muted small">加载中…</div></div>
            </div>

            <div class="card shadow-sm mb-4">
                <div class="card-header bg-warning text-dark d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-shield-halved me-2"></i>Canon 档案一致性</span>
                    <button class="btn btn-sm btn-dark" onclick="App.runCanon()">
                        <i class="fas fa-rotate me-1"></i>重新校验
                    </button>
                </div>
                <div class="card-body" id="canonPane"><div class="text-muted small">加载中…</div></div>
            </div>

            <div class="card shadow-sm mb-4">
                <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-sitemap me-2"></i>Blueprint 蓝图与章节卡</span>
                    <button class="btn btn-sm btn-light" onclick="App.runBlueprint()">
                        <i class="fas fa-${s.blueprint ? 'rotate' : 'magic'} me-1"></i>${s.blueprint ? '重生成' : '生成蓝图'}
                    </button>
                </div>
                <div class="card-body" id="blueprintPane"><div class="text-muted small">加载中…</div></div>
            </div>

            <div class="card shadow-sm mb-4">
                <div class="card-header bg-primary text-white">
                    <i class="fas fa-feather-pointed me-2"></i>章节生成
                </div>
                <div class="card-body">
                    <div class="row g-2">
                        <div class="col-md-3">
                            <label class="form-label small mb-1">起始章</label>
                            <input class="form-control form-control-sm" type="number" id="genStart" value="${s.chapters_done + 1}" min="1" max="${n.total_chapters_planned}" />
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-1">结束章</label>
                            <input class="form-control form-control-sm" type="number" id="genEnd" value="${Math.min(s.chapters_done + 5, n.total_chapters_planned)}" min="1" max="${n.total_chapters_planned}" />
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small mb-1">目标字数</label>
                            <input class="form-control form-control-sm" type="number" id="genWords" value="2300" min="500" max="6000" step="100" />
                        </div>
                        <div class="col-md-3 d-flex align-items-end">
                            <button class="btn btn-primary btn-sm w-100" onclick="App.startGenerateChapters()" ${!s.blueprint ? "disabled" : ""}>
                                <i class="fas fa-rocket me-1"></i>开始生成
                            </button>
                        </div>
                    </div>
                    <div class="form-text mt-2">
                        生成在后台异步运行，可在右上角"任务"查看实时进度。
                        ${!s.blueprint ? '<span class="text-danger ms-2">需要先生成蓝图</span>' : ""}
                    </div>
                </div>
            </div>
        </div>

        <div class="col-lg-5">
            <div class="card shadow-sm mb-4">
                <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-users me-2"></i>角色档案</span>
                    <button class="btn btn-sm btn-light" onclick="App.openCharsEditor()">
                        <i class="fas fa-pen me-1"></i>编辑
                    </button>
                </div>
                <div class="card-body p-0" id="charsPane"><div class="text-muted small p-3">加载中…</div></div>
            </div>

            <div class="card shadow-sm mb-4">
                <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-list-ol me-2"></i>章节进度</span>
                    <button class="btn btn-sm btn-outline-light" onclick="App.go('#/novel/${novelId}/chapters')">查看全部</button>
                </div>
                <div class="card-body" id="chaptersMiniPane"><div class="text-muted small">加载中…</div></div>
            </div>
        </div>
    </div>`;

    // 计算"已完成"进度，刷新底层 done 横线宽度
    paintTimeline([true, s.storyline_expanded, s.canon_report, s.blueprint, s.chapters_done > 0]);

    Promise.all([
        loadStorylinePane(novelId),
        loadCanonPane(novelId),
        loadBlueprintPane(novelId),
        loadCharsPane(novelId),
        loadChaptersMiniPane(novelId),
    ]);
}

function stageStep(idx, name, sub, done, icon, mode) {
    const m = mode || (done ? "done" : "todo");
    return `
        <div class="stage-step ${m}">
            <div class="stage-circle"><i class="${icon}"></i></div>
            <div class="stage-meta">
                <div class="stage-name">${idx}. ${name}</div>
                <div class="stage-sub">${sub}</div>
            </div>
        </div>`;
}

/** 计算已完成进度的横线宽度（百分比） */
function paintTimeline(states) {
    // states 是 5 个 bool；找到最后一个 true 的位置 idx，进度 = (idx + 0.5) / 5
    const el = document.getElementById("timelineDone");
    if (!el) return;
    let lastDone = -1;
    for (let i = 0; i < states.length; i++) if (states[i]) lastDone = i;
    if (lastDone < 0) { el.style.width = "0%"; return; }
    const total = states.length;
    // 横线从第 0 个节点中心开始，到最后一个完成节点的中心
    // 节点中心位置：(i + 0.5) / total，第 0 个就是 0.5/5=10%
    // 起点：10%，终点：(lastDone + 0.5)/total
    const startPct = 100 / total / 2;
    const endPct = (lastDone + 0.5) * 100 / total;
    el.style.left = `${startPct}%`;
    el.style.width = `${endPct - startPct}%`;
}

async function loadStorylinePane(novelId) {
    try {
        const s = await Util.get(`/novels/${novelId}/storyline`);
        const ov = s.overall_storyline || {};
        if (!ov.main_goal) {
            document.getElementById("storylinePane").innerHTML =
                `<div class="text-muted">storyline 尚未展开骨架。</div>`;
            return;
        }
        const a1 = ov.act1 || {}, a2 = ov.act2 || {}, a3 = ov.act3 || {};
        const themes = (ov.themes || []).map(t => `<span class="badge bg-success-subtle text-success me-1">${Util.escape(t)}</span>`).join("");
        const cf = ov.core_conflict || {};

        document.getElementById("storylinePane").innerHTML = `
            <div class="mb-3">
                <div class="text-muted small mb-1"><i class="fas fa-bullseye me-1"></i>主角终极目标</div>
                <div class="fw-bold">${Util.escape(ov.main_goal)}</div>
            </div>
            ${cf.external || cf.internal ? `
            <div class="mb-3">
                <div class="text-muted small mb-1"><i class="fas fa-bolt me-1"></i>核心冲突</div>
                <ul class="mb-0 small">
                    ${cf.external ? `<li><b>外在</b>：${Util.escape(cf.external)}</li>` : ""}
                    ${cf.internal ? `<li><b>内在</b>：${Util.escape(cf.internal)}</li>` : ""}
                    ${cf.interpersonal ? `<li><b>人际</b>：${Util.escape(cf.interpersonal)}</li>` : ""}
                </ul>
            </div>` : ""}
            ${a1.setup || a2.confrontation || a3.climax ? `
            <div class="acts-grid">
                <div class="act-block act1">
                    <div class="act-label">第一幕 · Setup</div>
                    <div class="act-content">${Util.escape((a1.setup || "").slice(0, 110))}…</div>
                </div>
                <div class="act-block act2">
                    <div class="act-label">第二幕 · 中点</div>
                    <div class="act-content">${Util.escape((a2.midpoint_crisis || a2.confrontation || "").slice(0, 110))}…</div>
                </div>
                <div class="act-block act3">
                    <div class="act-label">第三幕 · Climax</div>
                    <div class="act-content">${Util.escape((a3.climax || "").slice(0, 110))}…</div>
                </div>
            </div>` : ""}
            ${themes ? `<div class="mt-2"><div class="text-muted small mb-1">主题</div>${themes}</div>` : ""}
        `;
    } catch (e) {
        document.getElementById("storylinePane").innerHTML =
            `<div class="text-danger small">${Util.escape(e.message)}</div>`;
    }
}

async function loadCanonPane(novelId) {
    try {
        const r = await Util.get(`/novels/${novelId}/canon`);
        if (!r || !r.summary) {
            document.getElementById("canonPane").innerHTML =
                `<div class="text-muted">尚无校验报告，点击"重新校验"。</div>`;
            return;
        }
        const s = r.summary || {};
        const issues = r.issues || [];
        const sevColor = { ERROR: "danger", WARNING: "warning", INFO: "info" };
        document.getElementById("canonPane").innerHTML = `
            <div class="d-flex gap-3 mb-3 flex-wrap">
                <div class="canon-stat danger">
                    <div class="canon-stat-num">${s.ERROR || 0}</div>
                    <div class="canon-stat-lbl">ERROR</div>
                </div>
                <div class="canon-stat warning">
                    <div class="canon-stat-num">${s.WARNING || 0}</div>
                    <div class="canon-stat-lbl">WARNING</div>
                </div>
                <div class="canon-stat info">
                    <div class="canon-stat-num">${s.INFO || 0}</div>
                    <div class="canon-stat-lbl">INFO</div>
                </div>
                <div class="ms-auto small text-muted align-self-center text-end">
                    主角：${Util.escape(r.registered_main || "—")}<br/>
                    配角：${(r.registered_supporting || []).map(Util.escape).join(", ") || "—"}
                </div>
            </div>
            ${issues.length === 0
                ? `<div class="alert alert-success mb-0 py-2 small">
                       <i class="fas fa-circle-check me-1"></i> 全部规则通过</div>`
                : issues.slice(0, 8).map(i => `
                    <div class="issue-item issue-${(i.severity || "INFO").toLowerCase()}">
                        <div class="d-flex justify-content-between flex-wrap">
                            <span><span class="badge bg-${sevColor[i.severity] || "secondary"} me-2">${Util.escape(i.rule_id)}</span>${Util.escape(i.title)}</span>
                            <span class="text-muted small">${Util.escape(i.subject || "")}</span>
                        </div>
                        <div class="small text-muted mt-1">${Util.escape(i.detail)}</div>
                    </div>
                `).join("")}
            ${issues.length > 8 ? `<div class="text-muted small text-end">…还有 ${issues.length - 8} 条</div>` : ""}
        `;
    } catch (e) {
        document.getElementById("canonPane").innerHTML =
            `<div class="text-danger small">${Util.escape(e.message)}</div>`;
    }
}

async function loadBlueprintPane(novelId) {
    try {
        const bp = await Util.get(`/novels/${novelId}/blueprint`);
        if (!bp || !bp.meta) {
            document.getElementById("blueprintPane").innerHTML =
                `<div class="text-muted">蓝图尚未生成。点击上方"生成蓝图"按钮启动。</div>`;
            return;
        }
        const meta = bp.meta || {};
        const arc = bp.global_arc || {};
        const vols = bp.volumes || arc.volumes || [];
        const ledger = bp.global_foreshadow_ledger || bp.ledger || [];
        document.getElementById("blueprintPane").innerHTML = `
            <div class="row g-3 mb-3">
                <div class="col-sm-6"><div class="text-muted small">主题</div><div>${Util.escape(meta.core_theme || "—")}</div></div>
                <div class="col-sm-6"><div class="text-muted small">基调</div><div>${Util.escape(meta.tone || "—")}</div></div>
            </div>
            <div class="text-muted small mb-1">三幕节奏</div>
            <div class="acts-mini mb-3">
                <span class="act-mini bg-warning-subtle">第一幕 ${(arc.act1_range || []).join("-")}</span>
                <span class="act-mini bg-danger-subtle">第二幕 ${(arc.act2_range || []).join("-")} 中点 第${arc.midpoint_chapter || "?"}章</span>
                <span class="act-mini bg-success-subtle">第三幕 ${(arc.act3_range || []).join("-")}</span>
            </div>
            <div class="text-muted small mb-1">卷划分（${vols.length} 卷，点击展开看每章详情）</div>
            <div class="vol-list mb-3">
                ${vols.map(v => {
                    const idx = v.volume_index || v.index;
                    const isOpen = State.bp.expandedVolume === idx;
                    return `
                    <div class="vol-row vol-clickable ${isOpen ? "expanded" : ""}"
                         onclick="App.toggleVolumeDetail(${idx})">
                        <div class="vol-idx">卷${idx}</div>
                        <div class="flex-grow-1">
                            <div class="vol-title">${Util.escape(v.title || "")}</div>
                            <div class="vol-meta small text-muted">
                                ch ${(v.chapter_range || []).join("-")} · ${Util.escape(v.phase || "")}
                            </div>
                        </div>
                        <i class="fas fa-chevron-${isOpen ? 'up' : 'down'} text-muted ms-2"></i>
                    </div>
                    <div class="vol-detail" id="volDetail-${idx}" style="display:${isOpen ? "block" : "none"}">
                        ${isOpen ? '<div class="text-muted small p-2">加载中…</div>' : ''}
                    </div>`;
                }).join("")}
            </div>
            ${ledger.length ? `
            <div class="text-muted small mb-1">全局伏笔账本（${ledger.length} 条）</div>
            <div class="ledger-list small">
                ${ledger.slice(0, 6).map(f => `
                    <div class="ledger-row">
                        <span class="badge bg-light text-dark me-2">${Util.escape(f.id || "F?")}</span>
                        卷${f.plant_volume || "?"} → 卷${f.payoff_volume || "?"} ·
                        ${Util.escape(((f.keyword || f.title || f.description) || "").slice(0, 40))}
                    </div>`).join("")}
                ${ledger.length > 6 ? `<div class="text-muted text-end">…还有 ${ledger.length - 6} 条</div>` : ""}
            </div>` : ""}
        `;
        // 如果有已展开的卷，立即拉数据
        if (State.bp.expandedVolume != null) {
            loadVolumeDetail(novelId, State.bp.expandedVolume);
        }
    } catch (e) {
        document.getElementById("blueprintPane").innerHTML =
            `<div class="text-danger small">${Util.escape(e.message)}</div>`;
    }
}

async function loadVolumeDetail(novelId, volIdx) {
    const target = document.getElementById(`volDetail-${volIdx}`);
    if (!target) return;
    const cacheKey = novelId + ":" + volIdx;
    let cards = State.bpVolumeCards[cacheKey];
    if (!cards) {
        try {
            const data = await Util.get(`/novels/${novelId}/volumes/${volIdx}/cards`);
            cards = data.chapter_cards || [];
            State.bpVolumeCards[cacheKey] = cards;
        } catch (e) {
            target.innerHTML = `<div class="text-danger small p-2">${Util.escape(e.message)}</div>`;
            return;
        }
    }
    if (!cards || cards.length === 0) {
        target.innerHTML = `<div class="text-muted small p-2">本卷尚未展开章节卡。生成首章时会自动展开。</div>`;
        return;
    }
    target.innerHTML = cards.map(c => renderChapterCard(novelId, c)).join("");
}

function renderChapterCard(novelId, c) {
    const ma = c.must_appear || {};
    const beats = c.beats || c.scene_beats || [];
    const fp = c.foreshadow_plant || c.plant_foreshadow || [];
    const fd = c.foreshadow_payoff || c.payoff_foreshadow || [];
    const tension = c.tension != null ? c.tension : (c.tension_level || 0);
    const tone = c.tone || c.color_tone || "";
    const hook = c.ending_hook || c.hook || "";
    return `
    <div class="ch-card-mini">
        <div class="d-flex align-items-center gap-2 mb-1">
            <span class="badge bg-primary">第${c.chapter_number}章</span>
            <span class="fw-bold flex-grow-1">${Util.escape(c.title || "")}</span>
            ${tension ? `<span class="badge bg-danger-subtle text-danger" title="张力">⚡${tension}</span>` : ""}
            ${tone ? `<span class="badge bg-light text-dark" title="色调">${Util.escape(tone)}</span>` : ""}
            <button class="btn btn-sm btn-outline-secondary" onclick="event.stopPropagation();App.go('#/novel/${novelId}/chapter/${c.chapter_number}')">
                <i class="fas fa-eye"></i>
            </button>
        </div>
        ${c.summary ? `<div class="ch-card-summary text-muted small mb-2">${Util.escape(c.summary)}</div>` : ""}
        ${beats.length ? `
            <div class="ch-card-beats small">
                ${beats.map(b => `<div class="beat-item"><i class="fas fa-circle-dot me-1 text-primary"></i>${Util.escape(typeof b === "string" ? b : (b.event || b))}</div>`).join("")}
            </div>` : ""}
        <div class="d-flex gap-2 flex-wrap mt-2 small text-muted">
            ${(ma.characters || []).map(x => `<span class="ma-pill ma-c">👤 ${Util.escape(x)}</span>`).join("")}
            ${(ma.locations || []).map(x => `<span class="ma-pill ma-l">📍 ${Util.escape(x)}</span>`).join("")}
            ${(ma.objects || []).map(x => `<span class="ma-pill ma-o">📦 ${Util.escape(x)}</span>`).join("")}
        </div>
        ${(fp.length || fd.length) ? `
            <div class="small text-muted mt-2">
                ${fp.length ? `<div><i class="fas fa-seedling text-success me-1"></i>埋伏笔：${fp.map(Util.escape).join("、")}</div>` : ""}
                ${fd.length ? `<div><i class="fas fa-bullseye text-danger me-1"></i>收伏笔：${fd.map(Util.escape).join("、")}</div>` : ""}
            </div>` : ""}
        ${hook ? `<div class="ch-card-hook mt-2 small"><i class="fas fa-quote-left me-1"></i>${Util.escape(hook)}</div>` : ""}
    </div>`;
}

async function loadCharsPane(novelId) {
    try {
        const c = await Util.get(`/novels/${novelId}/characters`);
        const main = c.main_character || {};
        const sup = c.supporting_characters || [];
        document.getElementById("charsPane").innerHTML = `
            <div class="char-row main">
                <div class="char-avatar"><i class="fas fa-crown"></i></div>
                <div class="flex-grow-1">
                    <div class="char-name">${Util.escape((main.basic_info || {}).name || "—")}
                        <span class="char-role">主角</span></div>
                    <div class="char-meta small text-muted">
                        ${Util.escape((main.basic_info || {}).gender || "—")} ·
                        ${Util.escape((main.basic_info || {}).age || "—")} ·
                        ${Util.escape((main.basic_info || {}).occupation || "—")}
                    </div>
                </div>
            </div>
            ${sup.map(s => `
                <div class="char-row">
                    <div class="char-avatar"><i class="fas fa-user"></i></div>
                    <div class="flex-grow-1">
                        <div class="char-name">${Util.escape((s.basic_info || {}).name || "—")}
                            <span class="char-role">${Util.escape(s.role || "配角")}</span></div>
                        <div class="char-meta small text-muted">
                            ${Util.escape((s.basic_info || {}).gender || "—")} ·
                            ${Util.escape((s.basic_info || {}).age || "—")} ·
                            ${Util.escape((s.basic_info || {}).occupation || "—")}
                        </div>
                    </div>
                </div>
            `).join("")}
        `;
    } catch (e) {
        document.getElementById("charsPane").innerHTML =
            `<div class="text-danger small p-3">${Util.escape(e.message)}</div>`;
    }
}

async function loadChaptersMiniPane(novelId) {
    try {
        const list = await Util.get(`/novels/${novelId}/chapters`);
        if (list.length === 0) {
            document.getElementById("chaptersMiniPane").innerHTML =
                `<div class="text-muted small">尚未生成任何章节。</div>`;
            return;
        }
        const recent = list.slice(-6).reverse();
        document.getElementById("chaptersMiniPane").innerHTML = recent.map(c => `
            <a href="javascript:void(0)" class="chapter-mini" onclick="App.go('#/novel/${novelId}/chapter/${c.chapter_number}')">
                <span class="ch-num">第${c.chapter_number}章</span>
                <span class="ch-title">${Util.escape(c.title)}</span>
                <span class="ch-meta">${c.word_count}字 · ${c.passed ? "<i class='fas fa-check text-success'></i>" : "<i class='fas fa-times text-danger'></i>"}</span>
            </a>
        `).join("");
    } catch (e) {
        document.getElementById("chaptersMiniPane").innerHTML =
            `<div class="text-danger small">${Util.escape(e.message)}</div>`;
    }
}

/* ============================================================
 * 视图 3：章节网格
 * ============================================================ */
async function renderChaptersGrid(root, novelId) {
    const n = await Util.get(`/novels/${novelId}`);
    const list = await Util.get(`/novels/${novelId}/chapters`);
    State.currentNovelId = novelId;
    const total = n.total_chapters_planned;
    const map = Object.fromEntries(list.map(c => [c.chapter_number, c]));

    const cells = [];
    for (let i = 1; i <= total; i++) {
        const c = map[i];
        if (c) {
            cells.push(`
                <a href="javascript:void(0)" class="ch-cell done"
                   onclick="App.go('#/novel/${novelId}/chapter/${i}')"
                   title="${Util.escape(c.title)} · ${c.word_count}字">
                    <div class="ch-cell-num">${i}</div>
                    <div class="ch-cell-title">${Util.escape(c.title)}</div>
                    <div class="ch-cell-meta">${c.word_count}字</div>
                </a>`);
        } else {
            cells.push(`
                <div class="ch-cell todo" title="尚未生成">
                    <div class="ch-cell-num">${i}</div>
                    <div class="ch-cell-title text-muted">未生成</div>
                </div>`);
        }
    }

    root.innerHTML = `
        <div class="d-flex align-items-center mb-4 flex-wrap gap-2">
            <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/novel/${novelId}')"><i class="fas fa-arrow-left"></i></button>
            <h3 class="mb-0">${Util.escape(n.title)} · 章节库</h3>
            <span class="ms-2 badge bg-success">${list.length}</span>
            <span class="ms-1 badge bg-light text-dark">/ ${total} 章</span>
        </div>
        <div class="ch-grid">${cells.join("")}</div>`;
}

/* ============================================================
 * 视图 4：单章阅读 + 编辑
 * ============================================================ */
async function renderChapter(root, novelId, n) {
    const ch = await Util.get(`/novels/${novelId}/chapters/${n}`);
    State.currentNovelId = novelId;
    const meta = ch.meta || {};
    const v = meta.validation || {};
    const ma = (v.must_appear || {});

    // 必现项实际命中提取（在正文里 includes）
    const hitTag = (name, body) => body && body.includes(name)
        ? `<span class="ma-hit"><i class="fas fa-check"></i> ${Util.escape(name)}</span>`
        : `<span class="ma-miss"><i class="fas fa-xmark"></i> ${Util.escape(name)}</span>`;

    root.innerHTML = `
        <div class="reader-toolbar d-flex align-items-center mb-3 flex-wrap gap-2">
            <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/novel/${novelId}/chapters')" title="返回章节库">
                <i class="fas fa-arrow-left"></i>
            </button>
            <div class="flex-grow-1">
                <h4 class="mb-1" id="chTitleDisp">${Util.escape(ch.title)}</h4>
                <div class="text-muted small">
                    第 ${ch.chapter_number} 章 · <span id="chWcDisp">${meta.word_count || 0}</span> 字 ·
                    主角出现 ${v.protagonist_count || 0} 次
                    ${v.word_count_ok ? '<span class="badge bg-success ms-2">PASS</span>' : '<span class="badge bg-warning ms-2">字数偏差</span>'}
                    ${v._manually_edited ? '<span class="badge bg-info ms-2">已手动编辑</span>' : ''}
                </div>
            </div>
            <div class="btn-group btn-group-sm" title="字体大小">
                <button class="btn btn-outline-secondary" onclick="App.readerFont(-1)"><i class="fas fa-minus"></i></button>
                <button class="btn btn-outline-secondary" onclick="App.readerFont(0)"><span id="readerFontLabel">${State.reader.fontSize}</span></button>
                <button class="btn btn-outline-secondary" onclick="App.readerFont(1)"><i class="fas fa-plus"></i></button>
            </div>
            <button class="btn btn-sm btn-outline-secondary" onclick="App.toggleFullscreen()" title="全屏阅读 (F)">
                <i class="fas fa-expand" id="fullscreenIcon"></i>
            </button>
            <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-secondary" onclick="App.go('#/novel/${novelId}/chapter/${n-1}')" ${n <= 1 ? "disabled" : ""} title="上一章 ←">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <button class="btn btn-outline-warning" id="chEditBtn" onclick="App.toggleChapterEdit()">
                    <i class="fas fa-pen me-1"></i>编辑
                </button>
                <button class="btn btn-outline-secondary" onclick="App.go('#/novel/${novelId}/chapter/${n+1}')" title="下一章 →">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        </div>

        <div class="row g-4" id="readerLayout">
            <div class="col-lg-8" id="readerMain">
                <div id="chReader">
                    <div class="reader-card" id="readerCard" style="font-size:${State.reader.fontSize}px">${Util.paragraphize(ch.body)}</div>
                    <div class="reader-progress" id="readerProgress"></div>
                </div>
                <div id="chEditor" style="display:none">
                    <div class="card shadow-sm">
                        <div class="card-header bg-warning-subtle">
                            <input class="form-control" id="chEditTitle" value="${Util.escape(ch.title)}" />
                        </div>
                        <div class="card-body">
                            <textarea class="form-control reader-editor" id="chEditBody" rows="22">${Util.escape(ch.body)}</textarea>
                            <div class="d-flex gap-2 mt-3 align-items-center">
                                <button class="btn btn-success" onclick="App.saveChapter(${n})">
                                    <i class="fas fa-save me-1"></i>保存 (Ctrl+S)
                                </button>
                                <button class="btn btn-secondary" onclick="App.toggleChapterEdit()">
                                    <i class="fas fa-times me-1"></i>取消
                                </button>
                                <span class="ms-auto small text-muted">字数 <span id="chEditWc">0</span></span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4" id="readerSide">
                <div class="card shadow-sm mb-3">
                    <div class="card-header bg-light"><i class="fas fa-clipboard-check me-2"></i>必现项命中情况</div>
                    <div class="card-body small">
                        <div class="mb-2"><b>人物</b>：${(ma.characters && ma.characters.expected || []).map(x => hitTag(x, ch.body)).join(" ") || "—"}</div>
                        <div class="mb-2"><b>场景</b>：${(ma.locations && ma.locations.expected || []).map(x => hitTag(x, ch.body)).join(" ") || "—"}</div>
                        <div class="mb-2"><b>物件</b>：${(ma.objects && ma.objects.expected || []).map(x => hitTag(x, ch.body)).join(" ") || "—"}</div>
                        <hr/>
                        <div>字数：${meta.word_count} / 目标 ${v.word_count_target || "—"}</div>
                        <div>主角次数：${v.protagonist_count || 0}</div>
                    </div>
                </div>
                <div class="text-muted small text-center">
                    💡 快捷键：<kbd>←</kbd>/<kbd>→</kbd> 翻页 ·
                    <kbd>F</kbd> 全屏 · <kbd>E</kbd> 编辑 · <kbd>Ctrl+S</kbd> 保存
                </div>
            </div>
        </div>`;

    // 应用全屏状态
    if (State.reader.fullscreen) document.body.classList.add("reader-fullscreen");
    else document.body.classList.remove("reader-fullscreen");

    // 编辑模式下实时统计字数
    const ta = document.getElementById("chEditBody");
    if (ta) {
        const updateWc = () => {
            const el = document.getElementById("chEditWc");
            if (el) el.textContent = (ta.value || "").replace(/\s+/g, "").length;
        };
        ta.addEventListener("input", updateWc);
        updateWc();
    }

    // 阅读位置记忆 + 让快捷键能立刻生效（清空遗留焦点 → 让 main 区聚焦）
    setTimeout(() => {
        const key = `inkai_scroll_${novelId}_${n}`;
        const saved = parseInt(localStorage.getItem(key) || "0");
        if (saved > 0) {
            window.scrollTo({ top: saved, behavior: "instant" });
        }
        const onScroll = () => {
            localStorage.setItem(key, String(window.scrollY));
            const card = document.getElementById("readerCard");
            const prog = document.getElementById("readerProgress");
            if (card && prog) {
                const total = document.body.scrollHeight - window.innerHeight;
                const pct = total > 0 ? Math.min(100, Math.max(0, window.scrollY / total * 100)) : 0;
                prog.style.width = pct + "%";
            }
        };
        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
        State._onScroll = onScroll;

        // 关键：把焦点从遗留的 navbar 链接 / "进入" 按钮上挪走
        // 否则方向键会被浏览器用作 "Tab between focusable" 而吞掉
        try { document.activeElement && document.activeElement.blur && document.activeElement.blur(); } catch (_) {}
        const main = document.getElementById("readerMain");
        if (main) { main.setAttribute("tabindex", "-1"); main.focus({ preventScroll: true }); }
    }, 50);
}

/* ============================================================
 * 视图 5：全本审计
 * ============================================================ */
async function renderAudit(root, novelId) {
    const n = await Util.get(`/novels/${novelId}`);
    State.currentNovelId = novelId;
    let rpt = await Util.get(`/novels/${novelId}/audit`);
    if (!rpt || !rpt.dimension_scores) {
        root.innerHTML = `
            <div class="d-flex align-items-center mb-4 flex-wrap gap-2">
                <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/novel/${novelId}')"><i class="fas fa-arrow-left"></i></button>
                <h3 class="mb-0">${Util.escape(n.title)} · 全本审计</h3>
            </div>
            <div class="empty-state text-center py-5">
                <i class="fas fa-chart-pie fa-3x text-muted mb-3"></i>
                <h5 class="text-muted mb-3">尚无审计报告</h5>
                <button class="btn btn-info" onclick="App.runAudit()">
                    <i class="fas fa-play me-2"></i>立即跑一次审计
                </button>
            </div>`;
        return;
    }

    const dims = rpt.dimension_scores || {};
    const labels = Object.keys(dims).map(k => k.replace(/^M\d+_/, ""));
    const data = Object.values(dims);
    const findings = rpt.findings || [];
    const sevColor = { ERROR: "danger", WARNING: "warning", INFO: "info" };

    root.innerHTML = `
        <div class="d-flex align-items-center mb-4 flex-wrap gap-2">
            <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/novel/${novelId}')"><i class="fas fa-arrow-left"></i></button>
            <div class="flex-grow-1">
                <h3 class="mb-1">${Util.escape(n.title)} · 全本审计</h3>
                <div class="text-muted small">综合得分 <b class="audit-score-big">${rpt.overall_score}</b> / 100 ·
                    覆盖 ${rpt.chapters_loaded}/${rpt.chapters_total} 章</div>
            </div>
            <button class="btn btn-info" onclick="App.runAudit()"><i class="fas fa-rotate me-1"></i>重新审计</button>
        </div>
        <div class="row g-4">
            <div class="col-lg-6">
                <div class="card shadow-sm">
                    <div class="card-header bg-info text-white"><i class="fas fa-chart-pie me-2"></i>六维雷达</div>
                    <div class="card-body"><canvas id="auditRadar" height="320"></canvas></div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="card shadow-sm">
                    <div class="card-header bg-secondary text-white">
                        <i class="fas fa-list-check me-2"></i>问题清单（${findings.length} 条）
                    </div>
                    <div class="card-body" style="max-height: 480px; overflow-y: auto;">
                        ${findings.length === 0 ? `<div class="alert alert-success mb-0 py-2 small">
                            <i class="fas fa-circle-check me-1"></i>未发现问题</div>` : ""}
                        ${findings.map(f => `
                            <div class="issue-item issue-${(f.severity || "INFO").toLowerCase()}">
                                <div><span class="badge bg-${sevColor[f.severity] || "secondary"} me-2">${Util.escape(f.code)}</span>${Util.escape(f.title)}</div>
                                <div class="small text-muted mt-1">${Util.escape(f.detail)}</div>
                                ${(f.evidence || []).slice(0, 3).map(e => `
                                    <div class="small text-muted ms-3"><i class="fas fa-arrow-right me-1"></i>${Util.escape(e)}</div>
                                `).join("")}
                            </div>
                        `).join("")}
                    </div>
                </div>
            </div>
        </div>`;

    setTimeout(() => {
        const ctx = document.getElementById("auditRadar");
        if (!ctx || typeof Chart === "undefined") return;
        State.chartInstances.audit = new Chart(ctx, {
            type: "radar",
            data: {
                labels,
                datasets: [{
                    label: "本次得分", data, fill: true,
                    backgroundColor: "rgba(13, 202, 240, 0.18)",
                    borderColor: "rgba(13, 110, 253, 0.85)",
                    pointBackgroundColor: "rgba(13, 110, 253, 1)",
                    pointRadius: 4,
                }],
            },
            options: {
                scales: { r: { min: 0, max: 100, ticks: { stepSize: 20 } } },
                plugins: { legend: { display: false } },
            },
        });
    }, 50);
}

/* ============================================================
 * 视图 6：编辑档案大页（characters / storyline 大表单）
 * ============================================================ */
async function renderEdit(root, novelId) {
    const [n, chars, story] = await Promise.all([
        Util.get(`/novels/${novelId}`),
        Util.get(`/novels/${novelId}/characters`),
        Util.get(`/novels/${novelId}/storyline`),
    ]);
    State.currentNovelId = novelId;

    const main = chars.main_character || {};
    const sup = chars.supporting_characters || [];
    const ov = story.overall_storyline || {};
    const a1 = ov.act1 || {}, a2 = ov.act2 || {}, a3 = ov.act3 || {};
    const cf = ov.core_conflict || {};

    root.innerHTML = `
        <div class="d-flex align-items-center mb-4 flex-wrap gap-2">
            <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/novel/${novelId}')"><i class="fas fa-arrow-left"></i></button>
            <h3 class="mb-0">${Util.escape(n.title)} · 编辑档案</h3>
        </div>

        <ul class="nav nav-tabs mb-3" role="tablist">
            <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-meta">基本信息</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-chars">角色档案</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-story">Storyline</button></li>
        </ul>
        <div class="tab-content">
            <!-- 基本信息 -->
            <div class="tab-pane fade show active" id="tab-meta">
                <div class="card shadow-sm">
                    <div class="card-body">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="form-label">小说标题</label>
                                <input class="form-control" id="metaTitle" value="${Util.escape(n.title)}" />
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">主角姓名</label>
                                <input class="form-control" id="metaProtag" value="${Util.escape(n.main_character_name)}" />
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">总章数</label>
                                <input type="number" class="form-control" id="metaTotal" value="${n.total_chapters_planned}" min="5" max="200" />
                            </div>
                            <div class="col-12">
                                <label class="form-label">附加创作要求</label>
                                <textarea class="form-control" id="metaExtra" rows="4">${Util.escape((await Util.get(`/novels/${novelId}/metadata`)).user_requirements || "")}</textarea>
                            </div>
                        </div>
                        <div class="mt-3 d-flex gap-2">
                            <button class="btn btn-primary" onclick="App.saveMetaTab()"><i class="fas fa-save me-1"></i>保存基本信息</button>
                            <span class="text-muted small align-self-center">注意：标题/主角名也会同步影响内部展示，但不会重写已生成内容</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 角色档案 -->
            <div class="tab-pane fade" id="tab-chars">
                <div id="charsForm"></div>
            </div>

            <!-- Storyline -->
            <div class="tab-pane fade" id="tab-story">
                <div class="card shadow-sm">
                    <div class="card-body">
                        <div class="mb-3">
                            <label class="form-label">主角终极目标</label>
                            <textarea class="form-control" id="stMainGoal" rows="2">${Util.escape(ov.main_goal || "")}</textarea>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-4">
                                <label class="form-label">外在冲突</label>
                                <textarea class="form-control" id="stExt" rows="3">${Util.escape(cf.external || "")}</textarea>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">内在冲突</label>
                                <textarea class="form-control" id="stInt" rows="3">${Util.escape(cf.internal || "")}</textarea>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">人际冲突</label>
                                <textarea class="form-control" id="stIntp" rows="3">${Util.escape(cf.interpersonal || "")}</textarea>
                            </div>
                        </div>
                        <div class="row g-3 mb-3">
                            <div class="col-md-4">
                                <label class="form-label">第一幕 · Setup</label>
                                <textarea class="form-control" id="stAct1" rows="6">${Util.escape(a1.setup || "")}</textarea>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">第二幕 · 中点危机</label>
                                <textarea class="form-control" id="stAct2" rows="6">${Util.escape(a2.midpoint_crisis || a2.confrontation || "")}</textarea>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">第三幕 · Climax</label>
                                <textarea class="form-control" id="stAct3" rows="6">${Util.escape(a3.climax || "")}</textarea>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">主题（每行一个）</label>
                            <textarea class="form-control" id="stThemes" rows="3">${Util.escape((ov.themes || []).join("\n"))}</textarea>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-primary" onclick="App.saveStorylineTab()"><i class="fas fa-save me-1"></i>保存 Storyline</button>
                            <span class="text-warning small align-self-center">
                                <i class="fas fa-triangle-exclamation me-1"></i>修改后建议重新跑一次 Canon 校验
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;

    renderCharsForm(main, sup);
}

function renderCharsForm(main, sup) {
    const mb = main.basic_info || {};
    const supRows = sup.map((s, i) => charSupRow(s, i)).join("");
    document.getElementById("charsForm").innerHTML = `
        <div class="card shadow-sm mb-3">
            <div class="card-header bg-warning"><i class="fas fa-crown me-2"></i>主角</div>
            <div class="card-body">
                <div class="row g-2">
                    <div class="col-md-3"><label class="form-label small">姓名</label>
                        <input class="form-control form-control-sm" data-mfield="name" value="${Util.escape(mb.name || "")}" /></div>
                    <div class="col-md-2"><label class="form-label small">性别</label>
                        <select class="form-select form-select-sm" data-mfield="gender">
                            <option value="男" ${mb.gender === "男" ? "selected" : ""}>男</option>
                            <option value="女" ${mb.gender === "女" ? "selected" : ""}>女</option>
                            <option value="未知" ${!mb.gender || (mb.gender !== "男" && mb.gender !== "女") ? "selected" : ""}>未知</option>
                        </select></div>
                    <div class="col-md-2"><label class="form-label small">年龄</label>
                        <input class="form-control form-control-sm" type="number" data-mfield="age" value="${mb.age || ""}" /></div>
                    <div class="col-md-5"><label class="form-label small">职业</label>
                        <input class="form-control form-control-sm" data-mfield="occupation" value="${Util.escape(mb.occupation || "")}" /></div>
                </div>
            </div>
        </div>
        <div class="card shadow-sm mb-3">
            <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
                <span><i class="fas fa-user-group me-2"></i>配角</span>
                <button class="btn btn-sm btn-light" onclick="App.addSupChar()">
                    <i class="fas fa-plus me-1"></i>新增配角
                </button>
            </div>
            <div class="card-body" id="supList">${supRows || `<div class="text-muted small">暂无配角</div>`}</div>
        </div>
        <button class="btn btn-primary" onclick="App.saveCharsTab()"><i class="fas fa-save me-1"></i>保存角色档案</button>
        <span class="text-warning small ms-2">
            <i class="fas fa-triangle-exclamation me-1"></i>修改后建议重新跑一次 Canon 校验
        </span>`;
}

function charSupRow(s, i) {
    const b = s.basic_info || {};
    return `
    <div class="sup-row mb-3 p-3 rounded" data-sup-idx="${i}">
        <div class="d-flex justify-content-between align-items-center mb-2">
            <span class="badge bg-light text-dark">配角 #${i + 1}</span>
            <button class="btn btn-sm btn-outline-danger" onclick="App.removeSupChar(${i})">
                <i class="fas fa-trash"></i> 删除
            </button>
        </div>
        <div class="row g-2">
            <div class="col-md-3"><label class="form-label small">姓名</label>
                <input class="form-control form-control-sm" data-sfield="name" value="${Util.escape(b.name || "")}" /></div>
            <div class="col-md-2"><label class="form-label small">性别</label>
                <select class="form-select form-select-sm" data-sfield="gender">
                    <option value="男" ${b.gender === "男" ? "selected" : ""}>男</option>
                    <option value="女" ${b.gender === "女" ? "selected" : ""}>女</option>
                    <option value="未知" ${!b.gender || (b.gender !== "男" && b.gender !== "女") ? "selected" : ""}>未知</option>
                </select></div>
            <div class="col-md-2"><label class="form-label small">年龄</label>
                <input class="form-control form-control-sm" type="number" data-sfield="age" value="${b.age || ""}" /></div>
            <div class="col-md-5"><label class="form-label small">角色定位</label>
                <input class="form-control form-control-sm" data-srole value="${Util.escape(s.role || "")}" placeholder="如：助手 / 反派 / 受害者" /></div>
            <div class="col-md-12"><label class="form-label small">职业</label>
                <input class="form-control form-control-sm" data-sfield="occupation" value="${Util.escape(b.occupation || "")}" /></div>
            <div class="col-md-12"><label class="form-label small">背景</label>
                <textarea class="form-control form-control-sm" data-sfield="background" rows="2">${Util.escape(b.background || "")}</textarea></div>
            <div class="col-md-12"><label class="form-label small">性格</label>
                <textarea class="form-control form-control-sm" data-spersonality rows="2">${Util.escape(typeof s.personality === "string" ? s.personality : JSON.stringify(s.personality || ""))}</textarea></div>
            <div class="col-md-12"><label class="form-label small">与主角的关系</label>
                <textarea class="form-control form-control-sm" data-srel rows="2">${Util.escape(s.relationship_with_main || "")}</textarea></div>
        </div>
    </div>`;
}

/* ============================================================
 * 视图 7：题材库主页 + 题材编辑大页
 * ============================================================ */
async function renderGenresHome(root) {
    State.currentNovelId = null;
    const genres = await Util.get("/genres");
    State.genres = genres;
    root.innerHTML = `
        <div class="d-flex align-items-center mb-4 flex-wrap gap-2">
            <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/')"><i class="fas fa-arrow-left"></i></button>
            <h3 class="mb-0"><i class="fas fa-palette text-primary me-2"></i>题材库</h3>
            <span class="badge bg-light text-dark ms-2">${genres.length} 个</span>
            <div class="ms-auto d-flex gap-2">
                <button class="btn btn-info" onclick="App.openGenerateGenreModal()">
                    <i class="fas fa-wand-magic-sparkles me-1"></i>LLM 一键造题材
                </button>
                <button class="btn btn-primary" onclick="App.go('#/genres/new')">
                    <i class="fas fa-plus me-1"></i>手动新建
                </button>
            </div>
        </div>
        <div class="row g-4">
            ${genres.map(genreCard).join("") || `
                <div class="col-12 text-center py-5 text-muted">
                    <i class="fas fa-palette fa-3x mb-2"></i>
                    <div>题材库为空，点击右上角新建</div>
                </div>`}
        </div>`;
}

function genreCard(g) {
    const tags = g.default_tags || {};
    const tagPreview = Object.values(tags).flat().slice(0, 4)
        .map(t => `<span class="badge bg-light text-dark me-1">${Util.escape(t)}</span>`).join("");
    return `
    <div class="col-md-6 col-xl-4">
        <div class="card genre-card h-100 shadow-sm" onclick="App.go('#/genres/${encodeURIComponent(g.name)}')">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="card-title mb-0"><i class="fas fa-bookmark text-primary me-2"></i>${Util.escape(g.display_name || g.name)}</h5>
                    <code class="text-muted small">${Util.escape(g.name)}</code>
                </div>
                <div class="text-muted small mb-3">${Util.escape(g.one_liner || "—")}</div>
                <div>${tagPreview || '<span class="text-muted small">无标签</span>'}</div>
            </div>
            <div class="card-footer bg-light d-flex justify-content-end gap-2" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-outline-primary" onclick="App.go('#/genres/${encodeURIComponent(g.name)}')">
                    <i class="fas fa-pen-to-square me-1"></i>编辑
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="App.deleteGenre('${g.name}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    </div>`;
}

/** 题材编辑大页：name=null 表示新建。 */
async function renderGenreEdit(root, name, presetData = null) {
    let g;
    let isNew = false;
    if (name) {
        g = await Util.get(`/genres/${encodeURIComponent(name)}`);
    } else {
        isNew = true;
        g = presetData || {
            name: "",
            display_name: "",
            one_liner: "",
            style_guide: "",
            allowed_elements: [],
            forbidden_elements: [],
            banned_phrases: [],
            default_tags: { "类型标签": [], "主题标签": [], "风格标签": [], "受众标签": [] },
            default_world_setting: { era: "", world_archetype: "", power_system: "", tech_baseline: "", key_locations: [] },
            default_themes: [],
            spec_template: {
                user_requirements_template: "",
                protagonist_skeleton: { basic_info: {}, personality: { traits: [] } },
                supporting_skeletons: [],
            },
        };
    }
    // 缓存当前编辑对象，方便保存时拿
    State._editingGenre = g;
    State._editingGenreIsNew = isNew;

    const ws = g.default_world_setting || {};
    const tags = g.default_tags || {};
    const st = g.spec_template || {};
    const proto = (st.protagonist_skeleton || {}).basic_info || {};
    const protoPers = (st.protagonist_skeleton || {}).personality || {};

    root.innerHTML = `
        <div class="d-flex align-items-center mb-4 flex-wrap gap-2">
            <button class="btn btn-sm btn-outline-secondary" onclick="App.go('#/genres')"><i class="fas fa-arrow-left"></i></button>
            <h3 class="mb-0">
                ${isNew ? '<i class="fas fa-plus-circle text-primary me-2"></i>新建题材' : '<i class="fas fa-pen-to-square text-primary me-2"></i>编辑题材'}
            </h3>
            ${!isNew ? `<code class="ms-2 text-muted">${Util.escape(g.name)}</code>` : ""}
            <div class="ms-auto">
                <button class="btn btn-success" onclick="App.saveGenre()">
                    <i class="fas fa-save me-1"></i>${isNew ? "保存为新题材" : "保存修改"}
                </button>
            </div>
        </div>

        <ul class="nav nav-tabs mb-3" role="tablist">
            <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#g-basic">基本信息</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#g-rules">风格与禁忌</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#g-world">世界观与标签</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#g-template">主角骨架</button></li>
            <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#g-raw">原始 JSON</button></li>
        </ul>
        <div class="tab-content">

            <!-- 基本信息 -->
            <div class="tab-pane fade show active" id="g-basic">
                <div class="card shadow-sm"><div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label class="form-label">英文 name <span class="text-danger">*</span></label>
                            <input class="form-control" id="gName" value="${Util.escape(g.name || "")}" ${isNew ? "" : "disabled"}
                                   placeholder="如 wuxia / cyberpunk" />
                            <div class="form-text">仅小写字母 / 数字 / 下划线，2-32 字符。${isNew ? "" : '已存在题材的 name 不可改'}</div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">中文显示名</label>
                            <input class="form-control" id="gDisplay" value="${Util.escape(g.display_name || "")}" placeholder="如 古典武侠" />
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">一句话简介</label>
                            <input class="form-control" id="gOne" value="${Util.escape(g.one_liner || "")}" placeholder="≤40 字" />
                        </div>
                    </div>
                </div></div>
            </div>

            <!-- 风格与禁忌 -->
            <div class="tab-pane fade" id="g-rules">
                <div class="card shadow-sm"><div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">风格 / 语感指引（style_guide）</label>
                        <textarea class="form-control" id="gStyle" rows="4">${Util.escape(g.style_guide || "")}</textarea>
                        <div class="form-text">告诉写手该用什么腔调、节奏、意象密度、情绪温度</div>
                    </div>
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label class="form-label">允许出现的元素（每行一个）</label>
                            <textarea class="form-control" id="gAllowed" rows="6">${Util.escape((g.allowed_elements || []).join("\n"))}</textarea>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">题材禁忌（每行一个）</label>
                            <textarea class="form-control" id="gForbidden" rows="6">${Util.escape((g.forbidden_elements || []).join("\n"))}</textarea>
                            <div class="form-text">如：现代科技、超能力</div>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">题材级禁词（每行一个）</label>
                            <textarea class="form-control" id="gBanned" rows="6">${Util.escape((g.banned_phrases || []).join("\n"))}</textarea>
                            <div class="form-text">写正文时绝对不能出现的词，会触发自动校验</div>
                        </div>
                    </div>
                </div></div>
            </div>

            <!-- 世界观 + 标签 -->
            <div class="tab-pane fade" id="g-world">
                <div class="card shadow-sm mb-3"><div class="card-body">
                    <h6 class="mb-3"><i class="fas fa-globe me-2"></i>默认世界观（default_world_setting）</h6>
                    <div class="row g-3">
                        <div class="col-md-3"><label class="form-label">时代</label>
                            <input class="form-control" id="gWsEra" value="${Util.escape(ws.era || "")}" /></div>
                        <div class="col-md-3"><label class="form-label">世界形态</label>
                            <input class="form-control" id="gWsArch" value="${Util.escape(ws.world_archetype || "")}" /></div>
                        <div class="col-md-3"><label class="form-label">力量体系</label>
                            <input class="form-control" id="gWsPower" value="${Util.escape(ws.power_system || "")}" /></div>
                        <div class="col-md-3"><label class="form-label">科技水平</label>
                            <input class="form-control" id="gWsTech" value="${Util.escape(ws.tech_baseline || "")}" /></div>
                        <div class="col-12"><label class="form-label">关键地点（每行一个）</label>
                            <textarea class="form-control" id="gWsLoc" rows="3">${Util.escape((ws.key_locations || []).join("\n"))}</textarea></div>
                    </div>
                </div></div>
                <div class="card shadow-sm mb-3"><div class="card-body">
                    <h6 class="mb-3"><i class="fas fa-tags me-2"></i>默认标签（default_tags）</h6>
                    <div class="row g-3">
                        ${["类型标签", "主题标签", "风格标签", "受众标签"].map(cat => `
                            <div class="col-md-6"><label class="form-label">${cat}（逗号分隔）</label>
                                <input class="form-control" data-gtag="${cat}" value="${Util.escape((tags[cat] || []).join(", "))}" /></div>
                        `).join("")}
                    </div>
                </div></div>
                <div class="card shadow-sm"><div class="card-body">
                    <h6 class="mb-3"><i class="fas fa-bullseye me-2"></i>默认主题（default_themes，每行一个）</h6>
                    <textarea class="form-control" id="gThemes" rows="3">${Util.escape((g.default_themes || []).join("\n"))}</textarea>
                </div></div>
            </div>

            <!-- 主角骨架 -->
            <div class="tab-pane fade" id="g-template">
                <div class="card shadow-sm mb-3"><div class="card-body">
                    <h6 class="mb-3"><i class="fas fa-user-pen me-2"></i>spec_template 用户需求模板</h6>
                    <textarea class="form-control" id="gUrTpl" rows="4">${Util.escape(st.user_requirements_template || "")}</textarea>
                    <div class="form-text">可用占位符 <code>{title}</code> / <code>{protagonist_name}</code> / <code>{total_chapters}</code></div>
                </div></div>
                <div class="card shadow-sm"><div class="card-body">
                    <h6 class="mb-3"><i class="fas fa-crown me-2"></i>主角骨架</h6>
                    <div class="row g-3">
                        <div class="col-md-2"><label class="form-label small">年龄</label>
                            <input type="number" class="form-control form-control-sm" id="gProtoAge" value="${proto.age || ""}" /></div>
                        <div class="col-md-2"><label class="form-label small">性别</label>
                            <select class="form-select form-select-sm" id="gProtoGender">
                                <option value="男" ${proto.gender === "男" ? "selected" : ""}>男</option>
                                <option value="女" ${proto.gender === "女" ? "selected" : ""}>女</option>
                            </select></div>
                        <div class="col-md-8"><label class="form-label small">职业 / 身份</label>
                            <input class="form-control form-control-sm" id="gProtoOcc" value="${Util.escape(proto.occupation || "")}" /></div>
                        <div class="col-12"><label class="form-label small">通用出身设定</label>
                            <textarea class="form-control form-control-sm" id="gProtoBg" rows="2">${Util.escape(proto.background || "")}</textarea></div>
                        <div class="col-md-6"><label class="form-label small">性格关键词（逗号分隔）</label>
                            <input class="form-control form-control-sm" id="gProtoTraits" value="${Util.escape((protoPers.traits || []).join(", "))}" /></div>
                        <div class="col-md-6"><label class="form-label small">弱点（逗号分隔）</label>
                            <input class="form-control form-control-sm" id="gProtoWeak" value="${Util.escape((protoPers.weakness || []).join(", "))}" /></div>
                    </div>
                </div></div>
            </div>

            <!-- 原始 JSON -->
            <div class="tab-pane fade" id="g-raw">
                <div class="card shadow-sm"><div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="text-muted small">直接编辑 JSON（保存时会校验结构）</span>
                        <button class="btn btn-sm btn-outline-secondary" onclick="App.refreshGenreRaw()">
                            <i class="fas fa-rotate me-1"></i>从上方表单同步
                        </button>
                    </div>
                    <textarea class="form-control reader-editor" id="gRawJson" rows="22">${Util.escape(JSON.stringify(g, null, 2))}</textarea>
                </div></div>
            </div>
        </div>`;
}

/* ============================================================
 * App 操作
 * ============================================================ */
const App = {
    /* 统一跳转入口：先改 hash，再强制 route() */
    go(hash) {
        if (location.hash === hash) {
            // 同 hash 不会触发 hashchange，手动调
            route();
        } else {
            location.hash = hash;
        }
    },

    /* ----------- 创建小说 ----------- */
    async openCreateModal() {
        if (State.genres.length === 0) {
            try { State.genres = await Util.get("/genres"); } catch (_) {}
        }
        document.getElementById("genrePicker").innerHTML = State.genres.map(g => `
            <div class="col-md-4">
                <div class="genre-pick" data-name="${g.name}" onclick="App.pickGenre('${g.name}')">
                    <div class="genre-pick-name">${Util.escape(g.display_name)}</div>
                    <div class="genre-pick-desc">${Util.escape(g.one_liner || "")}</div>
                </div>
            </div>`).join("");
        const m = bootstrap.Modal.getOrCreateInstance(document.getElementById("createModal"));
        m.show();
    },
    pickGenre(name) {
        document.querySelectorAll(".genre-pick").forEach(el => el.classList.remove("active"));
        const el = document.querySelector(`.genre-pick[data-name="${name}"]`);
        if (el) el.classList.add("active");
    },
    async submitCreate() {
        const sel = document.querySelector(".genre-pick.active");
        if (!sel) return Util.toast("请选择一个题材包", "warn");
        const payload = {
            genre: sel.dataset.name,
            title: document.getElementById("newTitle").value.trim(),
            protagonist: document.getElementById("newProtagonist").value.trim(),
            total_chapters: parseInt(document.getElementById("newTotal").value || "30"),
            also_storyline: document.getElementById("newAlsoStoryline").checked,
            extra: document.getElementById("newExtra").value.trim(),
        };
        if (!payload.title || !payload.protagonist) return Util.toast("标题与主角必填", "warn");
        try {
            Util.showLoading("创建中…");
            const r = await Util.post("/novels", payload);
            bootstrap.Modal.getInstance(document.getElementById("createModal")).hide();
            Util.toast("已开始创建，正在后台跑 LLM…", "success");
            App.startPolling(r.task_id, () => {
                Util.toast(`小说《${payload.title}》创建完成`, "success");
                if (r.novel_id) App.go(`#/novel/${r.novel_id}`);
                else App.go("#/");
            });
        } catch (e) { Util.toast(e.message, "error", 6000); }
        finally { Util.hideLoading(); }
    },

    async deleteNovel(id) {
        if (!confirm("确定删除这本小说？所有数据将被永久移除。")) return;
        try {
            await Util.del(`/novels/${id}`);
            Util.toast("已删除", "success");
            App.go("#/");
        } catch (e) { Util.toast(e.message, "error"); }
    },

    /* ----------- 单本工作流上的操作 ----------- */
    async runCanon() {
        if (!State.currentNovelId) return;
        try {
            Util.showLoading("校验中…");
            await Util.post(`/novels/${State.currentNovelId}/canon`);
            Util.toast("校验完成", "success");
            await loadCanonPane(State.currentNovelId);
        } catch (e) { Util.toast(e.message, "error"); }
        finally { Util.hideLoading(); }
    },
    async runBlueprint() {
        if (!State.currentNovelId) return;
        if (State.currentNovel && State.currentNovel.stage && State.currentNovel.stage.blueprint) {
            if (!confirm("当前已有蓝图，重新生成会覆盖现有 blueprint.json，确定？")) return;
        }
        try {
            const r = await Util.post(`/novels/${State.currentNovelId}/blueprint`);
            Util.toast("蓝图生成已启动…", "success");
            App.startPolling(r.task_id, async () => {
                Util.toast("蓝图生成完成", "success");
                App.go(`#/novel/${State.currentNovelId}`);
            });
        } catch (e) { Util.toast(e.message, "error"); }
    },
    async startGenerateChapters() {
        if (!State.currentNovelId) return;
        const start = parseInt(document.getElementById("genStart").value);
        const end   = parseInt(document.getElementById("genEnd").value);
        const words = parseInt(document.getElementById("genWords").value);
        if (!(start >= 1 && end >= start && words >= 500)) return Util.toast("参数不合法", "warn");
        if (end - start + 1 > 10 && !confirm(`将一次生成 ${end - start + 1} 章，预计耗时较长，继续？`)) return;
        try {
            const r = await Util.post(`/novels/${State.currentNovelId}/chapters/generate`, {
                start, end, target_words: words, no_dynamic_state: false,
            });
            Util.toast(`已启动生成（共 ${end - start + 1} 章），可在右上角"任务"查看进度`, "success", 6000);
            App.startPolling(r.task_id, async () => {
                Util.toast("批量生成完成", "success");
                App.go(`#/novel/${State.currentNovelId}`);
            });
        } catch (e) { Util.toast(e.message, "error"); }
    },
    async runAudit() {
        const id = State.currentNovelId || parseHash().novelId;
        if (!id) return;
        try {
            Util.showLoading("审计中…");
            await Util.post(`/novels/${id}/audit`);
            Util.toast("审计完成", "success");
            App.go(`#/novel/${id}/audit`);
        } catch (e) { Util.toast(e.message, "error"); }
        finally { Util.hideLoading(); }
    },

    /* ----------- 编辑入口（快捷弹框 → 跳到编辑大页） ----------- */
    openMetaEditor()      { if (State.currentNovelId) App.go(`#/novel/${State.currentNovelId}/edit`); },
    openCharsEditor()     { if (State.currentNovelId) App.go(`#/novel/${State.currentNovelId}/edit`); },
    openStorylineEditor() { if (State.currentNovelId) App.go(`#/novel/${State.currentNovelId}/edit`); },

    /* ----------- 编辑大页保存 ----------- */
    async saveMetaTab() {
        const id = State.currentNovelId; if (!id) return;
        const payload = {
            title: document.getElementById("metaTitle").value.trim(),
            main_character_name: document.getElementById("metaProtag").value.trim(),
            total_chapters_planned: parseInt(document.getElementById("metaTotal").value || "30"),
            user_requirements: document.getElementById("metaExtra").value,
        };
        if (!payload.title) return Util.toast("标题不能为空", "warn");
        try {
            Util.showLoading("保存中…");
            await Util.put(`/novels/${id}/metadata`, payload);
            Util.toast("已保存基本信息", "success");
            Util.flash("#tab-meta .card");
        } catch (e) { Util.toast(e.message, "error"); }
        finally { Util.hideLoading(); }
    },

    addSupChar() {
        const list = document.getElementById("supList");
        const idx = list.querySelectorAll(".sup-row").length;
        if (list.querySelector(".text-muted")) list.innerHTML = "";
        list.insertAdjacentHTML("beforeend", charSupRow({ basic_info: {} }, idx));
    },
    removeSupChar(idx) {
        const row = document.querySelector(`.sup-row[data-sup-idx="${idx}"]`);
        if (row) row.remove();
    },
    async saveCharsTab() {
        const id = State.currentNovelId; if (!id) return;
        // 收集主角
        const main = { basic_info: {} };
        document.querySelectorAll("[data-mfield]").forEach(el => {
            main.basic_info[el.dataset.mfield] = el.value;
        });
        // 收集配角
        const sup = [];
        document.querySelectorAll(".sup-row").forEach(row => {
            const s = { basic_info: {} };
            row.querySelectorAll("[data-sfield]").forEach(el => { s.basic_info[el.dataset.sfield] = el.value; });
            const role = row.querySelector("[data-srole]"); if (role) s.role = role.value;
            const per  = row.querySelector("[data-spersonality]"); if (per && per.value) s.personality = per.value;
            const rel  = row.querySelector("[data-srel]"); if (rel && rel.value) s.relationship_with_main = rel.value;
            if ((s.basic_info.name || "").trim()) sup.push(s);
        });
        try {
            Util.showLoading("保存中…");
            await Util.put(`/novels/${id}/characters`, { main_character: main, supporting_characters: sup });
            // 同步 main_character_name 到 metadata
            if (main.basic_info.name) {
                const supNames = sup.map(s => s.basic_info.name).filter(Boolean);
                await Util.put(`/novels/${id}/metadata`, {
                    main_character_name: main.basic_info.name,
                    supporting_character_names: supNames,
                });
            }
            Util.toast("已保存角色档案，建议重新跑 Canon 校验", "success", 5000);
            Util.flash("#tab-chars .card");
        } catch (e) { Util.toast(e.message, "error"); }
        finally { Util.hideLoading(); }
    },
    async saveStorylineTab() {
        const id = State.currentNovelId; if (!id) return;
        try {
            const cur = await Util.get(`/novels/${id}/storyline`);
            const ov = cur.overall_storyline || {};
            ov.main_goal = document.getElementById("stMainGoal").value;
            ov.core_conflict = ov.core_conflict || {};
            ov.core_conflict.external      = document.getElementById("stExt").value;
            ov.core_conflict.internal      = document.getElementById("stInt").value;
            ov.core_conflict.interpersonal = document.getElementById("stIntp").value;
            ov.act1 = ov.act1 || {}; ov.act1.setup = document.getElementById("stAct1").value;
            ov.act2 = ov.act2 || {}; ov.act2.midpoint_crisis = document.getElementById("stAct2").value;
            ov.act3 = ov.act3 || {}; ov.act3.climax = document.getElementById("stAct3").value;
            ov.themes = document.getElementById("stThemes").value.split("\n").map(s => s.trim()).filter(Boolean);
            Util.showLoading("保存中…");
            await Util.put(`/novels/${id}/storyline`, { overall_storyline: ov });
            Util.toast("已保存 Storyline", "success");
            Util.flash("#tab-story .card");
        } catch (e) { Util.toast(e.message, "error"); }
        finally { Util.hideLoading(); }
    },

    /* ----------- 章节编辑 ----------- */
    toggleChapterEdit() {
        const reader = document.getElementById("chReader");
        const editor = document.getElementById("chEditor");
        const btn = document.getElementById("chEditBtn");
        const editing = editor.style.display !== "none";
        if (editing) {
            editor.style.display = "none";
            reader.style.display = "block";
            btn.innerHTML = `<i class="fas fa-pen me-1"></i>编辑`;
        } else {
            reader.style.display = "none";
            editor.style.display = "block";
            btn.innerHTML = `<i class="fas fa-eye me-1"></i>预览`;
        }
    },
    async saveChapter(n) {
        const id = State.currentNovelId; if (!id) return;
        const title = document.getElementById("chEditTitle").value.trim();
        const body  = document.getElementById("chEditBody").value;
        if (!title || !body.trim()) return Util.toast("标题和正文都不能为空", "warn");
        try {
            Util.showLoading("保存中…");
            const r = await Util.put(`/novels/${id}/chapters/${n}`, { title, body });
            Util.toast(`已保存（${r.word_count} 字）`, "success");
            App.go(`#/novel/${id}/chapter/${n}`);  // 刷新阅读器
        } catch (e) { Util.toast(e.message, "error"); }
        finally { Util.hideLoading(); }
    },

    /* ----------- 任务监控 ----------- */
    startPolling(taskId, onDone) {
        if (State.pollers[taskId]) return;
        const id = setInterval(async () => {
            try {
                const t = await Util.get(`/tasks/${taskId}`);
                App.refreshTaskBadge();
                if (t.status === "succeeded" || t.status === "failed") {
                    clearInterval(id);
                    delete State.pollers[taskId];
                    if (t.status === "succeeded") onDone && onDone(t);
                    else Util.toast(`任务失败：${t.error || "未知错误"}`, "error", 8000);
                }
            } catch (_) {}
        }, 2500);
        State.pollers[taskId] = id;
        App.refreshTaskBadge();
    },
    async refreshTaskBadge() {
        try {
            const tasks = await Util.get("/tasks");
            const running = tasks.filter(t => t.status === "running" || t.status === "pending").length;
            const badge = document.getElementById("navTaskBadge");
            if (running > 0) {
                badge.textContent = running;
                badge.style.display = "inline-block";
            } else {
                badge.style.display = "none";
            }
        } catch (_) {}
    },
    async openTasksModal() {
        const body = document.getElementById("tasksModalBody");
        body.innerHTML = `<div class="text-muted">加载中…</div>`;
        bootstrap.Modal.getOrCreateInstance(document.getElementById("tasksModal")).show();
        try {
            const tasks = await Util.get("/tasks");
            if (tasks.length === 0) {
                body.innerHTML = `<div class="text-muted text-center py-4">暂无任务记录</div>`;
                return;
            }
            const stCol = { pending: "secondary", running: "primary", succeeded: "success", failed: "danger" };
            body.innerHTML = tasks.map(t => {
                const p = t.progress || {};
                const pct = p.total ? Math.round((p.current / p.total) * 100) : 0;
                return `
                <div class="task-row">
                    <div class="d-flex justify-content-between mb-1">
                        <span><span class="badge bg-${stCol[t.status] || "secondary"} me-2">${t.status}</span>
                            <b>${Util.escape(t.type)}</b>
                            ${t.novel_id ? `· <span class="text-muted small">${t.novel_id.slice(0, 8)}…</span>` : ""}
                        </span>
                        <span class="text-muted small">${Util.fmtTs(t.started_at)}</span>
                    </div>
                    <div class="progress mb-1" style="height:6px">
                        <div class="progress-bar" style="width:${pct}%"></div>
                    </div>
                    <div class="small text-muted">${Util.escape(p.msg || "")} ${p.total ? `(${p.current}/${p.total})` : ""}</div>
                </div>`;
            }).join("");
        } catch (e) {
            body.innerHTML = `<div class="text-danger">${Util.escape(e.message)}</div>`;
        }
    },
};

/* ============================================================
 * v2.2 新增 App 方法：主页过滤 / 卷展开 / 阅读器升级 / 吸底任务条
 * ============================================================ */
App.applyHomeFilter = function () {
    const q = document.getElementById("homeQ");
    const sort = document.getElementById("homeSort");
    const stage = document.getElementById("homeStage");
    if (q) State.homeFilter.q = q.value;
    if (sort) State.homeFilter.sort = sort.value;
    if (stage) State.homeFilter.stage = stage.value;
    renderNovelGrid();
};
App.clearHomeFilter = function () {
    State.homeFilter = { q: "", sort: "updated_desc", stage: "all" };
    App.go("#/");
};

/* ----------- 题材库 ----------- */
App.openGenerateGenreModal = function () {
    document.getElementById("genGenreDesc").value = "";
    document.getElementById("genGenreName").value = "";
    bootstrap.Modal.getOrCreateInstance(document.getElementById("genGenreModal")).show();
};
/* 创建小说 modal 里点"LLM 造一个新题材"——先关掉创建 modal 再打开生成 modal */
App.openGenerateGenreModalFromCreate = function () {
    const cm = bootstrap.Modal.getInstance(document.getElementById("createModal"));
    if (cm) cm.hide();
    setTimeout(() => App.openGenerateGenreModal(), 300);
};
App.submitGenerateGenre = async function () {
    const description = document.getElementById("genGenreDesc").value.trim();
    const name = document.getElementById("genGenreName").value.trim();
    if (!description) return Util.toast("请填写题材描述", "warn");
    try {
        const r = await Util.post("/genres/generate", { description, name });
        bootstrap.Modal.getInstance(document.getElementById("genGenreModal")).hide();
        Util.toast("题材生成已启动…可在底部任务条查看进度", "success");
        App.startPolling(r.task_id, async (t) => {
            const genre = (t.result || {}).genre;
            if (genre) {
                Util.toast(`题材 ${genre.display_name || genre.name} 已生成，预览可保存`, "success", 5000);
                State._llmPreset = genre;
                App.go("#/genres/new");
            }
        });
    } catch (e) { Util.toast(e.message, "error"); }
};

App.deleteGenre = async function (name) {
    if (!confirm(`确定删除题材『${name}』？正被小说使用的题材无法删除。`)) return;
    try {
        await Util.del(`/genres/${encodeURIComponent(name)}`);
        Util.toast("已删除", "success");
        State.genres = [];
        App.go("#/genres");
    } catch (e) {
        Util.toast(e.message || "删除失败", "error", 6000);
    }
};

App.refreshGenreRaw = function () {
    const g = App._collectGenreFromForm();
    if (!g) return;
    document.getElementById("gRawJson").value = JSON.stringify(g, null, 2);
    Util.toast("已从上方表单同步到 JSON", "info", 1800);
};

App._collectGenreFromForm = function () {
    const splitLines = id => (document.getElementById(id).value || "")
        .split("\n").map(s => s.trim()).filter(Boolean);
    const splitCsv = id => (document.getElementById(id).value || "")
        .split(/[,，]/).map(s => s.trim()).filter(Boolean);
    const tags = {};
    document.querySelectorAll("[data-gtag]").forEach(el => {
        const cat = el.dataset.gtag;
        const arr = (el.value || "").split(/[,，]/).map(s => s.trim()).filter(Boolean);
        tags[cat] = arr;
    });
    return {
        name: document.getElementById("gName").value.trim(),
        display_name: document.getElementById("gDisplay").value.trim(),
        one_liner: document.getElementById("gOne").value.trim(),
        style_guide: document.getElementById("gStyle").value,
        allowed_elements: splitLines("gAllowed"),
        forbidden_elements: splitLines("gForbidden"),
        banned_phrases: splitLines("gBanned"),
        default_tags: tags,
        default_world_setting: {
            era: document.getElementById("gWsEra").value.trim(),
            world_archetype: document.getElementById("gWsArch").value.trim(),
            power_system: document.getElementById("gWsPower").value.trim(),
            tech_baseline: document.getElementById("gWsTech").value.trim(),
            key_locations: splitLines("gWsLoc"),
        },
        default_themes: splitLines("gThemes"),
        spec_template: {
            user_requirements_template: document.getElementById("gUrTpl").value,
            protagonist_skeleton: {
                basic_info: {
                    age: parseInt(document.getElementById("gProtoAge").value || "0") || undefined,
                    gender: document.getElementById("gProtoGender").value,
                    occupation: document.getElementById("gProtoOcc").value.trim(),
                    background: document.getElementById("gProtoBg").value,
                },
                personality: {
                    traits: splitCsv("gProtoTraits"),
                    weakness: splitCsv("gProtoWeak"),
                },
            },
            supporting_skeletons: ((State._editingGenre || {}).spec_template || {}).supporting_skeletons || [],
        },
    };
};

App.saveGenre = async function () {
    const isNew = !!State._editingGenreIsNew;
    let payload;
    const rawTab = document.getElementById("gRawJson");
    const rawTxt = rawTab && rawTab.value ? rawTab.value.trim() : "";
    if (rawTxt) {
        try {
            const parsed = JSON.parse(rawTxt);
            if (JSON.stringify(parsed) !== JSON.stringify(State._editingGenre)) {
                payload = parsed;
            }
        } catch (e) {
            return Util.toast(`原始 JSON 格式错误：${e.message}`, "error");
        }
    }
    if (!payload) payload = App._collectGenreFromForm();
    if (!payload) return;

    const name = (payload.name || "").trim().toLowerCase();
    if (!/^[a-z0-9_]{2,32}$/.test(name)) {
        return Util.toast("name 只能包含小写字母 / 数字 / 下划线，长度 2-32", "warn", 5000);
    }
    payload.name = name;

    try {
        Util.showLoading("保存中…");
        if (isNew) {
            await Util.post("/genres", payload);
            Util.toast("题材已新建", "success");
        } else {
            await Util.put(`/genres/${encodeURIComponent(name)}`, payload);
            Util.toast("题材已更新", "success");
        }
        State.genres = [];
        App.go(`#/genres/${encodeURIComponent(name)}`);
    } catch (e) { Util.toast(e.message, "error", 6000); }
    finally { Util.hideLoading(); }
};

App.toggleVolumeDetail = function (volIdx) {
    if (State.bp.expandedVolume === volIdx) {
        State.bp.expandedVolume = null;
    } else {
        State.bp.expandedVolume = volIdx;
    }
    if (State.currentNovelId) loadBlueprintPane(State.currentNovelId);
};

App.readerFont = function (delta) {
    if (delta === 0) {
        State.reader.fontSize = 17;
    } else {
        State.reader.fontSize = Math.max(13, Math.min(28, State.reader.fontSize + delta));
    }
    const card = document.getElementById("readerCard");
    if (card) card.style.fontSize = State.reader.fontSize + "px";
    const lbl = document.getElementById("readerFontLabel");
    if (lbl) lbl.textContent = State.reader.fontSize;
    try {
        localStorage.setItem("inkai_reader_prefs", JSON.stringify({ fontSize: State.reader.fontSize }));
    } catch (_) {}
};

App.toggleFullscreen = function () {
    State.reader.fullscreen = !State.reader.fullscreen;
    document.body.classList.toggle("reader-fullscreen", State.reader.fullscreen);
    const ic = document.getElementById("fullscreenIcon");
    if (ic) ic.className = State.reader.fullscreen ? "fas fa-compress" : "fas fa-expand";
};

/* ----------- 吸底任务条（dock） ----------- */
App.renderTaskDock = async function () {
    try {
        const tasks = await Util.get("/tasks");
        const running = tasks.filter(t => t.status === "running" || t.status === "pending");
        const dock = document.getElementById("taskDock");
        const inner = document.getElementById("taskDockInner");
        if (running.length === 0) {
            dock.style.display = "none";
            return;
        }
        dock.style.display = "block";
        inner.innerHTML = running.map(t => {
            const p = t.progress || {};
            const pct = p.total ? Math.round((p.current / p.total) * 100) : 0;
            const typeLabel = {
                create_novel: "创建小说",
                generate_blueprint: "生成蓝图",
                generate_chapters: "生成章节",
            }[t.type] || t.type;
            return `
                <div class="task-dock-row">
                    <div class="task-dock-icon"><i class="fas fa-cog fa-spin"></i></div>
                    <div class="task-dock-meta flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span><b>${Util.escape(typeLabel)}</b>
                                ${t.novel_id ? `<span class="text-muted small ms-1">${t.novel_id.slice(0, 8)}…</span>` : ""}
                            </span>
                            <span class="small text-muted">${pct}%${p.total ? ` (${p.current}/${p.total})` : ""}</span>
                        </div>
                        <div class="progress" style="height:5px">
                            <div class="progress-bar bg-primary" style="width:${pct}%"></div>
                        </div>
                        <div class="small text-muted mt-1">${Util.escape(p.msg || "")}</div>
                    </div>
                    ${t.novel_id ? `
                    <button class="btn btn-sm btn-outline-light" onclick="App.go('#/novel/${t.novel_id}')" title="去对应小说">
                        <i class="fas fa-arrow-right"></i>
                    </button>` : ""}
                </div>`;
        }).join("");
        // 同时刷新 navbar 徽章
        const badge = document.getElementById("navTaskBadge");
        badge.textContent = running.length;
        badge.style.display = "inline-block";
    } catch (_) {}
};

/* 覆盖 startPolling：完成后还要自动刷新当前页 */
App._startPollingOriginal = App.startPolling;
App.startPolling = function (taskId, onDone) {
    if (State.pollers[taskId]) return;
    State.runningTaskIds.add(taskId);
    App.renderTaskDock();
    const id = setInterval(async () => {
        try {
            const t = await Util.get(`/tasks/${taskId}`);
            App.renderTaskDock();
            if (t.status === "succeeded" || t.status === "failed") {
                clearInterval(id);
                delete State.pollers[taskId];
                State.runningTaskIds.delete(taskId);
                App.renderTaskDock();
                if (t.status === "succeeded") {
                    onDone && onDone(t);
                    // 自动刷新当前页（如果还停留在受影响的小说工作流页）
                    const r = parseHash();
                    if (r.name === "novel" && (t.novel_id === r.novelId)) {
                        renderNovel(document.getElementById("mainContainer"), r.novelId);
                    } else if (r.name === "home") {
                        renderHome(document.getElementById("mainContainer"));
                    }
                } else {
                    Util.toast(`任务失败：${t.error || "未知错误"}`, "error", 8000);
                }
            }
        } catch (_) {}
    }, 2500);
    State.pollers[taskId] = id;
};

/* 启动时把已经在跑的任务接管进 dock */
App.adoptRunningTasks = async function () {
    try {
        const tasks = await Util.get("/tasks");
        tasks.filter(t => t.status === "running" || t.status === "pending").forEach(t => {
            if (!State.pollers[t.task_id]) App.startPolling(t.task_id, () => {});
        });
    } catch (_) {}
};

window.App = App;

/* ----------- 全局键盘快捷键（capture 阶段，避免被任何 stopPropagation 干扰） ----------- */
function _inEditableField(e) {
    const t = e.target;
    if (!t) return false;
    const tag = (t.tagName || "").toUpperCase();
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (t.isContentEditable) return true;
    return false;
}

function _handleHotkey(e) {
    const key = (e.key || "").toLowerCase();
    const r = parseHash();

    // Ctrl/Cmd + S：永远 preventDefault 阻止浏览器"另存为"，
    // 在编辑器显示时触发保存
    if ((e.ctrlKey || e.metaKey) && key === "s") {
        e.preventDefault();
        e.stopPropagation();
        const editor = document.getElementById("chEditor");
        if (editor && editor.style.display !== "none" && r.name === "chapter") {
            App.saveChapter(r.n);
        }
        return;
    }

    // 在 input/textarea 中输入时，不拦截方向键和 F/E
    if (_inEditableField(e)) return;

    if (r.name === "chapter") {
        if (key === "arrowleft" || key === "pageup") {
            if (r.n > 1) {
                e.preventDefault();
                App.go(`#/novel/${r.novelId}/chapter/${r.n - 1}`);
            }
        } else if (key === "arrowright" || key === "pagedown" || key === " ") {
            e.preventDefault();
            App.go(`#/novel/${r.novelId}/chapter/${r.n + 1}`);
        } else if (key === "f") {
            e.preventDefault();
            App.toggleFullscreen();
        } else if (key === "e") {
            e.preventDefault();
            App.toggleChapterEdit();
        } else if (key === "escape" && State.reader.fullscreen) {
            e.preventDefault();
            App.toggleFullscreen();
        }
    }
}

// 用 capture 阶段保证最早接收事件
window.addEventListener("keydown", _handleHotkey, true);

/* ----------- 启动 ----------- */
window.addEventListener("DOMContentLoaded", () => {
    if (!location.hash) location.hash = "#/";
    route();
    setInterval(App.renderTaskDock, 3000);
    App.adoptRunningTasks();
});
