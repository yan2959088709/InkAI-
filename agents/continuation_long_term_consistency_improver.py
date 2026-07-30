"""
续写长期连贯性专项改进智能体
专门改进续写内容的长期连贯性问题
"""

from agents.base_continuation_improver import BaseContinuationImprover
from typing import Dict, List, Any, Optional
import config


class ContinuationLongTermConsistencyImprover(BaseContinuationImprover):
    """续写长期连贯性专项改进智能体"""
    
    def __init__(self):
        super().__init__("续写长期连贯性专项改进智能体")
    
    def _improve(self, continuation_content: Dict[str, Any],
                quality_assessment: Dict[str, Any],
                knowledge_base: Dict[str, Any],
                user_requirements: str) -> Dict[str, Any]:
        """改进长期连贯性"""
        long_term_issues = self._analyze_issues(quality_assessment)
        
        if not long_term_issues.get("needs_improvement", False):
            return {
                "status": "success",
                "improved_content": continuation_content,
                "long_term_issues": long_term_issues,
                "improvement_summary": "无需改进"
            }
        
        prompt = f"""
        请基于以下长期连贯性问题，对续写内容进行针对性改进：
        
        整体故事线：
        {self._format_plot_lines(knowledge_base)}
        
        人物发展轨迹：
        {self._format_character_evolution(knowledge_base.get("character_evolution", {}))}
        
        当前续写内容：
        {self._format_current_content(continuation_content)}
        
        长期连贯性问题：
        {self._format_issues(long_term_issues)}
        
        用户需求：{user_requirements if user_requirements else "无特殊要求"}
        
        改进要求：
        1. 确保整体故事发展一致
        2. 保持人物成长轨迹连贯
        3. 统一主题发展
        4. 完善伏笔线索
        
        请返回改进后的JSON格式内容。
        """
        
        messages = [
            {"role": "system", "content": "你是一个专业的长期连贯性编辑，擅长改进续写内容的长期连贯性问题。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.call_llm(messages)
        result = self.parse_json_response(response)
        
        return {
            "status": "success",
            "improved_content": self._integrate_improvements(continuation_content, result),
            "long_term_issues": long_term_issues,
            "improvement_summary": self._generate_improvement_summary(long_term_issues)
        }
    
    def _analyze_issues(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """分析长期连贯性问题"""
        long_term_issues = {
            "needs_improvement": False,
            "issue_areas": [],
            "priority_level": "low",
            "specific_issues": [],
            "improvement_strategies": []
        }
        
        dimensions = quality_assessment.get("dimensions", {})
        
        checks = [
            ("overall_story_development_consistency", 85, "整体故事发展不一致", "调整故事发展方向"),
            ("character_growth_trajectory_consistency", 85, "人物成长轨迹不连贯", "完善人物成长轨迹"),
            ("theme_development_consistency", 80, "主题发展不一致", "统一主题发展"),
            ("foreshadowing_clue_completeness", 85, "伏笔线索不完整", "完善伏笔线索"),
            ("story_rhythm_control", 85, "故事节奏控制不佳", "调整故事节奏")
        ]
        
        scores = []
        for dim_name, threshold, issue, strategy in checks:
            score = dimensions.get(dim_name, 100)
            scores.append(score)
            if score < threshold:
                long_term_issues["needs_improvement"] = True
                long_term_issues["issue_areas"].append(dim_name)
                long_term_issues["specific_issues"].append(issue)
                long_term_issues["improvement_strategies"].append(strategy)
        
        if long_term_issues["needs_improvement"] and scores:
            min_score = min(scores)
            if min_score < 60:
                long_term_issues["priority_level"] = "high"
            elif min_score < 80:
                long_term_issues["priority_level"] = "medium"
        
        return long_term_issues
    
    def _format_character_evolution(self, character_evolution: Dict[str, Any]) -> str:
        """格式化人物发展轨迹"""
        if not character_evolution:
            return "无人物发展轨迹"
        
        formatted = ""
        for char_name, evolution_list in character_evolution.items():
            formatted += f"{char_name}：\n"
            for evolution in evolution_list[-2:]:
                formatted += f"  第{evolution.get('chapter_number', 0)}章: {evolution.get('description', '')}\n"
            formatted += "\n"
        
        return formatted
    
    def _format_issues(self, issues: Dict[str, Any]) -> str:
        """格式化问题"""
        return f"""
        问题分析：
        - 需要改进: {issues.get('needs_improvement', False)}
        - 优先级: {issues.get('priority_level', 'low')}
        - 问题领域: {', '.join(issues.get('issue_areas', []))}
        - 具体问题: {', '.join(issues.get('specific_issues', []))}
        """
