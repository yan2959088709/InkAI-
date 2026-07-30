"""
章节摘要生成智能体
负责为完成的章节自动生成结构化摘要
"""

from base_agent import BaseAgent
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.type_safety import (
    safe_list_append, ensure_field_type, safe_join_list
)
import config
from utils.logger import get_logger
logger = get_logger("chapter_summary_generator")


class ChapterSummaryGenerator(BaseAgent):
    """章节摘要生成智能体"""
    
    def __init__(self):
        super().__init__("章节摘要生成智能体")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成章节摘要"""
        chapter_content = input_data.get("chapter_content", {})
        chapter_number = input_data.get("chapter_number", 1)
        novel_context = input_data.get("novel_context", {})
        previous_summaries = input_data.get("previous_summaries", [])
        
        if not chapter_content:
            return {"error": "缺少章节内容"}
        
        # 生成章节摘要
        summary_data = self._generate_chapter_summary(
            chapter_content, chapter_number, novel_context, previous_summaries
        )
        
        return {
            "success": True,
            "status": "success",
            "summary_data": summary_data
        }
    
    def _generate_chapter_summary(self, chapter_content: Dict[str, Any], 
                                chapter_number: int, novel_context: Dict[str, Any],
                                previous_summaries: List[Dict]) -> Dict[str, Any]:
        """生成详细的章节摘要"""
        try:
            # 获取章节基本信息
            title = chapter_content.get("title", f"第{chapter_number}章")
            content = chapter_content.get("content", "")
            existing_summary = chapter_content.get("summary", "")
            
            # 获取叙事阶段信息
            narrative_phase = novel_context.get("narrative_phase", {})
            phase_name = narrative_phase.get("phase", "unknown")
            phase_mission = narrative_phase.get("mission", "推进故事发展")
            
            # 获取最近几章的摘要作为上下文
            recent_context = self._format_recent_summaries(previous_summaries)
            
            # 构建摘要生成prompt
            prompt = f"""你是一名专业的小说编辑，请为以下章节生成详细的结构化摘要。

## 章节信息
章节号：第{chapter_number}章
章节标题：{title}
章节字数：{len(content)}字

## 叙事阶段
当前阶段：{phase_name}
阶段任务：{phase_mission}

## 最近章节发展
{recent_context}

## 章节内容
{content[:2000]}{'...' if len(content) > 2000 else ''}

## 已有摘要（如果存在）
{existing_summary if existing_summary else '无'}

请生成以下结构化摘要：

1. **情节摘要**（200-300字）：概括本章主要情节发展
2. **关键事件**：列出3-5个最重要的事件
3. **角色发展**：描述主要角色在本章的变化和成长
4. **新增伏笔**：识别本章埋下的新伏笔或暗示
5. **伏笔揭示**：识别本章揭示或推进的已有伏笔
6. **情感基调**：描述本章的整体情感氛围
7. **情节推进**：说明本章对整体故事的推进作用
8. **重要对话**：摘录1-2段最重要的对话或独白
9. **场景描述**：概括主要场景和环境
10. **章节意义**：分析本章在整体故事中的重要性

