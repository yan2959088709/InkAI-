# 续写分析智能体
# 负责分析现有内容，提取关键信息，确定续写方向

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..core.base_agent import EnhancedBaseAgent


class ContinuationAnalyzerAgent(EnhancedBaseAgent):
    """续写分析智能体 - 分析现有内容，确定续写方向"""
    
    def __init__(self):
        super().__init__("续写分析智能体")
        
        # 分析维度
        self.analysis_dimensions = {
            "content_analysis": "内容分析",
            "character_analysis": "人物分析", 
            "plot_analysis": "情节分析",
            "continuation_direction": "续写方向"
        }
        
        # 续写类型
        self.continuation_types = {
            "plot_advancement": "情节推进",
            "character_development": "人物发展",
            "conflict_escalation": "冲突升级",
            "world_building": "世界观扩展",
            "relationship_development": "关系发展",
            "mystery_revelation": "谜题揭示"
        }
        
        self._log("续写分析智能体初始化完成", "INFO")
    
    def analyze_for_continuation(self, novel_data: Dict[str, Any], continuation_requirements: str = "") -> Dict[str, Any]:
        """分析现有内容，为续写做准备"""
        self._log("开始续写分析", "INFO")
        
        # 提取关键信息
        key_info = self._extract_key_information(novel_data)
        
        # 分析内容状态
        content_analysis = self._analyze_content_state(novel_data)
        
        # 分析人物状态
        character_analysis = self._analyze_character_state(novel_data)
        
        # 分析情节状态
        plot_analysis = self._analyze_plot_state(novel_data)
        
        # 确定续写方向
        continuation_direction = self._determine_continuation_direction(
            key_info, content_analysis, character_analysis, plot_analysis, continuation_requirements
        )
        
        # 生成续写建议
        continuation_suggestions = self._generate_continuation_suggestions(continuation_direction)
        
        analysis_result = {
            "key_information": key_info,
            "content_analysis": content_analysis,
            "character_analysis": character_analysis,
            "plot_analysis": plot_analysis,
            "continuation_direction": continuation_direction,
            "continuation_suggestions": continuation_suggestions,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        self._log("续写分析完成", "INFO")
        return analysis_result
    
    def _extract_key_information(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键信息"""
        key_info = {
            "novel_title": novel_data.get("title", "未命名小说"),
            "total_chapters": len(novel_data.get("chapters", [])),
            "last_chapter": {},
            "main_characters": [],
            "current_plot_points": [],
            "unresolved_conflicts": [],
            "foreshadowing_elements": []
        }
        
        # 获取最后一章信息
        chapters = novel_data.get("chapters", [])
        if chapters:
            last_chapter = chapters[-1]
            key_info["last_chapter"] = {
                "title": last_chapter.get("title", ""),
                "summary": last_chapter.get("summary", ""),
                "key_events": last_chapter.get("key_events", []),
                "foreshadowing": last_chapter.get("foreshadowing", [])
            }
        
        # 提取人物信息
        characters = novel_data.get("characters", {})
        if characters:
            key_info["main_characters"] = self._extract_character_info(characters)
        
        # 提取故事线信息
        storyline = novel_data.get("storyline", {})
        if storyline:
            key_info["current_plot_points"] = self._extract_plot_points(storyline)
            key_info["unresolved_conflicts"] = self._extract_conflicts(storyline)
        
        return key_info
    
    def _extract_character_info(self, characters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取人物信息"""
        character_list = []
        
        # 处理主角信息
        if "basic_info" in characters:
            main_char = {
                "name": characters["basic_info"].get("name", "未知"),
                "role": "主角",
                "current_state": "活跃",
                "key_traits": characters.get("personality", {}).get("description", ""),
                "goals": characters.get("goals", {}),
                "relationships": characters.get("relationships", {})
            }
            character_list.append(main_char)
        
        # 处理配角信息
        supporting_chars = characters.get("supporting_characters", [])
        for char in supporting_chars:
            if isinstance(char, dict):
                char_info = {
                    "name": char.get("basic_info", {}).get("name", "未知"),
                    "role": char.get("character_type", "配角"),
                    "current_state": "活跃",
                    "key_traits": char.get("personality", {}).get("description", ""),
                    "relationship_to_main": char.get("relationship_to_main", "")
                }
                character_list.append(char_info)
        
        return character_list
    
    def _extract_plot_points(self, storyline: Dict[str, Any]) -> List[str]:
        """提取当前情节要点"""
        plot_points = []
        
        # 从三幕剧结构中提取
        for act in ["act1", "act2", "act3"]:
            if act in storyline:
                act_data = storyline[act]
                if isinstance(act_data, dict):
                    for key, value in act_data.items():
                        if isinstance(value, list):
                            plot_points.extend(value)
                        elif isinstance(value, str):
                            plot_points.append(value)
        
        return plot_points[:5]  # 限制数量
    
    def _extract_conflicts(self, storyline: Dict[str, Any]) -> List[str]:
        """提取未解决的冲突"""
        conflicts = []
        
        # 从故事线中提取冲突
        if "main_conflict" in storyline:
            main_conflict = storyline["main_conflict"]
            if isinstance(main_conflict, dict):
                conflicts.append(main_conflict.get("description", ""))
            else:
                conflicts.append(str(main_conflict))
        
        return conflicts
    
    def _analyze_content_state(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析内容状态"""
        chapters = novel_data.get("chapters", [])
        
        analysis = {
            "total_chapters": len(chapters),
            "story_progress": "开始",
            "content_quality": "良好",
            "pacing_analysis": "正常",
            "recent_themes": [],
            "writing_style": "标准"
        }
        
        if chapters:
            # 分析故事进度
            if len(chapters) <= 3:
                analysis["story_progress"] = "开始阶段"
            elif len(chapters) <= 10:
                analysis["story_progress"] = "发展阶段"
            elif len(chapters) <= 20:
                analysis["story_progress"] = "高潮阶段"
            else:
                analysis["story_progress"] = "收尾阶段"
            
            # 分析最近章节的主题
            recent_chapters = chapters[-3:]  # 最近3章
            for chapter in recent_chapters:
                if "key_events" in chapter:
                    analysis["recent_themes"].extend(chapter["key_events"][:2])
        
        return analysis
    
    def _analyze_character_state(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析人物状态"""
        characters = novel_data.get("characters", {})
        
        analysis = {
            "main_character_status": "活跃",
            "character_development_level": "初期",
            "relationship_dynamics": "稳定",
            "character_conflicts": [],
            "growth_potential": "高"
        }
        
        if characters:
            # 分析主角状态
            if "basic_info" in characters:
                analysis["main_character_status"] = "活跃"
                
                # 分析人物发展水平
                if "character_arc" in characters:
                    arc = characters["character_arc"]
                    if "starting_point" in arc:
                        analysis["character_development_level"] = "初期"
                    elif "growth_path" in arc:
                        analysis["character_development_level"] = "发展期"
                    elif "transformation" in arc:
                        analysis["character_development_level"] = "转变期"
        
        return analysis
    
    def _analyze_plot_state(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析情节状态"""
        storyline = novel_data.get("storyline", {})
        chapters = novel_data.get("chapters", [])
        
        analysis = {
            "current_act": "第一幕",
            "plot_tension": "中等",
            "unresolved_mysteries": [],
            "foreshadowing_count": 0,
            "conflict_intensity": "中等",
            "next_plot_hooks": []
        }
        
        if storyline:
            # 确定当前幕
            if "three_act_structure" in storyline:
                if len(chapters) <= 5:
                    analysis["current_act"] = "第一幕"
                elif len(chapters) <= 15:
                    analysis["current_act"] = "第二幕"
                else:
                    analysis["current_act"] = "第三幕"
            
            # 统计伏笔
            for chapter in chapters:
                if "foreshadowing" in chapter:
                    analysis["foreshadowing_count"] += len(chapter["foreshadowing"])
            
            # 提取未解决的谜题
            for chapter in chapters:
                if "foreshadowing" in chapter:
                    analysis["unresolved_mysteries"].extend(chapter["foreshadowing"])
        
        return analysis
    
    def _determine_continuation_direction(self, key_info: Dict[str, Any], content_analysis: Dict[str, Any], 
                                        character_analysis: Dict[str, Any], plot_analysis: Dict[str, Any], 
                                        requirements: str) -> Dict[str, Any]:
        """确定续写方向"""
        direction = {
            "primary_focus": "情节推进",
            "secondary_focus": "人物发展",
            "continuation_type": "plot_advancement",
            "target_length": 2500,
            "key_elements": [],
            "avoid_elements": [],
            "continuation_goals": []
        }
        
        # 根据故事进度确定重点
        story_progress = content_analysis.get("story_progress", "开始阶段")
        current_act = plot_analysis.get("current_act", "第一幕")
        
        if story_progress == "开始阶段":
            direction["primary_focus"] = "人物介绍和世界观建立"
            direction["continuation_type"] = "world_building"
            direction["key_elements"] = ["人物关系", "环境描写", "基础设定"]
        elif story_progress == "发展阶段":
            direction["primary_focus"] = "冲突发展和人物成长"
            direction["continuation_type"] = "conflict_escalation"
            direction["key_elements"] = ["冲突升级", "人物挑战", "技能发展"]
        elif story_progress == "高潮阶段":
            direction["primary_focus"] = "主要冲突解决"
            direction["continuation_type"] = "plot_advancement"
            direction["key_elements"] = ["高潮对决", "关键转折", "谜题揭示"]
        else:
            direction["primary_focus"] = "故事收尾和人物结局"
            direction["continuation_type"] = "character_development"
            direction["key_elements"] = ["人物成长", "关系发展", "故事总结"]
        
        # 根据用户需求调整
        if requirements:
            if "人物" in requirements or "角色" in requirements:
                direction["primary_focus"] = "人物发展"
                direction["continuation_type"] = "character_development"
            elif "冲突" in requirements or "战斗" in requirements:
                direction["primary_focus"] = "冲突升级"
                direction["continuation_type"] = "conflict_escalation"
            elif "谜题" in requirements or "真相" in requirements:
                direction["primary_focus"] = "谜题揭示"
                direction["continuation_type"] = "mystery_revelation"
        
        # 设置续写目标
        direction["continuation_goals"] = [
            f"推进{direction['primary_focus']}",
            "保持人物一致性",
            "发展故事情节",
            "为后续章节留下伏笔"
        ]
        
        return direction
    
    def _generate_continuation_suggestions(self, direction: Dict[str, Any]) -> Dict[str, Any]:
        """生成续写建议"""
        suggestions = {
            "plot_suggestions": [],
            "character_suggestions": [],
            "style_suggestions": [],
            "pacing_suggestions": [],
            "foreshadowing_suggestions": []
        }
        
        continuation_type = direction.get("continuation_type", "plot_advancement")
        
        # 根据续写类型生成建议
        if continuation_type == "plot_advancement":
            suggestions["plot_suggestions"] = [
                "推进主要情节线",
                "引入新的冲突点",
                "发展次要情节",
                "为高潮做铺垫"
            ]
        elif continuation_type == "character_development":
            suggestions["character_suggestions"] = [
                "展现人物内心世界",
                "发展人物关系",
                "让人物面临新挑战",
                "展现人物成长"
            ]
        elif continuation_type == "conflict_escalation":
            suggestions["plot_suggestions"] = [
                "升级现有冲突",
                "引入新的对手",
                "增加紧张感",
                "为决战做准备"
            ]
        elif continuation_type == "world_building":
            suggestions["style_suggestions"] = [
                "详细描述新环境",
                "介绍新的世界观元素",
                "建立新的规则",
                "丰富背景设定"
            ]
        
        # 通用建议
        suggestions["pacing_suggestions"] = [
            "保持适中的节奏",
            "平衡对话和叙述",
            "适当增加紧张感",
            "为读者留下思考空间"
        ]
        
        suggestions["foreshadowing_suggestions"] = [
            "埋下新的伏笔",
            "呼应之前的伏笔",
            "为后续情节做铺垫",
            "增加故事深度"
        ]
        
        return suggestions
