"""
续写世界观一致性专项改进智能体
专门改进续写内容中世界观的一致性问题
"""

from agents.base_continuation_improver import BaseContinuationImprover
from typing import Dict, List, Any, Optional
import config


class ContinuationWorldConsistencyImprover(BaseContinuationImprover):
    """续写世界观一致性专项改进智能体"""
    
    def __init__(self):
        super().__init__("续写世界观一致性专项改进智能体")
    
    def _improve(self, continuation_content: Dict[str, Any],
                quality_assessment: Dict[str, Any],
                knowledge_base: Dict[str, Any],
                user_requirements: str) -> Dict[str, Any]:
        """改进世界观一致性"""
        world_issues = self._analyze_issues(quality_assessment)
        
        if not world_issues.get("needs_improvement", False):
            return {
                "status": "success",
                "improved_content": continuation_content,
                "world_issues": world_issues,
                "improvement_summary": "无需改进"
            }
        
        prompt = f"""
        请基于以下世界观一致性问题，对续写内容进行针对性改进：
        
        世界观设定：
        {self._format_world_setting(knowledge_base)}
        
        当前续写内容：
        {self._format_current_content(continuation_content)}
        
        世界观一致性问题：
        {self._format_issues(world_issues)}
        
        用户需求：{user_requirements if user_requirements else "无特殊要求"}
        
        改进要求：
        1. 确保世界观设定与原文一致
        2. 统一社会制度描述
        3. 修正地理环境描写
        4. 保持文化设定一致
        
        请返回改进后的JSON格式内容。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的世界观编辑，擅长改进续写内容中世界观的一致性问题。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return {
            "status": "success",
            "improved_content": self._integrate_improvements(continuation_content, result),
            "world_issues": world_issues,
            "improvement_summary": self._generate_improvement_summary(world_issues)
        }
    
    def _analyze_issues(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """分析世界观一致性问题"""
        world_issues = {
            "needs_improvement": False,
            "issue_areas": [],
            "priority_level": "low",
            "specific_issues": [],
            "improvement_strategies": []
        }
        
        dimensions = quality_assessment.get("dimensions", {})
        
        checks = [
            ("world_rules_consistency", 85, "世界规则不一致", "修正世界规则描述"),
            ("social_system_consistency", 85, "社会制度描述不一致", "统一社会制度描写"),
            ("geographical_environment_consistency", 80, "地理环境描写不一致", "修正地理环境描述"),
            ("historical_background_consistency", 85, "历史背景不一致", "统一历史背景设定"),
            ("cultural_setting_consistency", 85, "文化设定不一致", "保持文化设定一致")
        ]
        
        scores = []
        for dim_name, threshold, issue, strategy in checks:
            score = dimensions.get(dim_name, 100)
            scores.append(score)
            if score < threshold:
                world_issues["needs_improvement"] = True
                world_issues["issue_areas"].append(dim_name)
                world_issues["specific_issues"].append(issue)
                world_issues["improvement_strategies"].append(strategy)
        
        if world_issues["needs_improvement"] and scores:
            min_score = min(scores)
            if min_score < 60:
                world_issues["priority_level"] = "high"
            elif min_score < 80:
                world_issues["priority_level"] = "medium"
        
        return world_issues
    
    def _format_issues(self, issues: Dict[str, Any]) -> str:
        """格式化问题"""
        return f"""
        问题分析：
        - 需要改进: {issues.get('needs_improvement', False)}
        - 优先级: {issues.get('priority_level', 'low')}
        - 问题领域: {', '.join(issues.get('issue_areas', []))}
        - 具体问题: {', '.join(issues.get('specific_issues', []))}
        """
