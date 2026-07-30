# InkAI 项目结构

## 顶层目录

```
InkAI/
├── server.py                        # Web 服务入口（Flask，端口 5000）
├── base_agent.py                    # 智能体基类（LLM 调用 + 缓存诊断）
├── config.py                        # 多 provider 配置（dashscope/deepseek/openai）
├── data_manager.py                  # 数据持久化（JSON 文件）
├── workflow_context.py              # 工作流上下文
├── inkai_workflow_optimized.py      # 旧 pipeline（冻结保留，不推荐）
├── requirements.txt                 # Python 依赖
│
├── run_*.py                         # 新 pipeline CLI 脚本（11 个）
├── scan_continuity.py               # 跨章连续性扫描
│
├── agents/                          # 智能体（33 个 .py）
├── core/                            # 核心模块（42 个 .py）
├── utils/                           # 工具模块
├── data/                            # 数据目录
│   └── genres/                      # 题材包 JSON
├── frontend/                        # 前端 SPA
├── docs/                            # 文档
├── templates/                       # 模板
├── optimization/                    # 优化相关
├── performance/                     # 性能相关
├── scripts/                         # 脚本
└── workflows/                       # 工作流配置
```

## CLI 脚本（新 pipeline）

| 脚本 | 功能 | 输出 |
|------|------|------|
| `run_init_novel.py` | 初始化小说（元信息 + 人物 + 故事线） | `metadata.json` + `characters.json` + `storyline.json` |
| `run_outline_demo.py` | 蓝图 + 卷章节卡 | `outline/blueprint.json` + `outline/volume_*_chapters.json` |
| `run_chapter_demo.py` | 章节生成（支持批量） | `chapters_demo/chapter_*.txt` + `.meta.json` |
| `run_validate_canon.py` | 正典校验（人物/故事线一致性） | `canon_report.json` |
| `run_validate_volume.py` | 卷校验 | `validation/volume_*_report.json` |
| `run_full_novel_audit.py` | 全书 6 维审计 | `audit_report.json` |
| `run_init_dynamic_state.py` | DKM 初始化 | `dynamic_state/state.json` |
| `run_replan_volume.py` | 卷重规划 | 更新 `outline/volume_*_chapters.json` |
| `run_cleanup_orphan_files.py` | 孤儿文件清理 | - |
| `scan_continuity.py` | 跨章断点扫描 | 终端输出 |

## agents/ 目录（33 个智能体）

### 创作类（10 个）
- `tag_selector.py` - 标签选择
- `character_creator.py` - 人物创建
- `storyline_generator.py` - 故事线生成
- `chapter_writer.py` - 旧版章节写作
- `chapter_card_writer.py` - **新版章节卡写作（推荐）**
- `chapter_summary_generator.py` - 章节摘要
- `enhanced_storyline_generator.py` - 增强故事线
- `enhanced_character_analyzer.py` - 增强人物分析
- `genre_pack_generator.py` - 题材包生成
- `simplified_writer_agent.py` - 简化写作
- `volume_validator.py` - 卷校验
- `character_improver.py` - 人物改进
- `novel_storyline_improver.py` - 故事线改进

### 续写类（4 个）
- `novel_continuation_agent.py` - 续写编排
- `continuation_storyline_generator.py` - 续写故事线
- `continuation_chapter_writer.py` - 续写章节
- `continuation_chapter_improver.py` - 续写改进

### 评估类（7 个）
- `continuation_quality_assessor.py` - 质量评估
- `continuation_character_consistency_assessor.py` - 人物一致性
- `continuation_plot_logic_assessor.py` - 情节逻辑
- `continuation_world_consistency_assessor.py` - 世界观一致性
- `continuation_style_consistency_assessor.py` - 风格一致性
- `continuation_reader_experience_assessor.py` - 读者体验
- `continuation_long_term_consistency_assessor.py` - 长期一致性

### 改进类（6 个）
- `continuation_character_consistency_improver.py`
- `continuation_plot_logic_improver.py`
- `continuation_world_consistency_improver.py`
- `continuation_style_consistency_improver.py`
- `continuation_reader_experience_improver.py`
- `continuation_long_term_consistency_improver.py`

### 基类（2 个）
- `base_continuation_assessor.py` - 评估基类
- `base_continuation_improver.py` - 改进基类

## core/ 目录（42 个核心模块）

### 规划与写作
- `outline_planner.py` - 蓝图 + 卷章节卡规划
- `novel_planner.py` - 小说规划
- `phase_planner.py` - 阶段规划
- `volume_storyline_planner.py` - 卷故事线规划
- `storyline_progression_planner.py` - 故事线推进

### 题材与规则
- `genre_pack.py` - 题材包系统

### 知识管理
- `dynamic_knowledge_manager.py` - 动态知识管理（DKM）
- `dynamic_knowledge_graph.py` - 动态知识图谱
- `core_knowledge_manager.py` - 核心知识库
- `intelligent_memory_manager.py` - 智能记忆管理
- `integrated_knowledge_system.py` - 集成知识系统
- `unified_knowledge_sync.py` - 知识同步
- `intelligent_context_selector.py` - 上下文选择

### 上下文构建
- `enhanced_context_builder.py` - 增强上下文构建
- `sliding_window_context.py` - 滑动窗口
- `context_slicer.py` - 上下文切片

### 卷与节奏
- `volume_manager.py` - 分卷管理
- `enhanced_volume_manager.py` - 增强分卷
- `volume_connection_manager.py` - 卷间关联
- `rhythm_config.py` / `rhythm_controller.py` / `rhythm_keeper.py` - 节奏控制

### 伏笔
- `foreshadowing_lifecycle_manager.py` - 伏笔生命周期
- `foreshadowing_recycler.py` - 伏笔回收

### 校验
- `canon_checker.py` - 正典校验
- `dual_storyline_checker.py` - 双线检查
- `quality_validator.py` - 质量校验
- `full_novel_auditor.py` - 全书审计

### 容错与限流
- `fault_tolerance.py` - 容错
- `quality_circuit_breaker.py` - 质量熔断
- `api_rate_limiter.py` - LLM 速率限制（2 并发 + 1s 间隔）

### 跨章去重
- `cross_chapter_dedup.py` - 跨章句式去重

### Embedding 与向量
- `embedding_service.py` - Embedding 服务
- `vector_database.py` - 向量库

### 其他
- `batch_continuation.py` - 批量续写（依赖旧 pipeline）
- `optimization_bridge.py` - 优化桥接（依赖旧 pipeline）
- `enhanced_continuation_executor.py` - 增强续写执行
- `comprehensive_novel_generation_system.py` - 综合生成系统
- `narrative_state_monitor.py` - 叙事状态监控
- `optimized_agent_interaction_system.py` - 优化交互
- `unified_integration_bridge.py` - 统一集成桥接
- `dual_layer_storyline_manager.py` - 双层故事线管理

## 数据目录结构

```
data/
├── genres/                          # 题材包 JSON
│   ├── xianxia.json
│   ├── urban.json
│   └── ...
└── novels/                          # 运行时生成
    └── <novel_id>/
        ├── metadata.json
        ├── characters.json
        ├── storyline.json
        ├── annotations.json
        ├── outline/
        │   ├── blueprint.json
        │   └── volume_<N>_chapters.json
        ├── chapters_demo/
        │   ├── chapter_<N>.txt
        │   └── chapter_<N>.meta.json
        ├── dynamic_state/
        │   └── state.json
        └── validation/
            └── volume_<N>_report.json
```
