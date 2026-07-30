# InkAI - AI 小说创作系统

> 基于大语言模型的中长篇小说自动创作系统，支持上千章小说的智能生成

---

## 项目概述

InkAI 是一个专业的 AI 小说创作系统，专门针对中长篇小说（100-1000 章）设计。它不是简单的"AI 续写"，而是一个完整的创作工作流，包含：

- **章节卡驱动的写作**（ChapterCardWriter）：基于结构化卡片生成单章正文
- **蓝图 + 卷章节卡规划**（OutlinePlanner）：整本蓝图 + 分卷章节卡
- **题材包系统**（GenrePack）：题材规则全链路注入
- **动态知识管理**（DKM）：跨章伏笔 / 人物 / 物品 / 场景状态追踪
- **多维度校验**：字数 / 主角 / 必现元素 / 禁用钩子 / 跨章句式去重
- **批注驱动重写**（半闭环读者反馈）

### 核心理念

```
短篇靠单点爆破，中长篇靠长线闭环
```

中长篇小说的核心是：**长线结构闭环、持续的情绪张力、完整的人物弧光**

---

## 快速开始

### 环境要求

- Python 3.9+
- 阿里云百炼 / DeepSeek / OpenAI API Key（任选其一）

### 安装

```bash
git clone https://github.com/yan2959088709/InkAI-.git
cd InkAI-
pip install -r requirements.txt
```

### 配置

通过环境变量配置（推荐）：

```bash
# 阿里云百炼（默认）
export INKAI_API_KEY="sk-your-dashscope-key"

# 或 DeepSeek
export INKAI_PROVIDER="deepseek"
export INKAI_API_KEY="sk-your-deepseek-key"
# DeepSeek 不提供 embedding，需独立配置 DashScope embedding key
export INKAI_EMBEDDING_API_KEY="sk-your-dashscope-key"

# 或 OpenAI
export INKAI_PROVIDER="openai"
export INKAI_API_KEY="sk-your-openai-key"
```

### 运行

```bash
# Web 界面（推荐）
python server.py
# 浏览器打开 http://127.0.0.1:5000

# 或 CLI 新流水线
python run_init_novel.py --genre xianxia --title "九霄道行" --protagonist "林朝歌"
python run_outline_demo.py --novel-id <id>
python run_chapter_demo.py --novel-id <id> --start-chapter 1 --end-chapter 10
```

---

## 技术架构

### 新流水线（推荐）

```
用户输入
    ↓
run_init_novel.py    -> metadata.json + characters.json + storyline.json
    ↓
run_outline_demo.py  -> outline/blueprint.json + outline/volume_*_chapters.json
    ↓
run_chapter_demo.py  -> chapters_demo/chapter_*.txt + chapter_*.meta.json
    ↓
run_validate_*.py    -> canon_report.json / volume_*_report.json
```

### 核心组件

| 模块 | 文件 | 职责 |
|------|------|------|
| Web 服务 | `server.py` | Flask API + 前端静态托管 |
| 章节卡写手 | `agents/chapter_card_writer.py` | 基于 ChapterCard 生成单章正文 |
| 蓝图规划器 | `core/outline_planner.py` | 整本蓝图 + 分卷章节卡 |
| 题材包 | `core/genre_pack.py` | 题材规则注入（style_guide / banned_phrases / supporting_skeletons） |
| 动态知识管理 | `core/dynamic_knowledge_manager.py` | 跨章伏笔 / 人物 / 物品 / 场景状态 |
| 跨章去重 | `core/cross_chapter_dedup.py` | 高频句式指纹提取 + 禁用注入 |
| 速率限制 | `core/api_rate_limiter.py` | 2 并发 + 1s 间隔 |
| 基础智能体 | `base_agent.py` | LLM 调用封装 + 缓存命中诊断 |

### 智能体系统（33 个 agent）

```
agents/
├── 创作类
│   ├── tag_selector.py              标签选择
│   ├── character_creator.py         人物创建
│   ├── storyline_generator.py       故事线生成
│   ├── chapter_writer.py            旧版章节写作（保留）
│   ├── chapter_card_writer.py       新版章节卡写作（推荐）
│   ├── chapter_summary_generator.py 章节摘要
│   ├── enhanced_storyline_generator.py 增强故事线
│   ├── genre_pack_generator.py      题材包生成
│   ├── simplified_writer_agent.py   简化写作
│   └── volume_validator.py          卷校验
│
├── 续写类
│   ├── continuation_storyline_generator.py
│   ├── continuation_chapter_writer.py
│   ├── continuation_chapter_improver.py
│   └── novel_continuation_agent.py
│
├── 评估类（6 个维度）
│   ├── continuation_quality_assessor.py
│   ├── continuation_character_consistency_assessor.py
│   ├── continuation_plot_logic_assessor.py
│   ├── continuation_world_consistency_assessor.py
│   ├── continuation_style_consistency_assessor.py
│   ├── continuation_reader_experience_assessor.py
│   └── continuation_long_term_consistency_assessor.py
│
├── 改进类（对应 6 个评估）
│   └── continuation_*_improver.py
│
└── 基类
    ├── base_continuation_assessor.py
    └── base_continuation_improver.py
```

