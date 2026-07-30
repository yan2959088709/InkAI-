"""
续写改进智能体基础类
提供所有续写改进智能体的公共功能
"""

from abc import ABC, abstractmethod
from base_agent import BaseAgent
from typing import Dict, List, Any, Optional
import config


class BaseContinuationImprover(BaseAgent, ABC):
    """续写改进智能体基础类"""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理改进请求"""
        continuation_content = input_data.get("continuation_content", {})
        quality_assessment = input_data.get("quality_assessment", {})
        knowledge_base = input_data.get("knowledge_base", {})
        user_requirements = input_data.get("user_requirements", "")
        
        if not continuation_content or not quality_assessment:
            return {"error": "缺少必要的改进数据"}
        
        # 调用子类实现的具体改进逻辑
        return self._improve(continuation_content, quality_assessment, knowledge_base, user_requirements)
    
    @abstractmethod
    def _improve(self, continuation_content: Dict[str, Any],
                quality_assessment: Dict[str, Any],
                knowledge_base: Dict[str, Any],
                user_requirements: str) -> Dict[str, Any]:
        """子类实现的具体改进逻辑"""
        pass
    
    @abstractmethod
    def _analyze_issues(self, quality_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """子类实现的问题分析逻辑"""
        pass
    
    def _integrate_improvements(self, original_content: Dict[str, Any], 
                              improvement_result: Dict[str, Any]) -> Dict[str, Any]:
        """整合改进结果"""
        try:
            improved_content = original_content.copy()
            
            # 更新内容
            if "improved_content" in improvement_result:
                new_content = improvement_result["improved_content"]
                if isinstance(new_content, str):
                    improved_content["content"] = new_content
                elif isinstance(new_content, dict) and "content" in new_content:
                    improved_content["content"] = new_content["content"]
            
            # 添加改进记录
            if "improvement_notes" in improvement_result:
                improved_content["improvement_notes"] = improvement_result["improvement_notes"]
            
            # 添加改进标记
            improved_content["improved"] = True
            improved_content["improvement_type"] = self.name
            
            return improved_content
            
        except Exception as e:
            self.log(f"整合改进结果失败: {e}")
            return original_content
    
    def _create_fallback_content(self, original_content: Dict[str, Any], 
                               issues: Dict[str, Any]) -> Dict[str, Any]:
        """创建备用内容"""
        fallback_content = original_content.copy()
        fallback_content["improved"] = False
        fallback_content["improvement_type"] = self.name
        fallback_content["improvement_notes"] = f"改进失败，保留原内容。问题：{issues.get('specific_issues', [])}"
        return fallback_content
    
    def _generate_improvement_summary(self, issues: Dict[str, Any]) -> str:
        """生成改进总结"""
        if not issues.get("needs_improvement", False):
            return "无需改进"
        
        issue_areas = issues.get("issue_areas", [])
        specific_issues = issues.get("specific_issues", [])
        priority = issues.get("priority_level", "low")
        
        summary = f"改进优先级：{priority}\n"
        summary += f"问题区域：{', '.join(issue_areas)}\n"
        summary += f"具体问题：{', '.join(specific_issues[:3])}"
        
        return summary
    
    def _format_current_content(self, content: Dict[str, Any]) -> str:
        """格式化当前内容"""
        if isinstance(content, str):
            return content[:3000]
        
        if isinstance(content, dict):
            # 如果是故事内容
            if "content" in content:
                return content["content"][:3000]
            # 如果是故事线
            return str(content)[:2000]
        
        return str(content)[:2000]
    
    def _format_character_profiles(self, knowledge_base: Dict[str, Any]) -> str:
        """格式化人物档案"""
        character_profiles = knowledge_base.get("character_profiles", {})
        if not character_profiles:
            return "无人物档案"
        
        formatted = ""
        main_character = character_profiles.get("main_character", {})
        if main_character:
            basic_info = main_character.get("basic_info", {})
            personality = main_character.get("personality", {})
            
            formatted += f"主角：{basic_info.get('name', '未知')}\n"
            formatted += f"  性格：{personality.get('description', '未知')}\n\n"
        
        supporting_characters = character_profiles.get("supporting_characters", [])
        for char in supporting_characters[:3]:  # 只显示前3个配角
            basic_info = char.get("basic_info", {})
            formatted += f"配角：{basic_info.get('name', '未知')}\n"
            formatted += f"  性格：{char.get('personality', '未知')}\n\n"
        
        return formatted
    
    def _format_plot_lines(self, knowledge_base: Dict[str, Any]) -> str:
        """格式化故事线"""
        plot_lines = knowledge_base.get("plot_lines", {})
        if not plot_lines:
            return "无故事线信息"
        
        formatted = ""
        main_line = plot_lines.get("main_line", [])
        if main_line:
            formatted += "主线：\n"
            for i, line in enumerate(main_line[:5], 1):  # 只显示前5个要点
                formatted += f"  {i}. {line}\n"
        
        return formatted
    
    def _format_world_setting(self, knowledge_base: Dict[str, Any]) -> str:
        """格式化世界观设定"""
        world_setting = knowledge_base.get("world_setting", "")
        if not world_setting:
            return "无世界观设定"
        
        if isinstance(world_setting, str):
            return world_setting
        
        if isinstance(world_setting, dict):
            return f"时代：{world_setting.get('time_period', '未知')}, 地点：{world_setting.get('location', '未知')}"
        
        return str(world_setting)
