<div align="center">

# InkAI

### 基于大语言模型的中长篇小说自动创作系统

*从一句话到一千章 — 让 AI 写出结构完整、节奏稳定、长线连贯的小说*

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=flat-square&logo=flask&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Models](https://img.shields.io/badge/LLM-qwen3.6--plus%20%7C%20deepseek%20%7C%20gpt--4o-blue?style=flat-square)
![Architecture](https://img.shields.io/badge/Architecture-33%20Agents%20%C2%B7%2042%20Core%20Modules-orange?style=flat-square)

[快速开始](#快速开始) · [架构演进](#架构演进) · [技术亮点](#技术亮点) · [Issue 修复案例](#issue-2-修复案例) · [项目结构](#项目结构)

</div>

---

## 为什么做这个项目

市面上的 AI 写作工具大多是"单点续写"——给个开头，AI 接着写几百字。但长篇小说（100-1000 章）的核心难题不是"写一段"，而是 **长线闭环**：

- 第 500 章不能让主角改名、不能让已死角色复活
- 第 1 章埋的伏笔要在第 1000 章兑现
- 节奏不能掉——3 章一循环（缓冲 → 转折 → 强推）
- 跨章不能复读——同一句式不能反复出现

InkAI 用 **结构化卡片驱动 + 跨章状态追踪 + 多维硬校验** 解决这些问题。不是"AI 续写工具"，而是一个完整的创作工程系统。

---

## 亮点速览

| 维度 | 实现 |
|------|------|
| **章节卡驱动写作** | `ChapterCardWriter` 基于结构化 ChapterCard（beats / must_appear / foreshadow_plant / ending_hook）生成单章，硬校验字数 ±20% / 主角 ≥2 次 / 必现元素全覆盖 |
| **跨章状态追踪** | `DynamicKnowledgeManager` 维护伏笔生命周期（open/planted/closed/overdue）、角色持有物、常驻场景，每章快照注入 prompt |
| **题材规则注入** | `GenrePack` 全链路注入 style_guide / banned_phrases / supporting_skeletons，仙侠/悬疑/校园各自有写作规则 |
| **多 Provider 支持** | dashscope / deepseek / openai 三种 provider，embedding 独立配置，prompt cache 命中诊断 |
| **批注驱动重写** | 读者选中文字标记问题（模板复读/内容重复/逻辑矛盾），AI 根据批注重写对应段落 |

---

## 快速开始

### 环境要求

- Python 3.9+
- 阿里云百炼 / DeepSeek / OpenAI API Key（任选其一）

### 三步启动

```bash
# 1. 克隆 + 安装
git clone https://github.com/yan2959088709/InkAI-.git
cd InkAI-
pip install -r requirements.txt

# 2. 配置 API Key（环境变量）
export INKAI_API_KEY="sk-your-dashscope-key"
# 或 DeepSeek：export INKAI_PROVIDER="deepseek" && export INKAI_API_KEY="sk-your-deepseek-key"

# 3. 启动 Web 界面
python server.py
# 浏览器打开 http://127.0.0.1:5000
```

### CLI 新流水线（批量生成）

```bash
# 初始化小说（元信息 + 人物 + 故事线）
python run_init_novel.py --genre xianxia --title "九霄道行" --protagonist "林朝歌"

# 生成蓝图 + 卷章节卡
python run_outline_demo.py --novel-id <id>

# 批量生成 1-10 章
python run_chapter_demo.py --novel-id <id> --start-chapter 1 --end-chapter 10
```

---

## 架构演进

这个项目经历了两次重大架构重构。**记录这些决策比代码本身更重要**——它们体现了"为什么这样设计"的工程思考。

### v1.0 → v1.10（2025-09）: 从原型到多 Agent

**起点**：5 个 agent 的单点续写原型（`main.py` CLI + `inkai_workflow.py`）。

**问题**：单 agent 写出来的章节质量不稳定，缺乏多维度校验。

**演进**：扩展到 25 个 agent，按"创作 / 续写 / 评估 / 改进"四层组织。引入 `inkai_workflow_optimized.py`（140KB 单体状态机）统一编排。

**代价**：单体状态机膨胀到 1649 行，所有 workflow 逻辑硬编码在一个类里，无插件机制。

### v1.10 → v2.11（2026-04）: 架构重构，删除多入口

这是最重要的一次重构。**删掉的东西比新增的多**。

#### 删除的决策

| 删除项 | 原因 |
|--------|------|
| `app.py`（1496 行 Flask 入口） | 多入口共享同一单体 workflow，状态不一致风险高 |
| `main.py`（交互式 CLI） | 交互式无法批量，被 `run_*.py` 脚本化 CLI 取代 |
| `start_web.py` | 与 `app.py` 重复，统一为 `server.py` 单入口 |
| `quick_continuation_executor.py`（900 行） | 新 pipeline 的 `run_chapter_demo.py` 已含批量 + 断点续写，冗余 |
| `storyline_improver.py` | 功能被 `enhanced_storyline_generator.py` 覆盖 |
| glm-4.5-flash 模型 | 128K 上下文不够，长篇需要 1M 上下文（qwen3.6-plus） |

#### 保留的决策

| 保留项 | 原因 |
|--------|------|
| `inkai_workflow_optimized.py`（140KB 单体） | **Stunt Double 模式** — 冻结作为 rollback safety，新 pipeline 稳定 3+ 迭代后再删 |
| `chapter_writer.py`（旧版章节写作） | 与新版 `chapter_card_writer.py` 并存，新版基于结构化卡片，旧版基于自由 prompt，渐进迁移 |

#### 新增的决策

| 新增项 | 解决的问题 |
|--------|-----------|
| `ChapterCardWriter` | 旧版自由 prompt 写作质量不可控；新版基于 ChapterCard 结构化卡片 + 硬校验 |
| `OutlinePlanner` | 旧版无蓝图，章节间剧情不连贯；新版先生成整本蓝图 + 分卷章节卡 |
| `GenrePack` | 旧版无题材规则；新版按题材注入 style_guide / banned_phrases |
| `DynamicKnowledgeManager` | 旧版无跨章状态；新版追踪伏笔/人物/物品/场景 |
| 跨章句式去重（开发中） | 旧版章节间句式复读严重；新版扫描高频指纹注入禁用列表 |
| `server.py` 单入口 | 替代多入口，统一 API + 前端托管 |
| `run_*.py` CLI 系列（11 个） | 替代交互式 CLI，支持脚本化批量 |

**核心原则**：新代码在新模块（black-box isolation），旧模块只做最小 wiring 改动，不重构旧模块内部。这避免了"重构雪崩"——改一个地方崩三个地方。

### v2.11 → 当前（2026-07）: Issue #2 修复 + 多 Provider

开源后收到用户反馈（[Issue #2](#issue-2-修复案例)），暴露了两个工程问题：

1. DeepSeek 缓存命中率 0% — prompt 结构问题
2. DeepSeek 配置后 embedding 失败 — 配置耦合问题

修复详见 [Issue #2 修复案例](#issue-2-修复案例)。

---

## 技术亮点

### 1. ChapterCardWriter：结构化卡片驱动写作

**问题**：自由 prompt 写作不可控——字数漂移、主角失踪、必现道具被同义词替换。

**方案**：每章先生成结构化 ChapterCard，写作器基于卡片硬约束生成。

```python
# ChapterCard 结构
{
  "chapter_number": 5,
  "title": "古玩造假",
  "role": "advancement",           # 缓冲/转折/强推
  "beats": ["主角鉴定古玩", "发现造假证据", "对手威胁"],
  "must_appear": {
    "characters": ["林朝歌", "苏婉清"],   # 硬失败：必须出场
    "objects": ["恐吓信"],               # 硬失败：必须原词出现
    "locations": ["古玩市场"]            # 软告警
  },
  "foreshadow_plant": ["F03"],     # 本章埋下的伏笔 ID
  "foreshadow_payoff": ["F01"],    # 本章兑现的伏笔 ID
  "ending_hook": "雨夜惊雷",        # 章末钩子（会被加入下章 banned_endings）
  "tension_level": 7
}
```

**硬校验**（失败则重写一次）：
- 字数：目标 ±20%，硬上限 +30%
- 主角出现 ≥2 次
- `must_appear.characters` / `objects` 必须原词出现（不可同义词替换）
- 章末 300 字不得命中 `banned_endings`

### 2. DynamicKnowledgeManager：跨章状态追踪

**问题**：第 50 章不能让第 10 章已死角色复活，不能让已回收的伏笔再次被埋。

**方案**：DKM 维护跨章状态，每章快照注入 prompt。

```
DKM 维护的状态：
├── characters
│   ├── first/last_appearance          首末次出场
│   ├── appearance_chapters            出场章节列表
│   ├── total_mentions                 总提及次数
│   └── currently_holds                当前持有道具
├── objects
│   ├── holders_chain                  持有者链（A->B->C）
│   └── current_holder                 当前持有者
├── locations
│   ├── appearance_count               出现次数
│   └── is_recurring                   是否常驻（≥3 章）
└── foreshadowings
    ├── id (F01, F02, ...)             规范 ID（来自 blueprint.global_foreshadow_ledger）
    ├── status                         open / planted / closed / overdue
    └── age                            距埋设章数（>12 章 = overdue）
```

**伏笔状态机**：`open` → `planted`（埋设） → `closed`（兑现） / `overdue`（超期未兑现，触发警告）

### 3. GenrePack：题材规则全链路注入

**问题**：仙侠和悬疑的写作规则完全不同，通用 prompt 写不出题材味。

**方案**：每个题材一个 JSON 包，含 `style_guide` / `allowed_elements` / `forbidden_elements` / `banned_phrases` / `supporting_skeletons`，全链路注入 OutlinePlanner + ChapterCardWriter。

```bash
data/genres/
├── xianxia.json        # 仙侠：禁用现代词汇，要求境界体系
├── detective.json      # 悬疑：禁用超自然元素，要求线索公平性
└── campus_youth.json   # 校园青春：禁用暴力，要求青春期心理描写
```

### 4. 跨章句式去重

**问题**：AI 写 50 章后开始复读——"他的眼神变得锐利"、"空气中弥漫着紧张"反复出现。

**方案**：写新章前扫描全文，提取高频句式指纹（≥2 次出现，8-40 字），注入本章 system prompt 的"跨章去重铁律"。

> 注：此功能在 v2.11 开源版本中尚未包含，正在开发中。

### 5. 多 Provider 支持 + Prompt Cache 诊断

详见 [Issue #2 修复案例](#issue-2-修复案例)。

---

## Issue #2 修复案例

这是开源后收到的一个真实 Issue，修复过程体现了 **用户反馈闭环 / 根因分析 / 不留尾巴** 的工程素养。

### Issue 描述

> **Eli-Zxh (2026-06-30)**: 接入 deepseek-v4-flash 后缓存命中率是 0，怀疑是提示词工程问题。
>
> **eirakezhao (2026-07-20)**: 在 config 里配置了 DEEPSEEK，结果 WEB 端一直提示失败。

### 根因分析

**问题 1：缓存命中率 0%**

DeepSeek 的 prompt cache 基于 **前缀完全匹配**。调查 `chapter_card_writer._system_prompt` 发现：

```python
# 修复前 — system prompt 含动态内容，每章都不同
base = (
    f"3. 严禁出现下列钩子句式：{banned_text}。\n"      # ❌ 每章 banned_text 不同
    f"4. 字数：{target_word_count}±20% 字。\n"         # ❌ 每章 target_word_count 可能不同
)
if cross_chapter_banned:
    base += f"以下句式已反复出现：{preview}"            # ❌ 每章 cross_chapter_banned 不同
```

system prompt 字节级变化 → 前缀不匹配 → cache 完全无法命中。

**问题 2：DeepSeek 配置失败**

`config.py` 里 embedding/rerank 复用主 LLM key：

```python
# 修复前 — embedding 复用主 key
EMBEDDING_API_KEY = os.environ.get("INKAI_API_KEY", "")  # ❌ DeepSeek key 不能用于 DashScope embedding
EMBEDDING_BASE_URL = "https://dashscope.aliyuncs.com/..."  # embedding 端点固定 DashScope
```

用户配 DeepSeek key → embedding 调用 DashScope → key 无效 → 依赖 embedding 的功能（知识图谱）失败 → 前端报错。

### 修复方案

**修复 1：system prompt 静态化**

```python
# 修复后 — system prompt 只含静态内容，动态内容移到 user prompt
def _system_prompt(self, protagonist_name, name_whitelist):
    return (
        f"3. 严禁使用前几章已用过的钩子句式；具体禁用清单见 user prompt 中的【本章禁用钩子】。\n"
        f"4. 字数控制在目标值±20%；具体目标字数见 user prompt 中的【目标字数】。\n"
    )

def _build_user_prompt(self, ..., banned_endings, target_word_count, ...):
    # 动态内容放这里
    banned_block = f"=== 本章禁用钩子 ===\n- {banned_endings}"
    target_block = f"=== 目标字数 ===\n{target_word_count} ±20%"
```

**验证**：构造两章不同动态数据，断言 `system1 == system2` ✅

**修复 2：embedding/rerank 独立配置 + Provider 抽象**

```python
# 修复后 — provider 抽象 + embedding 独立 key
PROVIDER_PRESETS = {
    "dashscope": {"base_url": "...", "model": "qwen3.6-plus", "embedding_base_url": "..."},
    "deepseek":  {"base_url": "...", "model": "deepseek-chat", "embedding_base_url": "dashscope..."},  # DeepSeek 不提供 embedding，回退 dashscope
    "openai":    {"base_url": "...", "model": "gpt-4o-mini", "embedding_base_url": "..."},
}

EMBEDDING_API_KEY = os.environ.get("INKAI_EMBEDDING_API_KEY", "") or API_KEY  # 独立 key，回退主 key

def _compute_embedding_status():
    """诊断：LLM 与 embedding 跨 host 且复用 key 时警告"""
    if llm_host != emb_host and EMBEDDING_API_KEY == API_KEY:
        return {"status": "warning", "message": "请配 INKAI_EMBEDDING_API_KEY"}
```

**修复 3：cache 命中诊断日志**

```python
# base_agent.py — 读取 response.usage 的 cache hit 字段
usage = response.usage
cache_hit = getattr(usage, 'prompt_cache_hit_tokens', None)  # DeepSeek
if cache_hit is None:
    cache_hit = usage.prompt_tokens_details.cached_tokens     # OpenAI
self.log(f"[cache] prompt={prompt_tokens} cache_hit={cache_hit} ({hit_rate:.1f}%)")
```

### 修复成果

- DeepSeek 缓存命中率从 0% 提升（具体数值取决于 prompt 重复度）
- DeepSeek 配置不再失败（embedding 用独立 key）
- `/api/config` 返回 `embedding_status` 诊断信息，用户能明确看到配置问题
- 向后兼容：dashscope 用户无感知，老 config.json 仍能工作

### 体现的工程能力

1. **用户反馈闭环**：Issue 报告 → 根因定位 → 修复 → 验证 → 推送
2. **不留尾巴**：修复时发现 openai provider 误报 warning（同 host 复用 key 合法），立即修正诊断逻辑
3. **决策记录**：修复过程记录在 commit message 和 Issue #2 闭环中
4. **向后兼容**：`save_api_key` 保留为 `save_config` 的 wrapper，老调用方无感知

---

## 数据流

### 单章生成流程（11 步）

```
1.  定位卷 + 加载卷章节卡
2.  抽取本章 ChapterCard
3.  收集卷内已用钩子（banned_endings）
4.  加载近 N 章原文（承接锚点）
5.  DKM 快照（伏笔/人物/物品/场景状态）
6.  跨章去重（高频句式指纹注入禁用列表）
7.  LLM 写作（system prompt 静态 + user prompt 动态）
8.  字数/主角/必现元素/禁用钩子校验
9.  失败重写一次（带反馈）
10. 落盘 + DKM 状态更新
11. 批量收尾：VolumeValidator 整卷校验
```

### 状态持久化

```
data/novels/<novel_id>/
├── metadata.json                    小说元信息
├── characters.json                  人物档案
├── storyline.json                   故事线
├── outline/
│   ├── blueprint.json               整本蓝图（name_whitelist / global_foreshadow_ledger）
│   └── volume_<N>_chapters.json     卷章节卡
├── chapters_demo/
│   ├── chapter_<N>.txt              章节正文
│   └── chapter_<N>.meta.json        章节元信息（含 validation）
├── dynamic_state/
│   └── state.json                   DKM 状态
└── validation/
    └── volume_<N>_report.json       卷校验报告
```

---

## 项目结构

```
InkAI/
├── server.py                        # Web 服务入口（Flask，端口 5000）
├── base_agent.py                    # 智能体基类（LLM 调用 + 缓存诊断）
├── config.py                        # 多 provider 配置（dashscope/deepseek/openai）
├── data_manager.py                  # 数据持久化
├── workflow_context.py              # 工作流上下文
├── inkai_workflow_optimized.py      # 旧 pipeline（冻结保留，stunt double）
│
├── run_*.py                         # 新 pipeline CLI（11 个脚本）
│   ├── run_init_novel.py            #   初始化小说
│   ├── run_outline_demo.py          #   蓝图 + 卷章节卡
│   ├── run_chapter_demo.py          #   章节生成（批量 + 断点续写）
│   ├── run_validate_canon.py        #   正典校验
│   ├── run_validate_volume.py       #   卷校验
│   ├── run_full_novel_audit.py      #   全书 6 维审计
│   └── ...
│
├── agents/                          # 33 个智能体
│   ├── chapter_card_writer.py       #   章节卡写作（推荐）
│   ├── chapter_writer.py            #   旧版章节写作（保留）
│   ├── tag_selector.py              #   标签选择
│   ├── character_creator.py         #   人物创建
│   ├── storyline_generator.py       #   故事线生成
│   ├── volume_validator.py          #   卷校验
│   ├── continuation_*.py            #   续写系列（评估 6 + 改进 6）
│   └── ...
│
├── core/                            # 42 个核心模块
│   ├── outline_planner.py           #   蓝图 + 卷章节卡规划
│   ├── genre_pack.py                #   题材包系统
│   ├── dynamic_knowledge_manager.py #   动态知识管理（DKM）
│   ├── api_rate_limiter.py          #   LLM 速率限制（2 并发 + 1s 间隔）
│   ├── canon_checker.py             #   正典校验
│   ├── full_novel_auditor.py        #   全书 6 维审计
│   ├── rhythm_controller.py         #   节奏控制
│   ├── foreshadowing_lifecycle_manager.py  伏笔生命周期
│   ├── embedding_service.py         #   Embedding 服务
│   └── ...
│
├── utils/                           # 工具（json_fixer / logger / type_safety）
├── data/genres/                     # 题材包 JSON（仙侠/悬疑/校园）
├── frontend/                        # 前端 SPA（Bootstrap 5 + Chart.js）
├── docs/                            # 文档
└── requirements.txt
```

---

## 多 Provider 配置

| Provider | `INKAI_PROVIDER` | BASE_URL | 默认模型 | Embedding |
|----------|------------------|----------|----------|-----------|
| 阿里云百炼（默认） | `dashscope` | dashscope.aliyuncs.com | qwen3.6-plus | text-embedding-v3（同 provider） |
| DeepSeek | `deepseek` | api.deepseek.com | deepseek-chat | 回退 dashscope（需独立 key） |
| OpenAI | `openai` | api.openai.com | gpt-4o-mini | text-embedding-3-small（同 provider） |

### 环境变量

```bash
# 主 LLM 配置
INKAI_PROVIDER                      # dashscope / deepseek / openai（默认 dashscope）
INKAI_API_KEY                       # 主 LLM API key（必需）
INKAI_BASE_URL                      # 覆盖 provider preset 的 base_url
INKAI_MODEL                         # 覆盖 provider preset 的 model

# Embedding/Rerank 独立配置（LLM 非 dashscope 时必需）
INKAI_EMBEDDING_API_KEY             # embedding key（不配则回退主 key + warning）
INKAI_EMBEDDING_BASE_URL            # embedding base_url
INKAI_EMBEDDING_MODEL               # embedding 模型名
INKAI_RERANK_API_KEY                # rerank key
INKAI_RERANK_BASE_URL               # rerank base_url
```

### 配置诊断

```bash
curl http://localhost:5000/api/config
```

```json
{
  "ok": true,
  "data": {
    "provider": "dashscope",
    "model": "qwen3.6-plus",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "has_api_key": true,
    "api_key_preview": "sk-6275...372d",
    "available_providers": ["dashscope", "deepseek", "openai"],
    "has_embedding_key": false,
    "embedding_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "embedding_status": {"status": "ok", "message": ""}
  }
}
```

`embedding_status` 可能值：`ok` / `warning`（跨 host 复用 key）/ `error`（无 embedding key）。

---

## 版本历史

| 版本 | 时间 | 核心变化 |
|------|------|----------|
| v1.0 | 2025-09 | 5 agent 单点续写原型 |
| v1.10 | 2025-09 | 25 agent + 多入口 + glm-4.5-flash |
| v2.11 | 2026-04 | 架构重构：删除多入口，引入 ChapterCardWriter/OutlinePlanner/GenrePack/DKM，切换 qwen3.6-plus |
| 当前 | 2026-07 | Issue #2 修复：prompt cache 命中 + 多 provider + embedding 解耦 |

---

## 已知限制

- **无并发控制**：`data_manager.py` 写 JSON 无文件锁，并发请求可能损坏数据
- **无 API 输入校验**：`server.py` 部分端点直接传 raw payload 给 agent
- **Module-level 副作用**：`config.py` import 时创建目录，只读环境导入会失败
- **旧 pipeline 保留**：`inkai_workflow_optimized.py`（140KB 单体）冻结保留作为 rollback safety，新 pipeline 是推荐路径

---

## Roadmap

- [ ] 文件锁支持（解决并发写入）
- [ ] API 输入 schema 校验（pydantic）
- [ ] 向量检索增强（基于 Milvus 的语义回忆）
- [ ] 更多题材包（科幻 / 武侠 / 历史）
- [ ] 测试套件（pytest + 集成测试）

---

## 反馈与建议

Bug 报告、功能建议或任何其他反馈，欢迎通过邮箱联系：

- **邮箱**：[iudm0358@agent.qq.com](mailto:iudm0358@agent.qq.com)

---

## License

MIT

---

<div align="center">

*如果这个项目对你有帮助，欢迎 Star 支持*

</div>
