# InkAI 上千章小说创作使用指南

## 一、快速开始

### 1. 创建新小说

```python
from inkai_workflow_optimized import InkAIWorkflowOptimized

# 初始化工作流
workflow = InkAIWorkflowOptimized()

# 创建小说
result = workflow.start_new_novel(
    user_requirements="我想写一本都市异能长篇小说，目标1000章...",
    title="透视人生"
)

# 选择标签
workflow.select_tags()

# 创建人物
workflow.create_characters()

# 生成故事线
workflow.generate_storyline()

# 写第1章
workflow.write_first_chapter()
```

---

## 二、单章续写

### 方法1：使用工作流直接续写

```python
from inkai_workflow_optimized import InkAIWorkflowOptimized
from workflow_context import WorkflowContext
from data_manager import DataManager

novel_id = "your_novel_id"

# 初始化
workflow = InkAIWorkflowOptimized()
workflow.context = WorkflowContext(novel_id)
workflow.context.load_context(novel_id)

# 加载数据
dm = DataManager()
storyline = dm.load_novel_data(novel_id, "storyline")
characters = dm.load_novel_data(novel_id, "characters")
tags = dm.load_novel_data(novel_id, "tags")

workflow.context.set_storyline(storyline)
workflow.context.set_characters(characters)
workflow.context.set_tags(tags)
workflow.context.is_continuation = True

workflow.context.continuation_data = {
    "knowledge_base": {
        "character_profiles": characters or {},
        "plot_lines": storyline or {},
        "chapters": dm.get_chapters(novel_id),
        "tags": tags or {}
    },
    "status": "initialized"
}

# 生成故事线
workflow.generate_continuation_storyline(novel_id)

# 写作章节
workflow.write_continuation_chapter(novel_id)

# 保存章节
workflow.save_continuation_chapter(novel_id)
```

---

## 三、批量续写（推荐用于长篇）

### 方法1：批量续写指定章数

```python
from core.batch_continuation import BatchContinuationManager

novel_id = "your_novel_id"

# 创建批量续写管理器
manager = BatchContinuationManager()

# 批量续写10章
result = manager.batch_continue(
    novel_id=novel_id,
    num_chapters=10
)

# 批量续写50章
result = manager.batch_continue(
    novel_id=novel_id,
    num_chapters=50
)

# 批量续写100章
result = manager.batch_continue(
    novel_id=novel_id,
    num_chapters=100
)

# 查看结果
print(f"完成: {result['completed_chapters']}/{result['total_chapters']}")
print(f"失败: {result['failed_chapters']}")
print(f"耗时: {result['elapsed_seconds']:.0f}秒")
```

### 方法2：指定起始章节

```python
# 从第100章开始，续写20章
result = manager.batch_continue(
    novel_id=novel_id,
    num_chapters=20,
    start_chapter=100
)
```

### 方法3：断点续写

```python
# 如果中途停止，可以从断点继续
result = manager.resume_batch(
    novel_id=novel_id,
    remaining_chapters=30  # 剩余要写的章节数
)
```

---

## 四、分卷管理

### 1. 查看章节所在卷

```python
from core.volume_manager import VolumeManager

manager = VolumeManager()

# 获取第100章的卷信息
volume_info = manager.get_volume_info(
    novel_id="your_novel_id",
    chapter_number=100,
    chapters_per_volume=40  # 每卷40章
)

print(f"第{volume_info['chapter_number']}章")
print(f"位于第{volume_info['volume_number']}卷")
print(f"卷内第{volume_info['chapter_in_volume']}章")
print(f"卷进度: {volume_info['volume_progress']*100:.0f}%")
```

### 2. 查看卷指导

```python
# 获取写作指导
guidance = manager.get_volume_guidance(
    novel_id="your_novel_id",
    chapter_number=100,
    chapters_per_volume=40
)

print(guidance)
```

### 3. 1000章小说分卷规划

```python
total_chapters = 1000
chapters_per_volume = 40
total_volumes = total_chapters // chapters_per_volume

print(f"总卷数: {total_volumes}")
print(f"第1卷: 第1-40章")
print(f"第2卷: 第41-80章")
# ...
print(f"第25卷: 第961-1000章")
```

---

## 五、完整示例：写1000章小说

```python
from core.batch_continuation import BatchContinuationManager
from inkai_workflow_optimized import InkAIWorkflowOptimized

# 步骤1: 创建小说
workflow = InkAIWorkflowOptimized()
result = workflow.start_new_novel(
    user_requirements="""
    我想写一本都市异能长篇小说，目标1000章。
    
    核心设定：
    1. 主角林澈，23岁古玩店学徒，获得透视异能
    2. 核心冲突：古玩界的黑暗势力vs正义的守护者
    3. 明线：主角利用异能揭露古玩造假和阴谋
    4. 暗线：十二年前妹妹受伤的真相、双玉扳指的秘密
    
    写作要求：
    1. 双层故事线：明线是古玩鉴定冒险，暗线是家族秘密
    2. 每章3000-4000字
    3. 节奏：3章循环（强推/缓冲/转折）
    4. 伏笔分层：短伏笔3章回收，中伏笔20章回收，长伏笔全书回收
    """,
    title="透视人生"
)

novel_id = result["novel_id"]
print(f"小说创建成功: {novel_id}")

# 步骤2: 初始化小说
workflow.select_tags()
workflow.create_characters()
workflow.generate_storyline()
workflow.write_first_chapter()

# 步骤3: 批量续写
manager = BatchContinuationManager()

# 先写10章试试
result = manager.batch_continue(novel_id, num_chapters=10)
print(f"前10章完成: {result['completed_chapters']}章")

# 继续写90章（累计100章）
result = manager.resume_batch(novel_id, remaining_chapters=90)
print(f"累计100章完成")

# 继续写到1000章
result = manager.resume_batch(novel_id, remaining_chapters=900)
print(f"累计1000章完成!")
```

---

## 六、进度查看

### 查看批量续写进度

```python
from core.batch_continuation import BatchContinuationManager

manager = BatchContinuationManager()
progress = manager.load_progress("your_novel_id")

if progress:
    print(f"上次写到: 第{progress['last_chapter']}章")
    print(f"完成: {progress['result']['completed_chapters']}章")
    print(f"失败: {progress['result']['failed_chapters']}章")
```

### 查看所有卷摘要

```python
from core.volume_manager import VolumeManager

manager = VolumeManager()
summaries = manager.get_all_volume_summaries("your_novel_id")

for summary in summaries:
    print(f"第{summary['volume_number']}卷: {summary['chapters_count']}章")
```

---

## 七、注意事项

### 1. 时间估算
- 每章约3-5分钟
- 100章约5-8小时
- 1000章约50-80小时

### 2. 成本估算
- 每章约3-4次LLM调用
- 1000章约3000-4000次API调用

### 3. 建议分批写
```python
# 建议每天写50-100章
result = manager.batch_continue(novel_id, num_chapters=50)
```

### 4. 断点续写
- 支持随时停止和继续
- 自动保存进度

---

## 八、问题排查

### 1. 如果批量续写失败

```python
# 检查失败章节
result = manager.batch_continue(novel_id, num_chapters=10)
if result['failed_chapters'] > 0:
    print(f"失败章节: {result['failed_chapter_list']}")
```

### 2. 如果字数不足

检查 `agents/continuation_chapter_writer.py` 中的prompt字数要求。

### 3. 如果剧情重复

检查上一章结尾是否正确传递（2500字）。
