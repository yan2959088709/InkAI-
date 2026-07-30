"""
续写读者体验专项评估智能体
专门评估续写内容的读者体验
"""

from agents.base_continuation_assessor import BaseContinuationAssessor
from typing import Dict, List, Any, Optional
import config


class ContinuationReaderExperienceAssessor(BaseContinuationAssessor):
    """续写读者体验专项评估智能体"""
    
    def __init__(self):
        super().__init__("续写读者体验专项评估智能体")
    
    def _assess(self, continuation_content: Dict[str, Any], 
               knowledge_base: Dict[str, Any], 
               content_type: str) -> Dict[str, Any]:
        """评估读者体验"""
        try:
            if content_type == "story":
                return self._assess_story_reader_experience(continuation_content, knowledge_base)
            elif content_type == "storyline":
                return self._assess_storyline_reader_experience(continuation_content, knowledge_base)
            else:
                return self._assess_general_reader_experience(continuation_content, knowledge_base)
                
        except Exception as e:
            self.log(f"读者体验评估失败: {e}")
            return {
                "is_high_quality": False,
                "overall_score": 0,
                "dimensions": {},
                "suggestions": [f"评估过程出错: {str(e)}"]
            }
    
    def _assess_story_reader_experience(self, chapter_content: Dict[str, Any], 
                                      knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事内容的读者体验"""
        content = chapter_content.get("content", "")
        story_tone = knowledge_base.get("story_tone", "")
        target_audience = knowledge_base.get("target_audience", "")
        
        prompt = f"""
        请专门评估以下续写章节的读者体验，重点关注以下维度：
        
        故事基调：
        {story_tone}
        
        目标读者：
        {target_audience}
        
        续写章节内容：
        {content[:3000]}
        
        请从以下维度评估读者体验（每项0-100分）：
        1. 阅读流畅度：内容是否流畅易读，无阅读障碍
        2. 情感共鸣度：是否能引起读者的情感共鸣
        3. 悬念设置：悬念设置是否吸引读者继续阅读
        4. 节奏控制：节奏控制是否合适，不会让读者感到疲劳
        5. 期待值管理：是否满足读者的期待，同时创造新的期待
        
        请返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的读者体验编辑，擅长评估续写内容的读者体验。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_storyline_reader_experience(self, storyline_content: Dict[str, Any], 
                                          knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事线的读者体验"""
        story_tone = knowledge_base.get("story_tone", "")
        target_audience = knowledge_base.get("target_audience", "")
        
        prompt = f"""
        请评估以下续写故事线的读者体验：
        
        故事基调：
        {story_tone}
        
        目标读者：
        {target_audience}
        
        续写故事线：
        {str(storyline_content)[:2000]}
        
        请评估故事线的读者体验和吸引力，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事编辑，擅长评估故事线的读者体验。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_general_reader_experience(self, content: Dict[str, Any], 
                                        knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """通用读者体验评估"""
        story_tone = knowledge_base.get("story_tone", "")
        target_audience = knowledge_base.get("target_audience", "")
        
        prompt = f"""
        请评估以下续写内容的读者体验：
        
        故事基调：
        {story_tone}
        
        目标读者：
        {target_audience}
        
        续写内容：
        {str(content)[:2000]}
        
        请进行综合读者体验评估，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的内容编辑，擅长评估续写内容的读者体验。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