请返回JSON格式：
{{
    "title": "章节标题",
    "summary": "情节摘要",
    "key_events": ["关键事件1", "关键事件2", "关键事件3"],
    "character_development": {{
        "角色名": "发展描述"
    }},
    "new_foreshadowing": ["新伏笔1", "新伏笔2"],
    "revealed_foreshadowing": ["揭示的伏笔1", "揭示的伏笔2"],
    "emotional_tone": "情感基调",
    "plot_advancement": "情节推进描述",
    "important_dialogues": [
        {{
            "speaker": "说话者",
            "content": "对话内容",
            "significance": "重要性"
        }}
    ],
    "scene_description": "场景描述",
    "chapter_significance": "章节意义",
    "word_count": {len(content)},
    "narrative_phase": "{phase_name}",
    "quality_indicators": {{
        "coherence": "连贯性评分(1-10)",
        "character_consistency": "角色一致性评分(1-10)",
        "plot_progression": "情节推进评分(1-10)",
        "emotional_impact": "情感冲击力评分(1-10)"
    }}
}}"""
            
            # 调用LLM生成摘要
            response = self.call_llm([{"role": "user", "content": prompt}])
            result = self.parse_json_response(response)
            
            if "error" in result:
                logger.error(f"章节摘要生成失败: {result['error']}")
                return self._create_fallback_summary(chapter_content, chapter_number)
            
            # 验证和完善摘要数据
            summary_data = self._validate_and_enhance_summary(result, chapter_content, chapter_number)
            
            return summary_data
            
        except Exception as e:
            logger.info(f"生成章节摘要时出错: {e}")
            return self._create_fallback_summary(chapter_content, chapter_number)
    
    def _format_recent_summaries(self, previous_summaries: List[Dict]) -> str:
        """格式化最近几章的摘要"""
        if not previous_summaries:
            return "无前序章节摘要"
        
        formatted_summaries = []
        for summary in previous_summaries[-3:]:  # 最多显示最近3章
            chapter_num = summary.get("chapter_number", "?")
            title = summary.get("title", "未知标题")
            brief_summary = summary.get("summary", "")[:100]  # 简化摘要
            
            formatted_summaries.append(f"第{chapter_num}章《{title}》: {brief_summary}...")
        
        return "\n".join(formatted_summaries)
    
    def _validate_and_enhance_summary(self, summary_data: Dict[str, Any], 
                                    chapter_content: Dict[str, Any], 
                                    chapter_number: int) -> Dict[str, Any]:
        """验证和增强摘要数据"""
        # 确保必要字段存在
        required_fields = {
            "title": chapter_content.get("title", f"第{chapter_number}章"),
            "summary": "章节摘要",
            "key_events": [],
            "character_development": {},
            "new_foreshadowing": [],
            "revealed_foreshadowing": [],
            "emotional_tone": "平静",
            "plot_advancement": "推进故事发展",
            "important_dialogues": [],
            "scene_description": "场景描述",
            "chapter_significance": "推进整体故事",
            "word_count": len(chapter_content.get("content", "")),
            "narrative_phase": "unknown"
        }
        
        # 填充缺失字段
        for field, default_value in required_fields.items():
            if field not in summary_data or not summary_data[field]:
                summary_data[field] = default_value
        
        # 添加生成时间戳
        summary_data["generated_at"] = datetime.now().isoformat()
        summary_data["chapter_number"] = chapter_number
        
        # 从原章节内容中提取额外信息
        if "key_events" in chapter_content:
            original_events = chapter_content["key_events"]
            if isinstance(original_events, list) and original_events:
                # 合并原有关键事件（使用类型安全的方法）
                existing_events = summary_data.get("key_events", [])
                if not isinstance(existing_events, list):
                    existing_events = []
                summary_data["key_events"] = list(set(existing_events + original_events))
        
        if "foreshadowing" in chapter_content:
            original_foreshadowing = chapter_content["foreshadowing"]
            if isinstance(original_foreshadowing, list) and original_foreshadowing:
                # 合并原有伏笔（使用类型安全的方法）
                existing_foreshadowing = summary_data.get("new_foreshadowing", [])
                if not isinstance(existing_foreshadowing, list):
                    existing_foreshadowing = []
                summary_data["new_foreshadowing"] = list(set(existing_foreshadowing + original_foreshadowing))
        
        return summary_data
    
    def _create_fallback_summary(self, chapter_content: Dict[str, Any], 
                                chapter_number: int) -> Dict[str, Any]:
        """创建备用摘要（当LLM生成失败时）"""
        content = chapter_content.get("content", "")
        
        return {
            "title": chapter_content.get("title", f"第{chapter_number}章"),
            "summary": chapter_content.get("summary", f"第{chapter_number}章的内容发展"),
            "key_events": chapter_content.get("key_events", ["章节主要事件"]),
            "character_development": chapter_content.get("character_development", {}),
            "new_foreshadowing": chapter_content.get("foreshadowing", []),
            "revealed_foreshadowing": [],
            "emotional_tone": "平静发展",
            "plot_advancement": "推进故事情节",
            "important_dialogues": [],
            "scene_description": "章节场景",
            "chapter_significance": "故事发展的重要环节",
            "word_count": len(content),
            "narrative_phase": "unknown",
            "generated_at": datetime.now().isoformat(),
            "chapter_number": chapter_number,
            "fallback_generated": True,
            "quality_indicators": {
                "coherence": 5,
                "character_consistency": 5,
                "plot_progression": 5,
                "emotional_impact": 5
            }
        }
