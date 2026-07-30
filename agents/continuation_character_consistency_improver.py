"""
续写人物一致性专项改进智能体
专门改进续写内容中人物的一致性问题
"""

from agents.base_continuation_improver import BaseContinuationImprover
from typing import Dict, List, Any, Optional
import config


class ContinuationCharacterConsistencyImprover(BaseContinuationImprover):
    """续写人物一致性专项改进智能体"""
    
    def __init__(self):
        super().__init__("续写人物一致性专项改进智能体")
    
    def _improve(self, continuation_content: Dict[str, Any],
                quality_assessment: Dict[str, Any],
                knowledge_base: Dict[str, Any],
                user_requirements: str) -> Dict[str, Any]:
        """改进人物一致性"""
        # 分析人物一致性问题
        character_issues = self._analyze_issues(quality_assessment)
        
        # 执行人物一致性改进
        improved_content = self._improve_character_consistency(
            continuation_content, character_issues, knowledge_base, user_requirements
        )
        
        return {
            "status": "success",
            "improved_content": improved_content,
            "character_issues": character_issues,
            "improvement_summary": self._generate_improvement_summary(character_issues)
        }
    
    def _analyze_issues(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """分析人物一致性问题"""
        try:
            character_issues = {
                "needs_improvement": False,
                "issue_areas": [],
                "priority_level": "low",
                "specific_issues": [],
                "improvement_strategies": []
            }
            
            dimensions = quality_assessment.get("dimensions", {})
            suggestions = quality_assessment.get("suggestions", [])
            
            # 检查各项分数
            checks = [
                ("personality_consistency", 85, "人物性格特征与原文设定不一致", "调整人物性格表现和描述"),
                ("behavior_logic_consistency", 85, "人物行为逻辑不合理", "修正人物行为逻辑和动机"),
                ("language_style_consistency", 80, "人物语言风格与原文不一致", "统一人物语言风格和表达方式"),
                ("relationship_development_consistency", 85, "人物关系发展不合理", "调整人物关系发展逻辑"),
                ("growth_trajectory_consistency", 85, "人物成长轨迹不连贯", "完善人物成长轨迹和发展")
            ]
            
            scores = []
            for dim_name, threshold, issue, strategy in checks:
                score = dimensions.get(dim_name, 100)
                scores.append(score)
                if score < threshold:
                    character_issues["needs_improvement"] = True
                    character_issues["issue_areas"].append(dim_name)
                    character_issues["specific_issues"].append(issue)
                    character_issues["improvement_strategies"].append(strategy)
            
            # 确定优先级
            if character_issues["needs_improvement"] and scores:
                min_score = min(scores)
                if min_score < 60:
                    character_issues["priority_level"] = "high"
                elif min_score < 80:
                    character_issues["priority_level"] = "medium"
            
            # 添加具体建议
            for suggestion in suggestions:
                if any(keyword in suggestion for keyword in ["人物", "性格", "行为"]):
                    character_issues["improvement_strategies"].append(suggestion)
            
            return character_issues
            
        except Exception as e:
            self.log(f"分析人物一致性问题失败: {e}")
            return {
                "needs_improvement": True,
                "issue_areas": ["general"],
                "priority_level": "medium",
                "specific_issues": ["人物一致性问题需要改进"],
                "improvement_strategies": ["全面优化人物一致性"]
            }
    
    def _improve_character_consistency(self, continuation_content: Dict[str, Any], 
                                     character_issues: Dict[str, Any],
                                     knowledge_base: Dict[str, Any],
                                     user_requirements: str) -> Dict[str, Any]:
        """改进人物一致性"""
        try:
            if not character_issues.get("needs_improvement", False):
                return continuation_content
            
            prompt = f"""
            请基于以下人物一致性问题，对续写内容进行针对性改进：
            
            原文人物设定：
            {self._format_character_profiles(knowledge_base)}
            
            用户需求：
            {user_requirements if user_requirements else "无特殊要求"}
            
            当前续写内容（需要改进）：
            {self._format_current_content(continuation_content)}
            
            人物一致性问题分析：
            {self._format_issues(character_issues)}
            
            改进要求：
            1. 根据问题分析进行针对性改进
            2. 确保人物性格与原文设定一致
            3. 修正人物行为逻辑和动机
            4. 统一人物语言风格和表达方式
            5. 保持内容的自然流畅性
            
            请返回改进后的JSON格式内容。
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的人物设定编辑，擅长改进续写内容中人物的一致性问题。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.call_llm(messages)
            result = self.parse_json_response(response)
            
            return self._integrate_improvements(continuation_content, result)
            
        except Exception as e:
            self.log(f"改进人物一致性失败: {e}")
            return self._create_fallback_content(continuation_content, character_issues)
    
    def _format_issues(self, issues: Dict[str, Any]) -> str:
        """格式化问题"""
        return f"""
        问题分析：
        - 需要改进: {issues.get('needs_improvement', False)}
        - 优先级: {issues.get('priority_level', 'low')}
        - 问题领域: {', '.join(issues.get('issue_areas', []))}
        - 具体问题: {', '.join(issues.get('specific_issues', []))}
        - 改进策略: {', '.join(issues.get('improvement_strategies', []))}
        """
