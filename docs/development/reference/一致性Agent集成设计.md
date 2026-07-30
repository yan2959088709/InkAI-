# 一致性Agent集成设计文档

## 设计目标

在续写流程中集成12个一致性Agent，实现多维度一致性检查和自动改进机制。

## Agent列表

### 评估Agent（6个）
1. **ContinuationCharacterConsistencyAssessor** - 人物一致性评估
2. **ContinuationPlotLogicAssessor** - 情节逻辑评估
3. **ContinuationWorldConsistencyAssessor** - 世界观一致性评估
4. **ContinuationStyleConsistencyAssessor** - 风格一致性评估
5. **ContinuationReaderExperienceAssessor** - 读者体验评估
6. **ContinuationLongTermConsistencyAssessor** - 长期一致性评估

### 改进Agent（6个）
1. **ContinuationCharacterConsistencyImprover** - 人物一致性改进
2. **ContinuationPlotLogicImprover** - 情节逻辑改进
3. **ContinuationWorldConsistencyImprover** - 世界观一致性改进
4. **ContinuationStyleConsistencyImprover** - 风格一致性改进
5. **ContinuationReaderExperienceImprover** - 读者体验改进
6. **ContinuationLongTermConsistencyImprover** - 长期一致性改进

## 集成流程设计

### 故事线生成后的评估流程

```
generate_continuation_storyline()
  └─> assess_continuation_quality("storyline")  # 通用质量评估
  └─> [NEW] 专项一致性评估（如果质量不达标）
      ├─> ContinuationCharacterConsistencyAssessor
      ├─> ContinuationPlotLogicAssessor
      ├─> ContinuationWorldConsistencyAssessor
      ├─> ContinuationStyleConsistencyAssessor
      ├─> ContinuationReaderExperienceAssessor
      └─> ContinuationLongTermConsistencyAssessor
  └─> [NEW] 根据评估结果决定是否改进
      └─> 如果发现问题，调用对应的改进Agent
```

### 章节生成后的评估流程

```
write_continuation_chapter()
  └─> assess_continuation_quality("story")  # 通用质量评估
  └─> [NEW] 专项一致性评估（如果质量不达标）
      ├─> ContinuationCharacterConsistencyAssessor
      ├─> ContinuationPlotLogicAssessor
      ├─> ContinuationWorldConsistencyAssessor
      ├─> ContinuationStyleConsistencyAssessor
      ├─> ContinuationReaderExperienceAssessor
      └─> ContinuationLongTermConsistencyAssessor
  └─> [NEW] 根据评估结果决定是否改进
      └─> 如果发现问题，调用对应的改进Agent
```

## 评估Agent输入数据格式

```python
input_data = {
    "continuation_content": {
        # 章节内容或故事线
        "content": "...",
        "title": "...",
        # 其他字段
    },
    "original_knowledge_base": {
        # 原始知识库（从continuation_data获取）
        "character_profiles": {...},
        "plot_lines": {...},
        "world_setting": {...},
        # 需要整合核心知识库
    },
    "content_type": "story"  # 或 "storyline"
}
```

## 改进Agent输入数据格式

```python
input_data = {
    "continuation_content": {
        # 需要改进的内容
    },
    "quality_assessment": {
        # 对应的评估结果
        "overall_score": 75,
        "dimensions": {...},
        "suggestions": [...]
    },
    "knowledge_base": {
        # 知识库
    },
    "user_requirements": "..."
}
```

## 评估结果汇总

```python
consistency_assessments = {
    "character": {
        "overall_score": 85,
        "is_high_quality": True,
        "dimensions": {...},
        "suggestions": [...]
    },
    "plot_logic": {...},
    "world": {...},
    "style": {...},
    "reader_experience": {...},
    "long_term": {...}
}
```

## 改进决策逻辑

```python
def should_improve(assessment_result):
    """判断是否需要改进"""
    overall_score = assessment_result.get("overall_score", 100)
    is_high_quality = assessment_result.get("is_high_quality", True)
    
    # 如果总分低于80或标记为低质量，需要改进
    return overall_score < 80 or not is_high_quality
```

## 集成位置

1. **故事线生成后**: 在 `generate_continuation_storyline()` 中，在 `assess_continuation_quality()` 之后
2. **章节生成后**: 在 `write_continuation_chapter()` 中，在 `assess_continuation_quality()` 之后

## 性能考虑

- 可以使用并行处理来同时运行多个评估Agent
- 可以使用缓存来避免重复评估
- 可以根据质量评估结果决定是否进行专项评估（如果通用评估已经通过，可以跳过）

## 测试要求

- [ ] 测试6个评估Agent的调用
- [ ] 测试评估结果的汇总
- [ ] 测试改进决策逻辑
- [ ] 测试6个改进Agent的调用
- [ ] 测试自动改进机制
- [ ] 测试完整流程

