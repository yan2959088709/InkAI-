"""
续写情节逻辑专项评估智能体
专门评估续写内容中情节的逻辑性
"""

from agents.base_continuation_assessor import BaseContinuationAssessor
from typing import Dict, List, Any, Optional
import config


class ContinuationPlotLogicAssessor(BaseContinuationAssessor):
    """续写情节逻辑专项评估智能体"""
    
    def __init__(self):
        super().__init__("续写情节逻辑专项评估智能体")
    
    def _assess(self, continuation_content: Dict[str, Any], 
               knowledge_base: Dict[str, Any], 
               content_type: str) -> Dict[str, Any]:
        """评估情节逻辑"""
        try:
            if content_type == "story":
                return self._assess_story_plot_logic(continuation_content, knowledge_base)
            elif content_type == "storyline":
                return self._assess_storyline_plot_logic(continuation_content, knowledge_base)
            else:
                return self._assess_general_plot_logic(continuation_content, knowledge_base)
                
        except Exception as e:
            self.log(f"情节逻辑评估失败: {e}")
            return {
                "is_high_quality": False,
                "overall_score": 0,
                "dimensions": {},
                "suggestions": [f"评估过程出错: {str(e)}"]
            }
    
    def _assess_story_plot_logic(self, chapter_content: Dict[str, Any], 
                               knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事内容中的情节逻辑"""
        content = chapter_content.get("content", "")
        plot_lines = knowledge_base.get("plot_lines", {})
        last_chapter = knowledge_base.get("last_chapter_summary", {})
        
        prompt = f"""
        请专门评估以下续写章节中情节的逻辑性，重点关注以下维度：
        
        原文情节线：
        {self._format_plot_lines(plot_lines)}
        
        上一章结尾：
        {self._format_last_chapter(last_chapter)}
        
        续写章节内容：
        {content[:3000]}
        
        请从以下维度评估情节逻辑（每项0-100分）：
        1. 因果关系合理性：事件之间的因果关系是否合理
        2. 时间线一致性：时间顺序是否一致，无矛盾
        3. 事件发展逻辑：事件发展是否符合逻辑规律
        4. 冲突升级合理性：冲突发展是否合理递进
        5. 伏笔呼应完整性：伏笔设置和呼应是否完整
        
        请返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事编辑，擅长评估续写内容中情节的逻辑性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_storyline_plot_logic(self, storyline_content: Dict[str, Any], 
                                   knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """评估故事线中的情节逻辑"""
        plot_lines = knowledge_base.get("plot_lines", {})
        last_chapter = knowledge_base.get("last_chapter_summary", {})
        
        prompt = f"""
        请评估以下续写故事线中情节的逻辑性：
        
        原文情节线：
        {self._format_plot_lines(plot_lines)}
        
        上一章结尾：
        {self._format_last_chapter(last_chapter)}
        
        续写故事线：
        {str(storyline_content)[:2000]}
        
        请评估故事线中情节逻辑的合理性和连贯性，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事编辑，擅长评估故事线中情节的逻辑性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
    
    def _assess_general_plot_logic(self, content: Dict[str, Any], 
                                 knowledge_base: Dict[str, Any]) -> Dict[str, Any]:
        """通用情节逻辑评估"""
        prompt = f"""
        请评估以下续写内容中情节的逻辑性：
        
        原文情节信息：
        {self._format_plot_lines(knowledge_base.get("plot_lines", {}))}
        
        续写内容：
        {str(content)[:2000]}
        
        请进行综合情节逻辑评估，返回JSON格式评估结果。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的内容编辑，擅长评估续写内容中情节的逻辑性。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return self._validate_assessment_result(result)
