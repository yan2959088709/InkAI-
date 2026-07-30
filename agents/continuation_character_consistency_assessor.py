"""
续写人物一致性专项评估智能体
专门评估续写内容中人物的一致性
"""

from agents.base_continuation_assessor import BaseContinuationAssessor
from typing import Dict, List, Any, Optional
import config


class ContinuationCharacterConsistencyAssessor(BaseContinuationAssessor):
    """续写人物一致性专项评估智能体"""
    
    def __init__(self):
        super().__init__("续写人物一致性专项评估智能体")
    
    def _assess(self, continuation_content: Dict[str, Any], 
               knowledge_base: Dict[str, Any], 
               content_type: str) -> Dict[str, Any]:
        """评估人物一致性"""
        try:
            if content_type == "story":
                return self._assess_story_character_consistency(continuation_content, knowledge_base)
            elif content_type == "storyline":
                return self._assess_storyline_character_consistency(continuation_content, knowledge_base)
            else:
                return self._assess_general_character_consistency(continuation_content, knowledge_base)
                
        except Exception as e:
            self.log(f"人物一致性评估失败: {e}")
            return {
                "is_high_quality": False,
                "overall_score": 0,
                "dimensions": {},
                "suggestions": [f"评估过程出错: {str(e)}"]
            }
    
    def _assess_story_character_consistency(self, chapter_content: Dict[str, Any], 
                                          knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事内容中的人物一致性"""
        content = chapter_content.get("content", "")
        character_profiles = knowledge_base.get("character_profiles", {})
        
        # 构建评估提示
        prompt = f"""
        请专门评估以下续写章节中人物的一致性，重点关注以下维度：
        
        原文人物设定：
        {self._format_character_profiles(character_profiles)}
        
        续写章节内容：
        {content[:3000]}
        
        请从以下维度评估人物一致性（每项0-100分）：
        1. 性格一致性：人物性格特征是否与原文设定一致
        2. 行为逻辑一致性：人物行为是否符合其性格和背景
        3. 语言风格一致性：人物语言风格是否与原文一致
        4. 关系发展合理性：人物关系发展是否合理
        5. 成长轨迹连贯性：人物成长是否符合发展轨迹
        
        请返回JSON格式：
        {{
            "overall_score": 85,
            "dimensions": {{
                "personality_consistency": 90,
                "behavior_logic_consistency": 85,
                "language_style_consistency": 80,
                "relationship_development_consistency": 85,
                "growth_trajectory_consistency": 85
            }},
            "is_high_quality": true,
            "suggestions": [
                "人物性格表现符合原设定",
                "行为逻辑合理",
                "建议加强语言风格统一性"
            ],
            "detailed_analysis": {{
                "personality_analysis": "人物性格表现分析...",
                "behavior_analysis": "行为逻辑分析...",
                "language_analysis": "语言风格分析...",
                "relationship_analysis": "关系发展分析...",
                "growth_analysis": "成长轨迹分析..."
            }}
        }}
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的人物设定编辑，擅长评估续写内容中人物的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        # 验证和补充结果
        return self._validate_assessment_result(result)
    
    def _assess_storyline_character_consistency(self, storyline_content: Dict[str, Any], 
                                              knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事线中的人物一致性"""
        character_profiles = knowledge_base.get("character_profiles", {})
        
        prompt = f"""
        请评估以下续写故事线中人物设定的一致性：
        
        原文人物设定：
        {self._format_character_profiles(character_profiles)}
        
        续写故事线：
        {str(storyline_content)[:2000]}
        
        请评估故事线中人物设定的一致性和合理性，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事编辑，擅长评估故事线中人物设定的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_general_character_consistency(self, content: Dict[str, Any], 
                                            knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """通用人物一致性评估"""
        character_profiles = knowledge_base.get("character_profiles", {})
        
        prompt = f"""
        请评估以下续写内容中人物的一致性：
        
        原文人物设定：
        {self._format_character_profiles(character_profiles)}
        
        续写内容：
        {str(content)[:2000]}
        
        请进行综合人物一致性评估，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的内容编辑，擅长评估续写内容中人物的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
