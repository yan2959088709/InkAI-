"""
续写读者体验专项改进智能体
专门改进续写内容的读者体验
"""

from agents.base_continuation_improver import BaseContinuationImprover
from typing import Dict, List, Any, Optional
import config


class ContinuationReaderExperienceImprover(BaseContinuationImprover):
    """续写读者体验专项改进智能体"""
    
    def __init__(self):
        super().__init__("续写读者体验专项改进智能体")
    
    def _improve(self, continuation_content: Dict[str, Any],
                quality_assessment: Dict[str, Any],
                knowledge_base: Dict[str, Any],
                user_requirements: str) -> Dict[str, Any]:
        """改进读者体验"""
        reader_issues = self._analyze_issues(quality_assessment)
        
        if not reader_issues.get("needs_improvement", False):
            return {
                "status": "success",
                "improved_content": continuation_content,
                "reader_issues": reader_issues,
                "improvement_summary": "无需改进"
            }
        
        prompt = f"""
        请基于以下读者体验问题，对续写内容进行针对性改进：
        
        故事基调：{knowledge_base.get("story_tone", "未知")}
        目标读者：{knowledge_base.get("target_audience", "未知")}
        
        当前续写内容：
        {self._format_current_content(continuation_content)}
        
        读者体验问题：
        {self._format_issues(reader_issues)}
        
        用户需求：{user_requirements if user_requirements else "无特殊要求"}
        
        改进要求：
        1. 提升阅读流畅度
        2. 增强情感共鸣
        3. 优化悬念设置
        4. 调整节奏控制
        
        请返回改进后的JSON格式内容。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的读者体验编辑，擅长改进续写内容的读者体验。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return {
            "status": "success",
            "improved_content": self._integrate_improvements(continuation_content, result),
            "reader_issues": reader_issues,
            "improvement_summary": self._generate_improvement_summary(reader_issues)
        }
    
    def _analyze_issues(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """分析读者体验问题"""
        reader_issues = {
            "needs_improvement": False,
            "issue_areas": [],
            "priority_level": "low",
            "specific_issues": [],
            "improvement_strategies": []
        }
        
        dimensions = quality_assessment.get("dimensions", {})
        
        checks = [
            ("reading_fluency", 85, "阅读流畅度不足", "优化句子结构"),
            ("emotional_resonance", 80, "情感共鸣不足", "增强情感描写"),
            ("suspense_setting", 80, "悬念设置不佳", "优化悬念设计"),
            ("rhythm_control", 85, "节奏控制不佳", "调整叙事节奏"),
            ("expectation_management", 85, "期待值管理不当", "优化期待值管理")
        ]
        
        scores = []
        for dim_name, threshold, issue, strategy in checks:
            score = dimensions.get(dim_name, 100)
            scores.append(score)
            if score < threshold:
                reader_issues["needs_improvement"] = True
                reader_issues["issue_areas"].append(dim_name)
                reader_issues["specific_issues"].append(issue)
                reader_issues["improvement_strategies"].append(strategy)
        
        if reader_issues["needs_improvement"] and scores:
            min_score = min(scores)
            if min_score < 60:
                reader_issues["priority_level"] = "high"
            elif min_score < 80:
                reader_issues["priority_level"] = "medium"
        
        return reader_issues
    
    def _format_issues(self, issues: Dict[str, Any]) -> str:
        """格式化问题"""
        return f"""
        问题分析：
        - 需要改进: {issues.get('needs_improvement', False)}
        - 优先级: {issues.get('priority_level', 'low')}
        - 问题领域: {', '.join(issues.get('issue_areas', []))}
        - 具体问题: {', '.join(issues.get('specific_issues', []))}
        """
