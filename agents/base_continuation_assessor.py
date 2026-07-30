"""
续写评估智能体基础类
提供所有续写评估智能体的公共功能
"""

from abc import ABC, abstractmethod
from base_agent import BaseAgent
from typing import Dict, List, Any, Optional
import config
from utils.logger import get_logger
logger = get_logger("base_continuation_assessor")


class BaseContinuationAssessor(BaseAgent, ABC):
    """续写评估智能体基础类"""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理评估请求"""
        continuation_content = input_data.get("continuation_content", {})
        original_knowledge_base = input_data.get("original_knowledge_base", {})
        content_type = input_data.get("content_type", "story")
        
        if not continuation_content or not original_knowledge_base:
            return {"error": "缺少必要的评估数据"}
        
        # 调用子类实现的评估方法
        return self._assess(continuation_content, original_knowledge_base, content_type)
    
    @abstractmethod
    def _assess(self, continuation_content: Dict[str, Any], 
               knowledge_base: Dict[str, Any], 
               content_type: str) -> Dict[str, Any]:
        """子类实现的具体评估逻辑"""
        pass
    
    def _validate_assessment_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证评估结果，适配LLM的实际输出格式"""
        
        # 检查是否是LLM的实际输出格式（嵌套在evaluation对象内）
        if "evaluation" in result and isinstance(result["evaluation"], dict):
            logger.info(f"[{self.name}] 检测到LLM嵌套格式，开始转换...")
            evaluation = result["evaluation"]
            
            # 提取并转换评分数据
            converted_result = {}
            
            # 1. 转换总分（从0-10分制转为0-100分制）
            score_fields = ["character_consistency", "overall_coherence", "consistency_score",
                          "overall_score", "plot_logic", "world_consistency", 
                          "style_consistency", "reader_experience", "long_term_consistency"]
            for field in score_fields:
                if field in evaluation and isinstance(evaluation[field], (int, float)):
                    base_score = evaluation[field]
                    if base_score <= 10:
                        converted_result["overall_score"] = int(base_score * 10)
                    else:
                        converted_result["overall_score"] = int(base_score)
                    logger.info(f"[{self.name}] 转换总分: {base_score} -> {converted_result['overall_score']}")
                    break
            
            if "overall_score" not in converted_result:
                converted_result["overall_score"] = 75
            
            # 2. 转换维度评分
            dimensions = {}
            for key, value in evaluation.items():
                if isinstance(value, (int, float)) and key not in ["overall_score"]:
                    if value <= 10:
                        dimensions[key] = int(value * 10)
                    else:
                        dimensions[key] = int(value)
            
            converted_result["dimensions"] = dimensions
            
            # 3. 提取建议
            converted_result["suggestions"] = evaluation.get("suggestions", [])
            
            # 4. 构建详细分析
            detailed_analysis = {}
            for key in ["strengths", "weaknesses", "conclusion", "character_analysis",
                       "plot_analysis", "world_analysis", "style_analysis", 
                       "reader_analysis", "consistency_analysis"]:
                if key in evaluation:
                    detailed_analysis[key] = evaluation[key]
            
            converted_result["detailed_analysis"] = detailed_analysis
            
            # 使用转换后的结果
            result = converted_result
        
        # 确保必要字段存在（兜底逻辑）
        if "overall_score" not in result:
            dimensions = result.get("dimensions", {})
            if dimensions:
                total = sum(score for score in dimensions.values() if isinstance(score, (int, float)))
                count = len([score for score in dimensions.values() if isinstance(score, (int, float))])
                result["overall_score"] = total / count if count > 0 else 75
            else:
                result["overall_score"] = 75
        
        if "is_high_quality" not in result:
            result["is_high_quality"] = result.get("overall_score", 0) >= config.QUALITY_THRESHOLD
        
        if "suggestions" not in result:
            result["suggestions"] = []
        
        if "dimensions" not in result:
            result["dimensions"] = {}
        
        # 确保分数在合理范围内
        result["overall_score"] = max(0, min(100, result["overall_score"]))
        
        return result
    
    def _format_character_profiles(self, character_profiles: Dict[str, Any]) -> str:
        """格式化人物档案"""
        if not character_profiles:
            return "无人物档案"
        
        formatted = ""
        main_character = character_profiles.get("main_character", {})
        if main_character:
            basic_info = main_character.get("basic_info", {})
            personality = main_character.get("personality", {})
            background = main_character.get("background", {})
            
            formatted += f"主角：{basic_info.get('name', '未知')}\n"
            formatted += f"  年龄：{basic_info.get('age', '未知')}\n"
            formatted += f"  职业：{basic_info.get('occupation', '未知')}\n"
            formatted += f"  性格：{personality.get('description', '未知')}\n"
            formatted += f"  核心欲望：{background.get('core_desire', '未知')}\n"
            formatted += f"  主要恐惧：{background.get('fear', '未知')}\n\n"
        
        supporting_characters = character_profiles.get("supporting_characters", [])
        for char in supporting_characters:
            basic_info = char.get("basic_info", {})
            formatted += f"配角：{basic_info.get('name', '未知')} ({char.get('role', '未知角色')})\n"
            formatted += f"  性格：{char.get('personality', '未知')}\n"
            formatted += f"  与主角关系：{char.get('relationship_with_main', '未知')}\n\n"
        
        return formatted
    
    def _format_plot_lines(self, plot_lines: Dict[str, Any]) -> str:
        """格式化故事线"""
        if not plot_lines:
            return "无故事线信息"
        
        formatted = ""
        
        # 主线
        main_line = plot_lines.get("main_line", [])
        if main_line:
            formatted += "主线：\n"
            for i, line in enumerate(main_line, 1):
                formatted += f"  {i}. {line}\n"
            formatted += "\n"
        
        # 支线
        sub_lines = plot_lines.get("sub_lines", [])
        if sub_lines:
            formatted += "支线：\n"
            for i, line in enumerate(sub_lines, 1):
                formatted += f"  {i}. {line}\n"
            formatted += "\n"
        
        # 整体故事线
        overall = plot_lines.get("overall_storyline", {})
        if overall:
            formatted += f"世界观：{overall.get('world_setting', '未知')}\n"
            formatted += f"主角目标：{overall.get('main_goal', '未知')}\n"
            formatted += f"核心冲突：{overall.get('core_conflict', '未知')}\n"
        
        return formatted
    
    def _format_last_chapter(self, last_chapter: Dict[str, Any]) -> str:
        """格式化上一章信息"""
        if not last_chapter:
            return "无上一章信息"
        
        formatted = f"第{last_chapter.get('chapter_number', 0)}章：{last_chapter.get('title', '未知标题')}\n"
        formatted += f"概要：{last_chapter.get('summary', '无概要')}\n"
        
        key_events = last_chapter.get("key_events", [])
        if key_events:
            formatted += f"关键事件：{', '.join(key_events)}\n"
        
        foreshadowing = last_chapter.get("foreshadowing", [])
        if foreshadowing:
            formatted += f"伏笔：{', '.join(foreshadowing)}\n"
        
        next_hint = last_chapter.get("next_chapter_hint", "")
        if next_hint:
            formatted += f"下章预告：{next_hint}\n"
        
        return formatted
    
    def _format_world_setting(self, world_setting: Any) -> str:
        """格式化世界观设定"""
        if not world_setting:
            return "无世界观设定"
        
        if isinstance(world_setting, str):
            return world_setting
        
        if isinstance(world_setting, dict):
            formatted = ""
            formatted += f"时代：{world_setting.get('time_period', '未知')}\n"
            formatted += f"地点：{world_setting.get('location', '未知')}\n"
            formatted += f"社会：{world_setting.get('society', '未知')}\n"
            formatted += f"氛围：{world_setting.get('atmosphere', '未知')}\n"
            return formatted
        
        return str(world_setting)