### 核心模块（core/，42 个）

```
core/
├── outline_planner.py               蓝图 + 卷章节卡规划
├── genre_pack.py                    题材包系统
├── dynamic_knowledge_manager.py     动态知识管理（DKM）
├── dynamic_knowledge_graph.py       动态知识图谱
├── cross_chapter_dedup.py           跨章句式去重
├── api_rate_limiter.py              LLM 速率限制
├── canon_checker.py                 正典校验
├── full_novel_auditor.py            全书 6 维审计
├── volume_manager.py                分卷管理
├── rhythm_controller.py             节奏控制
├── foreshadowing_lifecycle_manager.py 伏笔生命周期
├── foreshadowing_recycler.py        伏笔回收
├── enhanced_context_builder.py      上下文构建
├── sliding_window_context.py        滑动窗口
├── context_slicer.py                上下文切片
├── fault_tolerance.py               容错
├── quality_circuit_breaker.py       质量熔断
├── embedding_service.py             Embedding 服务
├── vector_database.py               向量库
└── ...（共 42 个模块）
```

---

## 数据流

### 单章生成流程（新流水线）

```
1. 定位卷 + 加载卷章节卡
2. 抽取本章 ChapterCard
3. 收集卷内已用钩子（banned_endings）
4. 加载近 N 章原文（承接锚点）
5. DKM 快照（伏笔/人物/物品/场景状态）
6. 跨章去重（高频句式指纹注入禁用列表）
7. LLM 写作（system prompt 静态 + user prompt 动态）
8. 字数/主角/必现元素/禁用钩子校验
9. 失败重写一次（带反馈）
10. 落盘 + DKM 状态更新
11. 批量收尾：VolumeValidator 整卷校验
```

### 状态持久化

```
data/novels/<novel_id>/
├── metadata.json                    小说元信息
├── characters.json                  人物档案
├── storyline.json                   故事线
├── annotations.json                 读者批注
├── outline/
│   ├── blueprint.json               整本蓝图（含 name_whitelist / global_foreshadow_ledger）
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

## 多 Provider 支持

InkAI 支持三种 LLM provider（通过 `INKAI_PROVIDER` 环境变量切换）：

| Provider | BASE_URL | 默认模型 | Embedding |
|----------|----------|----------|-----------|
| dashscope（默认） | dashscope.aliyuncs.com | qwen3.6-plus | text-embedding-v3 |
| deepseek | api.deepseek.com | deepseek-chat | 回退 dashscope |
| openai | api.openai.com | gpt-4o-mini | text-embedding-3-small |

**Embedding 独立配置**：当 LLM provider 不是 dashscope 时，embedding 需独立配置 `INKAI_EMBEDDING_API_KEY`，否则会因 key 跨 host 复用而失败。系统会在 `/api/config` 返回 warning 诊断。

---

## 配置 API

```bash
# 查看当前配置（不泄露完整 key）
curl http://localhost:5000/api/config
```

返回示例：
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

---

## 项目结构

```
InkAI/
├── server.py                        # Web 服务入口
├── base_agent.py                    # 智能体基类（LLM 调用 + 缓存诊断）
├── config.py                        # 多 provider 配置
├── data_manager.py                  # 数据持久化
├── workflow_context.py              # 上下文管理
│
├── run_init_novel.py                # CLI: 初始化小说
├── run_outline_demo.py              # CLI: 蓝图 + 卷章节卡
├── run_chapter_demo.py              # CLI: 章节生成
├── run_validate_canon.py            # CLI: 正典校验
├── run_validate_volume.py           # CLI: 卷校验
├── run_full_novel_audit.py          # CLI: 全书审计
├── run_init_dynamic_state.py        # CLI: DKM 初始化
├── run_replan_volume.py             # CLI: 卷重规划
├── run_cleanup_orphan_files.py      # CLI: 孤儿文件清理
├── scan_continuity.py               # CLI: 连续性扫描
│
├── agents/                          # 33 个智能体
├── core/                            # 42 个核心模块
├── utils/                           # 工具（json_fixer / logger / type_safety）
├── data/genres/                     # 题材包 JSON
├── frontend/                        # 前端 SPA（Bootstrap 5 + Chart.js）
├── docs/                            # 文档
└── requirements.txt
```

---

## 已知限制

- **无并发控制**：`data_manager.py` 写 JSON 无文件锁，并发请求可能损坏数据
- **无 API 输入校验**：`server.py` 部分端点直接传 raw payload 给 agent
- **Module-level 副作用**：`config.py` import 时创建目录，只读环境导入会失败
- **旧 pipeline 保留**：`inkai_workflow_optimized.py`（140KB 单体）冻结保留，新流水线是推荐路径

---

## License

MIT
