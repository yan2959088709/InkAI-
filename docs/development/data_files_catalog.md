# 项目数据文件 & 模块归属表

> 本文档记录 `data/novels/<novel_id>/` 目录下所有可能出现的数据文件，
> 以及 `core/`、根目录下与"小说生成流水线"相关的 Python 模块的归属。
>
> **目的**：让任何人（人或 AI）一眼分清：哪些文件/模块属于**当前生效的"新流水线"**，
> 哪些是**历史遗留的"旧流水线"产物**，避免误用、误删、误读。
>
> 最后更新：2026-04-24

---

## 当前生效的"新流水线"（Active）

整套流程由四个 CLI 入口编排，彼此通过磁盘文件传递数据：

```
run_init_novel.py  ──>  run_outline_demo.py  ──>  run_chapter_demo.py
                                                      │
                                                      ▼
                                        run_validate_volume.py / run_validate_canon.py
```

### 数据文件（产出 / 消费方一目了然）

| 文件 | 写入者 | 读取者 | 状态 |
|---|---|---|---|
| `metadata.json` | `run_init_novel.py` | `run_outline_demo.py`, `run_chapter_demo.py` | **Active** |
| `characters.json` | `run_init_novel.py` | `run_outline_demo.py`, `run_chapter_demo.py`, `core/canon_checker.py` | **Active** |
| `storyline.json` | `run_init_novel.py`（`--also-storyline` 经 `agents/storyline_generator.py` 展开）| `run_outline_demo.py`, `core/canon_checker.py` | **Active** |
| `canon_report.json` | `run_init_novel.py`, `run_validate_canon.py` | 人类查看 | **Active** |
| `outline/blueprint.json` | `run_outline_demo.py`（经 `core/outline_planner.py`）| `run_chapter_demo.py` | **Active** |
| `outline/volume_<N>_chapters.json` | `run_outline_demo.py`（按需扩展卷）| `run_chapter_demo.py` | **Active** |
| `chapters_demo/chapter_<N>.txt` | `run_chapter_demo.py`（经 `agents/chapter_card_writer.py`）| `run_validate_volume.py`, 人类阅读 | **Active** |
| `chapters_demo/chapter_<N>.meta.json` | 同上 | 同上 | **Active** |
| `validation/volume_<N>_report.json` | `run_validate_volume.py`（经 `agents/volume_validator.py`）| 人类查看；`--revise` 流程消费 | **Active** |
| `dynamic_state/state.json` | `run_chapter_demo.py`（经 `core/dynamic_knowledge_manager.py`，可被 `--no-dynamic-state` 关闭）| 同模块 | **Active** |

### 代码模块

| 模块 | 角色 |
|---|---|
| `run_init_novel.py` | 一键初始化新书：写 metadata/characters/storyline + 可选 `--also-storyline`、`--also-blueprint`、`--strict-canon` |
| `run_outline_demo.py` | 调 `OutlinePlanner` 出 blueprint + 卷章节卡 |
| `run_chapter_demo.py` | 调 `ChapterCardWriter` 出正文 + 元数据 |
| `run_validate_volume.py` | 调 `VolumeValidator` 出整卷质量报告 |
| `run_validate_canon.py` | 调 `core/canon_checker.py` 校验 characters↔storyline 一致性（**新**）|
| `run_replan_volume.py` | 重排某卷的章节卡（针对节奏/伏笔问题）|
| `run_init_dynamic_state.py` | 单独初始化 DKM 的 `dynamic_state/state.json` |
| `scan_continuity.py` | 启发式扫描"卡间断裂"，写 `continuity_scan.json` |
| `core/outline_planner.py` | OutlinePlanner —— 蓝图 + 章节卡生成器 |
| `core/canon_checker.py` | **新增** Canon Checker —— 6 条规则的档案一致性校验引擎 |
| `core/genre_pack.py` | 题材包系统（`data/genres/*.json`）|
| `core/dynamic_knowledge_manager.py` | DKM —— 动态知识管理（角色出场/物品/伏笔）|
| `core/volume_validator.py` | 整卷质量校验器 |
| `agents/storyline_generator.py` | 把 GenrePack 骨架展开为完整三幕剧 storyline（新流程通过 `--also-storyline` 调用）|
| `agents/chapter_card_writer.py` | 章节正文生成器，带角色档案精挑注入 |

---

## 已废弃的"旧流水线"（Deprecated / Legacy）

这些模块构成一个**完全孤立的旧子图**——彼此互相引用，但**新流水线（`run_*.py` 系列）已经完全不依赖它们**。
它们仍留在仓库中，只是为了：
1. 历史回溯：理解项目演进（部分逻辑思路有参考价值）
2. 兼容历史 novel_dir：旧小说目录里残留的产物文件不会被误读

> **不要在新代码里 import 这些模块**。如必须使用，请先评估是否能把同等能力接入"新流水线"。

### 数据文件

