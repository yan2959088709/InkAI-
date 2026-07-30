"""
卷间关联增强系统
确保每一卷的人物成长、剧情推进都有联系

核心功能：
1. 跨卷人物成长追踪
2. 剧情阶梯升级
3. 伏笔跨卷管理
4. 卷间强制衔接
"""

from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger("volume_connection")


class VolumeConnectionManager:
    """卷间关联管理器"""
    
    def __init__(self, data_manager=None):
        self.data_manager = data_manager
    
    def get_volume_connection_context(self, novel_id: str, chapter_number: int,
                                     chapters_per_volume: int = 40) -> Dict[str, Any]:
        """
        获取卷间关联上下文
        
        确保每一卷都与前文保持连贯
        """
        from core.volume_manager import VolumeManager
        volume_manager = VolumeManager(self.data_manager)
        
        # 获取卷信息
        volume_info = volume_manager.get_volume_info(novel_id, chapter_number, chapters_per_volume)
        current_volume = volume_info["volume_number"]
        chapter_in_volume = volume_info["chapter_in_volume"]
        
        context = {
            "volume_info": volume_info,
            "character_arc": {},
            "plot_progression": {},
            "foreshadowing_status": {},
            "volume_transition": {}
        }
        
        # 1. 获取人物弧光（跨卷追踪）
        context["character_arc"] = self._get_character_arc(novel_id, current_volume)
        
        # 2. 获取剧情进度
        context["plot_progression"] = self._get_plot_progression(novel_id, current_volume)
        
        # 3. 获取伏笔状态
        context["foreshadowing_status"] = self._get_foreshadowing_status(novel_id, chapter_number)
        
        # 4. 卷间转换信息
        if chapter_in_volume == 1 and current_volume > 1:
            context["volume_transition"] = self._get_volume_transition(novel_id, current_volume)
        
        return context
    
    def _get_character_arc(self, novel_id: str, current_volume: int) -> Dict[str, Any]:
        """获取人物弧光（跨卷追踪）"""
        if not self.data_manager:
            return {}
        
        try:
            # 从动态知识库获取角色演化
            characters = self.data_manager.load_novel_data(novel_id, "characters")
            
            arc = {
                "main_character": {
                    "name": "",
                    "initial_state": "",  # 初始状态
                    "current_state": "",  # 当前状态
                    "growth_milestones": [],  # 成长里程碑
                    "next_growth_target": ""  # 下一个成长目标
                },
                "supporting_characters": []
            }
            
            if characters:
                main_char = characters.get("main_character", {})
                arc["main_character"]["name"] = main_char.get("basic_info", {}).get("name", "")
                arc["main_character"]["initial_state"] = main_char.get("personality", {}).get("description", "")
            
            return arc
            
        except Exception as e:
            logger.error(f"获取人物弧光失败: {e}")
            return {}
    
    def _get_plot_progression(self, novel_id: str, current_volume: int) -> Dict[str, Any]:
        """获取剧情进度（确保阶梯升级）"""
        if not self.data_manager:
            return {}
        
        try:
            chapters = self.data_manager.get_chapters(novel_id)
            
            progression = {
                "current_volume": current_volume,
                "total_chapters": len(chapters),
                "conflict_level": self._determine_conflict_level(current_volume),
                "stakes_level": self._determine_stakes_level(current_volume),
                "major_events_count": 0,
                "unresolved_conflicts": []
            }
            
            # 统计主要事件
            for ch in chapters:
                key_events = ch.get("key_events", [])
                progression["major_events_count"] += len(key_events)
            
            return progression
            
        except Exception as e:
            logger.error(f"获取剧情进度失败: {e}")
            return {}
    
    def _determine_conflict_level(self, volume_number: int) -> str:
        """根据卷号确定冲突级别"""
        if volume_number <= 3:  # 前3卷（约120章）
            return "personal_crisis"  # 个人危机
        elif volume_number <= 15:  # 中间12卷（约480章）
            return "local_crisis"  # 局部危机
        else:  # 最后10卷（约400章）
            return "global_crisis"  # 全局危机
    
    def _determine_stakes_level(self, volume_number: int) -> str:
        """根据卷号确定赌注级别"""
        if volume_number <= 3:
            return "personal_safety"  # 个人安危
        elif volume_number <= 15:
            return "team_survival"  # 团队生存
        else:
            return "world_fate"  # 世界命运
    
    def _get_foreshadowing_status(self, novel_id: str, chapter_number: int) -> Dict[str, Any]:
        """获取伏笔状态"""
        if not self.data_manager:
            return {}
        
        try:
            chapters = self.data_manager.get_chapters(novel_id)
            
            status = {
                "active_foreshadowing": [],
                "recently_resolved": [],
                "pending_resolution": []
            }
            
            # 收集最近的伏笔
            for ch in chapters[-10:]:
                foreshadowing = ch.get("foreshadowing", [])
                for fs in foreshadowing:
                    if isinstance(fs, str):
                        status["active_foreshadowing"].append({
                            "content": fs,
                            "chapter": ch.get("chapter_number", 0)
                        })
            
            return status
            
        except Exception as e:
            logger.error(f"获取伏笔状态失败: {e}")
            return {}
    
    def _get_volume_transition(self, novel_id: str, current_volume: int) -> Dict[str, Any]:
        """获取卷间转换信息"""
        from core.volume_manager import VolumeManager
        volume_manager = VolumeManager(self.data_manager)
        
        # 获取上一卷摘要
        prev_summary = volume_manager.load_volume_summary(novel_id, current_volume - 1)
        
        transition = {
            "previous_volume": current_volume - 1,
            "previous_summary": prev_summary,
            "connection_requirements": self._get_connection_requirements(current_volume)
        }
        
        return transition
    
    def _get_connection_requirements(self, volume_number: int) -> List[str]:
        """获取卷间衔接要求"""
        requirements = [
            "1. 回顾上卷结尾的关键事件",
            "2. 延续上卷的人物状态和发展",
            "3. 推进上卷未完成的伏笔",
            "4. 升级核心冲突的赌注"
        ]
        
        # 根据卷号添加特定要求
        if volume_number == 2:
            requirements.append("5. 建立本卷的新目标和挑战")
        elif volume_number > 10:
            requirements.append("5. 深化核心矛盾，为最终决战铺垫")
        
        return requirements
    
    def get_volume_guidance_with_connection(self, novel_id: str, chapter_number: int,
                                           chapters_per_volume: int = 40) -> str:
        """获取带卷间关联的写作指导"""
        context = self.get_volume_connection_context(novel_id, chapter_number, chapters_per_volume)
        
        volume_info = context["volume_info"]
        plot = context["plot_progression"]
        
        guidance = f"""
【分卷信息】：
- 当前卷：第{volume_info['volume_number']}卷
- 卷内章节：第{volume_info['chapter_in_volume']}章
- 冲突级别：{self._get_conflict_name(plot.get('conflict_level', ''))}
- 赌注级别：{self._get_stakes_name(plot.get('stakes_level', ''))}

【卷间关联要求】：
{self._format_connection_requirements(context)}
"""
        return guidance
    
    def _get_conflict_name(self, level: str) -> str:
        """获取冲突级别名称"""
        names = {
            "personal_crisis": "个人危机",
            "local_crisis": "局部危机",
            "global_crisis": "全局危机"
        }
        return names.get(level, level)
    
    def _get_stakes_name(self, level: str) -> str:
        """获取赌注级别名称"""
        names = {
            "personal_safety": "个人安危",
            "team_survival": "团队生存",
            "world_fate": "世界命运"
        }
        return names.get(level, level)
    
    def _format_connection_requirements(self, context: Dict) -> str:
        """格式化衔接要求"""
        volume_info = context["volume_info"]
        transition = context.get("volume_transition", {})
        
        if not transition:
            return "本章继续推进当前卷剧情"
        
        prev_summary = transition.get("previous_summary")
        requirements = transition.get("connection_requirements", [])
        
        result = ""
        if prev_summary:
            result += f"上卷关键事件: {', '.join(prev_summary.get('key_events', [])[:3])}\n"
        
        for req in requirements[:3]:
            result += f"{req}\n"
        
        return result


def get_volume_connection_context(novel_id: str, chapter_number: int,
                                 chapters_per_volume: int = 40) -> Dict[str, Any]:
    """获取卷间关联上下文的便捷函数"""
    manager = VolumeConnectionManager()
    return manager.get_volume_connection_context(novel_id, chapter_number, chapters_per_volume)
