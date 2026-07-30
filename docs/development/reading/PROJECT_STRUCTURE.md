# InkAI 小说创作系统 - 项目结构

## 📁 项目目录结构

```
InkAI/
├── agents/                          # 智能体模块
│   ├── base_agent.py               # 基础智能体类
│   ├── tag_selector.py             # 标签选择智能体
│   ├── character_creator.py        # 角色创建智能体
│   ├── character_improver.py       # 角色改进智能体
│   ├── storyline_generator.py      # 故事线生成智能体
│   ├── storyline_improver.py       # 故事线改进智能体
│   ├── chapter_writer.py           # 章节写作智能体
│   ├── quality_assessor.py         # 质量评估智能体
│   ├── novel_continuation_agent.py # 小说续写智能体
│   ├── continuation_storyline_generator.py # 续写故事线生成
│   ├── continuation_chapter_writer.py      # 续写章节写作
│   ├── continuation_quality_assessor.py    # 续写质量评估
│   └── novel_storyline_improver.py  # 小说故事线改进
├── data/                           # 数据存储目录
│   ├── novels/                     # 小说数据
│   └── knowledge_graphs/           # 知识图谱
├── docs/                           # 文档目录
│   ├── InkAI完整文档.md
│   ├── InkAI逻辑思路文档.md
│   ├── WEB_README.md
│   ├── 使用说明.md
│   ├── 智能体交互优化分析报告.md
│   ├── 智能体交互优化实施报告.md
│   ├── 智能体创作需求接收检查报告.md
│   └── 续写功能说明.md
├── frontend/                       # 前端文件
│   ├── index.html                  # 主页面
│   ├── app.js                      # 前端逻辑
│   └── styles.css                  # 样式文件
├── templates/                      # 模板目录（空）
├── app.py                          # Flask Web服务器
├── base_agent.py                   # 基础智能体类
├── config.py                       # 配置文件
├── data_manager.py                 # 数据管理器
├── inkai_workflow_optimized.py     # 优化的工作流程
├── workflow_context.py             # 工作流上下文
├── main.py                         # 主程序入口
├── start_web.py                    # Web服务器启动脚本
├── repair_data.py                  # 数据修复工具
├── requirements.txt                # Python依赖
├── README.md                       # 项目说明
└── PROJECT_STRUCTURE.md            # 项目结构说明（本文件）
```

## 🔧 核心模块说明

### 1. 智能体系统 (agents/)
- **BaseAgent**: 所有智能体的基类，提供LLM调用、JSON解析等基础功能
- **TagSelectorAgent**: 根据用户需求推荐和选择标签
- **CharacterCreatorAgent**: 创建主要角色和配角
- **StorylineGeneratorAgent**: 生成整体故事线和第一个模块
- **ChapterWriterAgent**: 根据故事线生成具体章节内容
- **QualityAssessorAgent**: 评估生成内容的质量

### 2. 工作流程 (inkai_workflow_optimized.py)
- **InkAIWorkflowOptimized**: 主要的工作流程控制器
- 协调各个智能体的工作
- 管理数据流转和状态

### 3. 数据管理 (data_manager.py)
- **DataManager**: 数据持久化管理
- 支持小说数据的保存、加载、更新
- 自动标准化数据格式，防止JSON解析错误

### 4. Web服务 (app.py)
- Flask RESTful API服务器
- 提供前端所需的所有API接口
- 支持小说创作、续写、质量评估等功能

### 5. 前端界面 (frontend/)
- 单页应用(SPA)设计
- 响应式界面，支持各种设备
- 实时显示创作进度和结果

## 🚀 快速开始

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

2. **启动Web服务器**:
   ```bash
   python start_web.py
   ```

3. **访问应用**:
   打开浏览器访问 `http://localhost:5000`

## 📝 主要功能

- ✅ 智能标签选择
- ✅ 角色创建和改进
- ✅ 故事线生成和改进
- ✅ 章节内容创作
- ✅ 质量评估
- ✅ 小说续写
- ✅ 数据格式标准化
- ✅ 错误处理和重试机制

## 🔄 数据流程

1. 用户输入需求 → 标签选择
2. 标签 + 需求 → 角色创建
3. 角色 + 标签 → 故事线生成
4. 故事线 + 角色 → 章节写作
5. 生成内容 → 质量评估
6. 评估结果 → 用户确认/改进

## 🛠️ 技术栈

- **后端**: Python, Flask, ZhipuAI API
- **前端**: HTML5, CSS3, JavaScript, Bootstrap
- **数据存储**: JSON文件系统
- **AI模型**: 智谱AI大语言模型

## 📊 项目状态

- ✅ 核心功能完整
- ✅ 数据格式问题已解决
- ✅ 错误处理完善
- ✅ 代码结构优化
- ✅ 文档整理完成
