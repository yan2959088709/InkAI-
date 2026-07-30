"""
续写语言风格专项评估智能体
专门评估续写内容中语言风格的一致性
"""

from agents.base_continuation_assessor import BaseContinuationAssessor
from typing import Dict, List, Any, Optional
import config


class ContinuationStyleConsistencyAssessor(BaseContinuationAssessor):
    """续写语言风格专项评估智能体"""
    
    def __init__(self):
        super().__init__("续写语言风格专项评估智能体")
    
    def _assess(self, continuation_content: Dict[str, Any], 
               knowledge_base: Dict[str, Any], 
               content_type: str) -> Dict[str, Any]:
        """评估语言风格一致性"""
        try:
            if content_type == "story":
                return self._assess_story_style_consistency(continuation_content, knowledge_base)
            elif content_type == "storyline":
                return self._assess_storyline_style_consistency(continuation_content, knowledge_base)
            else:
                return self._assess_general_style_consistency(continuation_content, knowledge_base)
                
        except Exception as e:
            self.log(f"语言风格一致性评估失败: {e}")
            return {
                "is_high_quality": False,
                "overall_score": 0,
                "dimensions": {},
                "suggestions": [f"评估过程出错: {str(e)}"]
            }
    
    def _assess_story_style_consistency(self, chapter_content: Dict[str, Any], 
                                      knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事内容中的语言风格一致性"""
        content = chapter_content.get("content", "")
        story_tone = knowledge_base.get("story_tone", "")
        original_chapters = knowledge_base.get("chapters", [])
        
        # 获取原文样本
        original_sample = self._get_original_style_sample(original_chapters)
        
        prompt = f"""
        请专门评估以下续写章节中语言风格的一致性，重点关注以下维度：
        
        原文故事基调：
        {story_tone}
        
        原文语言风格样本：
        {original_sample}
        
        续写章节内容：
        {content[:3000]}
        
        请从以下维度评估语言风格一致性（每项0-100分）：
        1. 语言风格一致性：语言风格是否与原文保持一致
        2. 文笔质量：文笔质量是否达到原文水平
        3. 修辞手法运用：修辞手法的运用是否与原文一致
        4. 节奏感控制：节奏感控制是否与原文一致
        5. 情感表达方式：情感表达方式是否与原文一致
        
        请返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的语言风格编辑，擅长评估续写内容中语言风格的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_storyline_style_consistency(self, storyline_content: Dict[str, Any], 
                                          knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事线中的语言风格一致性"""
        story_tone = knowledge_base.get("story_tone", "")
        
        prompt = f"""
        请评估以下续写故事线中语言风格的一致性：
        
        原文故事基调：
        {story_tone}
        
        续写故事线：
        {str(storyline_content)[:2000]}
        
        请评估故事线中语言风格的一致性和合理性，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事编辑，擅长评估故事线中语言风格的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_general_style_consistency(self, content: Dict[str, Any], 
                                        knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """通用语言风格一致性评估"""
        story_tone = knowledge_base.get("story_tone", "")
        
        prompt = f"""
        请评估以下续写内容中语言风格的一致性：
        
        原文故事基调：
        {story_tone}
        
        续写内容：
        {str(content)[:2000]}
        
        请进行综合语言风格一致性评估，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的内容编辑，擅长评估续写内容中语言风格的一致性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _get_original_style_sample(self, original_chapters: List[Dict[str, Any]]) -> str:
        """获取原文语言风格样本"""
        try:
            if not original_chapters:
                return "无原文样本"
            
            # 选择最近的几章作为样本
            sample_chapters = original_chapters[-3:] if len(original_chapters) >= 3 else original_chapters
            
            sample_text = ""
            for chapter in sample_chapters:
                content = chapter.get("content", "")
                if content:
                    # 取前500字作为样本
                    sample_text += content[:500] + "\n\n"
            
            return sample_text if sample_text else "无原文样本"
            
        except Exception as e:
            self.log(f"获取原文风格样本失败: {e}")
            return "无原文样本"
