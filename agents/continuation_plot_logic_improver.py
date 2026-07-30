"""
续写情节逻辑专项改进智能体
专门改进续写内容中情节的逻辑性问题
"""

from agents.base_continuation_improver import BaseContinuationImprover
from typing import Dict, List, Any, Optional
import config


class ContinuationPlotLogicImprover(BaseContinuationImprover):
    """续写情节逻辑专项改进智能体"""
    
    def __init__(self):
        super().__init__("续写情节逻辑专项改进智能体")
    
    def _improve(self, continuation_content: Dict[str, Any],
                quality_assessment: Dict[str, Any],
                knowledge_base: Dict[str, Any],
                user_requirements: str) -> Dict[str, Any]:
        """改进情节逻辑"""
        plot_issues = self._analyze_issues(quality_assessment)
        
        if not plot_issues.get("needs_improvement", False):
            return {
                "status": "success",
                "improved_content": continuation_content,
                "plot_issues": plot_issues,
                "improvement_summary": "无需改进"
            }
        
        prompt = f"""
        请基于以下情节逻辑问题，对续写内容进行针对性改进：
        
        故事线信息：
        {self._format_plot_lines(knowledge_base)}
        
        当前续写内容：
        {self._format_current_content(continuation_content)}
        
        情节逻辑问题：
        {self._format_issues(plot_issues)}
        
        用户需求：{user_requirements if user_requirements else "无特殊要求"}
        
        改进要求：
        1. 修正情节逻辑问题
        2. 确保因果关系合理
        3. 保持时间线一致
        4. 完善伏笔呼应
        
        请返回改进后的JSON格式内容。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的故事编辑，擅长改进续写内容中情节的逻辑性问题。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return {
            "status": "success",
            "improved_content": self._integrate_improvements(continuation_content, result),
            "plot_issues": plot_issues,
            "improvement_summary": self._generate_improvement_summary(plot_issues)
        }
    
    def _analyze_issues(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """分析情节逻辑问题"""
        plot_issues = {
            "needs_improvement": False,
            "issue_areas": [],
            "priority_level": "low",
            "specific_issues": [],
            "improvement_strategies": []
        }
        
        dimensions = quality_assessment.get("dimensions", {})
        
        checks = [
            ("causality_reasonableness", 85, "因果关系不合理", "修正因果关系逻辑"),
            ("timeline_consistency", 85, "时间线不一致", "统一时间线"),
            ("event_development_logic", 80, "事件发展逻辑混乱", "理顺事件发展逻辑"),
            ("conflict_escalation_reasonableness", 85, "冲突升级不合理", "调整冲突发展节奏"),
            ("foreshadowing_echo_completeness", 85, "伏笔呼应不完整", "完善伏笔呼应")
        ]
        
        scores = []
        for dim_name, threshold, issue, strategy in checks:
            score = dimensions.get(dim_name, 100)
            scores.append(score)
            if score < threshold:
                plot_issues["needs_improvement"] = True
                plot_issues["issue_areas"].append(dim_name)
                plot_issues["specific_issues"].append(issue)
                plot_issues["improvement_strategies"].append(strategy)
        
        if plot_issues["needs_improvement"] and scores:
            min_score = min(scores)
            if min_score < 60:
                plot_issues["priority_level"] = "high"
            elif min_score < 80:
                plot_issues["priority_level"] = "medium"
        
        return plot_issues
    
    def _format_issues(self, issues: Dict[str, Any]) -> str:
        """格式化问题"""
        return f"""
        问题分析：
        - 需要改进: {issues.get('needs_improvement', False)}
        - 优先级: {issues.get('priority_level', 'low')}
        - 问题领域: {', '.join(issues.get('issue_areas', []))}
        - 具体问题: {', '.join(issues.get('specific_issues', []))}
        """
