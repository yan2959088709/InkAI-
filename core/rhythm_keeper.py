"""
节奏控制器
确保小说不掉拍的核心机制

功能：
1. 3章节奏循环
2. 卷内阶段控制
3. 冲突阶梯升级
4. 人物弧光追踪
"""

from typing import Dict, List, Any
from utils.logger import get_logger

logger = get_logger("rhythm_keeper")


class RhythmKeeper:
    """节奏保持器 - 确保不掉拍"""
    
    # 节奏循环定义
    RHYTHM_CYCLE = {
        1: {"name": "缓冲铺垫章", "focus": "人物/伏笔", "conflict": "内部/人际"},
        2: {"name": "升级转折章", "focus": "矛盾升级", "conflict": "多类型叠加"},
        3: {"name": "强推进章", "focus": "主线推进", "conflict": "外部强冲突"}
    }
    
    # 卷内阶段
    VOLUME_PHASES = {
        "beginning": {"range": (1, 10), "focus": "建立冲突"},
        "middle": {"range": (11, 30), "focus": "推进发展"},
        "ending": {"range": (31, 40), "focus": "高潮收束"}
    }
    
    def __init__(self):
        self.rhythm_history = []
    
    def get_rhythm_for_chapter(self, chapter_number: int) -> Dict[str, Any]:
        """获取章节的节奏配置"""
        # 3章循环
        cycle_position = ((chapter_number - 1) % 3) + 1
        rhythm = self.RHYTHM_CYCLE[cycle_position].copy()
        
        # 卷内阶段
        chapter_in_volume = ((chapter_number - 1) % 40) + 1
        
        if chapter_in_volume <= 10:
            volume_phase = "beginning"
        elif chapter_in_volume <= 30:
            volume_phase = "middle"
        else:
            volume_phase = "ending"
        
        rhythm["chapter_number"] = chapter_number
        rhythm["cycle_position"] = cycle_position
        rhythm["volume_phase"] = volume_phase
        rhythm["chapter_in_volume"] = chapter_in_volume
        
        return rhythm
    
    def get_rhythm_guidance(self, chapter_number: int) -> str:
        """获取节奏指导"""
        rhythm = self.get_rhythm_for_chapter(chapter_number)
        
        guidance = f"""
【节奏控制】：
- 本章类型：{rhythm['name']}
- 节奏位置：第{rhythm['cycle_position']}章/3章循环
- 卷内阶段：{self._get_phase_name(rhythm['volume_phase'])}

{self._get_type_specific_guidance(rhythm)}

【不掉拍要求】：
1. 本章必须有明确的核心冲突
2. 主角目标必须有进展（哪怕是坏的进展）
3. 结尾必须留下钩子
4. 人物状态必须延续
"""
        return guidance
    
    def _get_phase_name(self, phase: str) -> str:
        """获取阶段名称"""
        names = {
            "beginning": "卷开端（建立冲突）",
            "middle": "卷中段（推进发展）",
            "ending": "卷结尾（高潮收束）"
        }
        return names.get(phase, phase)
    
    def _get_type_specific_guidance(self, rhythm: Dict) -> str:
        """获取类型特定指导"""
        name = rhythm["name"]
        
        if "缓冲" in name:
            return """
【缓冲铺垫章要求】：
- 冲突类型：内部冲突/人际冲突
- 重点：人物成长、伏笔铺垫
- 可以不推主线，但必须推进人物弧光
"""
        elif "升级" in name:
            return """
【升级转折章要求】：
- 冲突类型：多类型冲突叠加
- 重点：矛盾升级、双线交叉
- 必须让读者感到更大的威胁
"""
        else:  # 强推进
            return """
【强推进章要求】：
- 冲突类型：外部强冲突
- 重点：核心主线推进
- 必须有明确的爽点/高光时刻
"""
    
    def check_no_drop(self, chapter_content: Dict[str, Any], 
                     previous_chapters: List[Dict]) -> Dict[str, Any]:
        """
        检查是否掉拍
        
        掉拍的定义：
        - 主角目标没有进展
        - 没有核心冲突
        - 情绪曲线太平
        """
        result = {
            "is_good": True,
            "issues": []
        }
        
        content = chapter_content.get("content", "")
        
        # 检查1: 是否有冲突
        conflict_keywords = ["对抗", "冲突", "危机", "矛盾", "挣扎", "选择"]
        has_conflict = any(kw in content for kw in conflict_keywords)
        
        if not has_conflict:
            result["is_good"] = False
            result["issues"].append("本章缺少核心冲突")
        
        # 检查2: 是否有行动
        action_keywords = ["行动", "做", "决定", "开始", "发现", "找到"]
        has_action = any(kw in content for kw in action_keywords)
        
        if not has_action:
            result["issues"].append("本章主角缺乏行动")
        
        # 检查3: 字数是否达标
        if len(content) < 2500:
            result["issues"].append(f"字数不足: {len(content)}字")
        
        return result


def get_rhythm_for_chapter(chapter_number: int) -> Dict[str, Any]:
    """获取章节节奏的便捷函数"""
    keeper = RhythmKeeper()
    return keeper.get_rhythm_for_chapter(chapter_number)


def get_rhythm_guidance(chapter_number: int) -> str:
    """获取节奏指导的便捷函数"""
    keeper = RhythmKeeper()
    return keeper.get_rhythm_guidance(chapter_number)