| 文件 | 写入者（旧流水线）| 现状 | 处理建议 |
|---|---|---|---|
| `tags.json` | `inkai_workflow_optimized.py` | 已被 `metadata.json` 中的 `tags` 字段吸收 | **可安全删除** |
| `workflow_context.json` | `inkai_workflow_optimized.py`, `workflow_context.py` | 旧 workflow 状态机的快照 | **可安全删除** |
| `character_quality_assessment.json` | `inkai_workflow_optimized.py` | 旧的 character 质量评估 | **可安全删除** |
| `storyline_quality_assessment.json` | `inkai_workflow_optimized.py` | 旧的 storyline 质量评估 | **可安全删除** |
| `continuation_storyline_quality_assessment.json` | `inkai_workflow_optimized.py` | 旧的续写质量评估 | **可安全删除** |
| `core_knowledge.json` | `core/core_knowledge_manager.py` | 旧的"核心知识"缓存（已被 characters.json + storyline.json 替代）| **可安全删除** |
| `dynamic_knowledge.json` | `core/dynamic_knowledge_graph.py` | 旧的动态知识图（已被 `dynamic_state/state.json` 替代）| **可安全删除**（注意名字相近但**不是** `dynamic_state/state.json`）|
| `foreshadowing_lifecycle.json` | `core/foreshadowing_lifecycle_manager.py` | 旧的伏笔生命周期管理（能力已被 OutlinePlanner 的全局伏笔账本覆盖）| **可安全删除** |

### 代码模块

| 模块 | 状态 | 备注 |
|---|---|---|
| `inkai_workflow_optimized.py` | **Deprecated** | 旧版状态机式 workflow 编排器，已被 `run_*.py` 取代 |
| `new_50chapters_novel_auto.py` | **Deprecated** | 旧的"50 章自动化"脚本，使用 `WorkflowContext` |
| `workflow_context.py` | **Deprecated** | 旧的 workflow 状态对象 |
| `core/core_knowledge_manager.py` | **Deprecated** | 旧的"核心知识"管理器 |
| `core/foreshadowing_lifecycle_manager.py` | **Deprecated** | 旧的伏笔生命周期管理 |
| `core/dynamic_knowledge_graph.py` | **Deprecated** | 旧的动态知识图（注意：与新流程在用的 `dynamic_knowledge_manager.py` 是两个不同的东西）|
| `core/intelligent_context_selector.py` | **Deprecated** | 旧的上下文选择器，仅被 `integrated_knowledge_system` 使用 |
| `core/integrated_knowledge_system.py` | **Deprecated** | 旧的集成知识系统 |
| `core/batch_continuation.py` | **Deprecated** | 旧的批量续写器，仅被 `inkai_workflow_optimized` 使用 |

### 一组在 `core/` 下"看起来像还在用、其实没接入新流水线"的模块

下列模块**未被任何 `run_*.py` / `agents/*.py`（新流程）import**，仅在旧 workflow 内部被引用，可视同 Deprecated 处理：

```
core/comprehensive_novel_generation_system.py
core/optimized_agent_interaction_system.py
core/unified_integration_bridge.py
core/optimization_bridge.py
core/enhanced_continuation_executor.py
core/enhanced_volume_manager.py
core/enhanced_context_builder.py
core/enhanced_character_tracker.py
core/dual_layer_storyline_manager.py
core/dual_storyline_checker.py
core/storyline_progression_planner.py
core/volume_storyline_planner.py
core/volume_connection_manager.py
core/quality_circuit_breaker.py
core/quality_validator.py
core/narrative_state_monitor.py
core/novel_planner.py
core/phase_planner.py
core/foreshadowing_recycler.py
core/rhythm_config.py
core/rhythm_keeper.py
core/rhythm_controller.py
core/sliding_window_context.py
core/intelligent_memory_manager.py
core/unified_knowledge_sync.py
core/context_slicer.py
core/fault_tolerance.py
```

> 上述模块清理建议：**先标注、不删除**。后续若确认彻底无用，可整批移入 `legacy/` 子目录。

---

## 清理工具

提供 `run_cleanup_orphan_files.py` —— 用户可选择某本小说的孤儿文件批量备份/删除，避免误操作：

```powershell
# 默认就是 dry-run：只列出会被处理的文件，不实际操作
python run_cleanup_orphan_files.py --novel-id <id>

# 真备份后删除（加 --yes 才真执行）
python run_cleanup_orphan_files.py --novel-id <id> --yes

# 不备份直接删除（不推荐）
python run_cleanup_orphan_files.py --novel-id <id> --yes --no-backup

# 干跑列出所有 novel 的孤儿
python run_cleanup_orphan_files.py --all
```

---

## 决策要点

- **数据文件清理是可选的**——保留不影响新流水线。但清理后目录更整洁，新人 onboarding 更快。
- **代码模块清理是激进的**——目前选择"标注 + 保留"的保守路线。后续如确认无用，可整批迁入 `legacy/` 子目录。
- **任何新增的 manager 或 workflow 都不要再用旧子图的命名规约**（避免与历史文件混淆）。
