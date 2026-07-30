"""
节奏控制器
实现3章节奏循环（强推进章/缓冲铺垫章/升级转折章）
"""

from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger("rhythm_controller")


class RhythmController:
    """节奏控制器"""
    
    # 章节类型定义
    CHAPTER_TYPES = {
        0: {
            "name": "strong_push",
            "display_name": "强推进章",
            "description": "核心主线推进，主角直面障碍，完成关键行动",
            "conflict_preference": "external",
            "focus": "plot_progression"
        },
        1: {
            "name": "buffer_setup", 
            "display_name": "缓冲铺垫章",
            "description": "人物塑造、伏笔铺垫、双线穿插",
            "conflict_preference": "internal",
            "focus": "character_development"
        },
        2: {
            "name": "upgrade_turn",
            "display_name": "升级转折章",
            "description": "收束铺垫，矛盾升级，为下阶段铺垫",
            "conflict_preference": "mixed",
            "focus": "conflict_escalation"
        }
    }
    
    def get_chapter_type(self, chapter_number: int) -> Dict[str, Any]:
        """
        根据章节号获取章节类型
        
        Args:
            chapter_number: 章节号
        
        Returns:
            章节类型信息
        """
        type_index = chapter_number % 3
        chapter_type = self.CHAPTER_TYPES[type_index].copy()
        chapter_type["chapter_number"] = chapter_number
        chapter_type["type_index"] = type_index
        
        return chapter_type
    
    def get_writing_guidance(self, chapter_number: int) -> str:
        """
        获取写作指导
        
        Args:
            chapter_number: 章节号
        
        Returns:
            写作指导文本
        """
        chapter_type = self.get_chapter_type(chapter_number)
        
        guidance = f"""
【本章类型】：{chapter_type['display_name']}
【类型说明】：{chapter_type['description']}

{self._get_type_specific_guidance(chapter_type)}
"""
        return guidance
    
    def _get_type_specific_guidance(self, chapter_type: Dict) -> str:
        """获取类型特定的写作指导"""
        type_name = chapter_type["name"]
        
        if type_name == "strong_push":
            return """
【强推进章写作要求】：
1. 冲突类型：以外部强冲突为主（生死对抗、正邪对决）
2. 核心任务：推进主线剧情，完成关键行动
3. 情绪落点：必须有明确的爽点/高光时刻
4. 结尾要求：强钩子，让读者期待下一章

【示例场景】：
- 主角潜入敌人基地获取关键证据
- 与反派的正面交锋
- 解决一个关键难题
"""
        elif type_name == "buffer_setup":
            return """
【缓冲铺垫章写作要求】：
1. 冲突类型：以内部冲突/人际冲突为主
2. 核心任务：人物成长、伏笔铺垫、双线穿插
3. 情绪落点：人物弧光的关键节点/悬念升级
4. 结尾要求：埋下新的伏笔或揭示新的疑点

【示例场景】：
- 主角的内心挣扎和关键选择
- 配角的背景故事和动机揭示
- 角色之间的信任危机或理念碰撞
"""
        elif type_name == "upgrade_turn":
            return """
【升级转折章写作要求】：
1. 冲突类型：多类型冲突叠加
2. 核心任务：矛盾升级，为下阶段铺垫
3. 情绪落点：危机感升级，读者感到更大威胁
4. 结尾要求：颠覆性反转或危机升级

【示例场景】：
- 反派的真实身份或计划被揭露
- 主角发现更大的阴谋
- 双线首次交汇，真相初现
"""
        return ""


def get_rhythm_guidance(chapter_number: int) -> str:
    """获取节奏指导的便捷函数"""
    controller = RhythmController()
    return controller.get_writing_guidance(chapter_number)


def get_chapter_type_info(chapter_number: int) -> Dict[str, Any]:
    """获取章节类型信息的便捷函数"""
    controller = RhythmController()
    return controller.get_chapter_type(chapter_number)
