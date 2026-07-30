"""
续写世界观一致性专项评估智能体
专门评估续写内容中世界观的一致性
"""

from agents.base_continuation_assessor import BaseContinuationAssessor
from typing import Dict, List, Any, Optional
import config


class ContinuationWorldConsistencyAssessor(BaseContinuationAssessor):
    """续写世界观一致性专项评估智能体"""
    
    def __init__(self):
        super().__init__("续写世界观一致性专项评估智能体")
    
    def _assess(self, continuation_content: Dict[str, Any], 
               knowledge_base: Dict[str, Any], 
               content_type: str) -> Dict[str, Any]:
        """评估世界观一致性"""
        try:
            if content_type == "story":
                return self._assess_story_world_consistency(continuation_content, knowledge_base)
            elif content_type == "storyline":
                return self._assess_storyline_world_consistency(continuation_content, knowledge_base)
            else:
                return self._assess_general_world_consistency(continuation_content, knowledge_base)
                
        except Exception as e:
            self.log(f"世界观一致性评估失败: {e}")
            return {
                "is_high_quality": False,
                "overall_score": 0,
                "dimensions": {},
                "suggestions": [f"评估过程出错: {str(e)}"]
            }
    
    def _assess_story_world_consistency(self, chapter_content: Dict[str, Any], 
                                      knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事内容中的世界观一致性"""
        content = chapter_content.get("content", "")
        world_setting = knowledge_base.get("world_setting", "")
        story_tone = knowledge_base.get("story_tone", "")
        
        prompt = f"""
        请专门评估以下续写章节中世界观的一致性，重点关注以下维度：
        
        原文世界观设定：
        {self._format_world_setting(world_setting)}
        
        故事基调：
        {story_tone}
        
        续写章节内容：
        {content[:3000]}
        
        请从以下维度评估世界观一致性（每项0-100分）：
        1. 世界规则一致性：是否符合原文的世界规则和设定
        2. 社会制度一致性：社会制度描述是否与原文一致
        3. 地理环境一致性：地理环境描述是否与原文一致
        4. 历史背景一致性：历史背景是否与原文一致
        5. 文化设定一致性：文化设定是否与原文一致
        
        请返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的世界观设定编辑，擅长评估续写内容中世界观的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_storyline_world_consistency(self, storyline_content: Dict[str, Any], 
                                          knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事线中的世界观一致性"""
        world_setting = knowledge_base.get("world_setting", "")
        story_tone = knowledge_base.get("story_tone", "")
        
        prompt = f"""
        请评估以下续写故事线中世界观设定的一致性：
        
        原文世界观设定：
        {self._format_world_setting(world_setting)}
        
        故事基调：
        {story_tone}
        
        续写故事线：
        {str(storyline_content)[:2000]}
        
        请评估故事线中世界观设定的一致性和合理性，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事编辑，擅长评估故事线中世界观设定的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_general_world_consistency(self, content: Dict[str, Any], 
                                        knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """通用世界观一致性评估"""
        world_setting = knowledge_base.get("world_setting", "")
        story_tone = knowledge_base.get("story_tone", "")
        
        prompt = f"""
        请评估以下续写内容中世界观的一致性：
        
        原文世界观设定：
        {self._format_world_setting(world_setting)}
        
        故事基调：
        {story_tone}
        
        续写内容：
        {str(content)[:2000]}
        
        请进行综合世界观一致性评估，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的内容编辑，擅长评估续写内容中世界观的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
