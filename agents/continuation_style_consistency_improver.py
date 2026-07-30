"""
续写语言风格专项改进智能体
专门改进续写内容中语言风格的一致性问题
"""

from agents.base_continuation_improver import BaseContinuationImprover
from typing import Dict, List, Any, Optional
import config


class ContinuationStyleConsistencyImprover(BaseContinuationImprover):
    """续写语言风格专项改进智能体"""
    
    def __init__(self):
        super().__init__("续写语言风格专项改进智能体")
    
    def _improve(self, continuation_content: Dict[str, Any],
                quality_assessment: Dict[str, Any],
                knowledge_base: Dict[str, Any],
                user_requirements: str) -> Dict[str, Any]:
        """改进语言风格一致性"""
        style_issues = self._analyze_issues(quality_assessment)
        
        if not style_issues.get("needs_improvement", False):
            return {
                "status": "success",
                "improved_content": continuation_content,
                "style_issues": style_issues,
                "improvement_summary": "无需改进"
            }
        
        prompt = f"""
        请基于以下语言风格一致性问题，对续写内容进行针对性改进：
        
        原文风格样本：
        {self._get_original_style_sample(knowledge_base.get("chapters", []))}
        
        当前续写内容：
        {self._format_current_content(continuation_content)}
        
        语言风格问题：
        {self._format_issues(style_issues)}
        
        用户需求：{user_requirements if user_requirements else "无特殊要求"}
        
        改进要求：
        1. 统一语言风格
        2. 提升文笔质量
        3. 调整修辞手法
        4. 保持节奏一致
        
        请返回改进后的JSON格式内容。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的语言风格编辑，擅长改进续写内容中语言风格的一致性问题。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return {
            "status": "success",
            "improved_content": self._integrate_improvements(continuation_content, result),
            "style_issues": style_issues,
            "improvement_summary": self._generate_improvement_summary(style_issues)
        }
    
    def _analyze_issues(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """分析语言风格一致性问题"""
        style_issues = {
            "needs_improvement": False,
            "issue_areas": [],
            "priority_level": "low",
            "specific_issues": [],
            "improvement_strategies": []
        }
        
        dimensions = quality_assessment.get("dimensions", {})
        
        checks = [
            ("language_style_consistency", 85, "语言风格不一致", "统一语言风格"),
            ("writing_quality", 80, "文笔质量不足", "提升文笔质量"),
            ("rhetorical_device_usage", 80, "修辞手法运用不当", "调整修辞手法"),
            ("rhythm_control", 85, "节奏控制不佳", "优化节奏控制"),
            ("emotional_expression_consistency", 85, "情感表达不一致", "统一情感表达")
        ]
        
        scores = []
        for dim_name, threshold, issue, strategy in checks:
            score = dimensions.get(dim_name, 100)
            scores.append(score)
            if score < threshold:
                style_issues["needs_improvement"] = True
                style_issues["issue_areas"].append(dim_name)
                style_issues["specific_issues"].append(issue)
                style_issues["improvement_strategies"].append(strategy)
        
        if style_issues["needs_improvement"] and scores:
            min_score = min(scores)
            if min_score < 60:
                style_issues["priority_level"] = "high"
            elif min_score < 80:
                style_issues["priority_level"] = "medium"
        
        return style_issues
    
    def _get_original_style_sample(self, chapters: List[Dict[str, Any]]) -> str:
        """获取原文风格样本"""
        if not chapters:
            return "无原文样本"
        
        sample_chapters = chapters[-2:] if len(chapters) >= 2 else chapters
        sample = ""
        for chapter in sample_chapters:
            content = chapter.get("content", "")
            if content:
                sample += content[:300] + "\n\n"
        
        return sample if sample else "无原文样本"
    
    def _format_issues(self, issues: Dict[str, Any]) -> str:
        """格式化问题"""
        return f"""
        问题分析：
        - 需要改进: {issues.get('needs_improvement', False)}
        - 优先级: {issues.get('priority_level', 'low')}
        - 问题领域: {', '.join(issues.get('issue_areas', []))}
        - 具体问题: {', '.join(issues.get('specific_issues', []))}
        """
