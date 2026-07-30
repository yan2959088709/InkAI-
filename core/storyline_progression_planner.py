"""
故事线推进规划器
实现：
1. 剧情阶段追踪（开端/中段/结局）
2. 矛盾阶梯升级机制
3. 双层故事线咬合规划
4. 伏笔分层回收计划
"""

from typing import Dict, List, Any, Optional
from utils.logger import get_logger

logger = get_logger("storyline_progression_planner")


class StorylineProgressionPlanner:
    """故事线推进规划器"""
    
    # 剧情阶段定义
    STORY_PHASES = {
        "beginning": {
            "name": "开端",
            "chapters_ratio": 0.25,  # 占全书25%
            "conflict_level": "个人危机",
            "stakes": "个人/身边人安危",
            "description": "核心目标被触发，只关乎个人"
        },
        "middle": {
            "name": "中段",
            "chapters_ratio": 0.50,  # 占全书50%
            "conflict_level": "局部危机",
            "stakes": "团队/组织生死",
            "description": "核心矛盾扩大，面对体系对抗"
        },
        "ending": {
            "name": "结局",
            "chapters_ratio": 0.25,  # 占全书25%
            "conflict_level": "全局危机",
            "stakes": "天下/世界命运",
            "description": "终极矛盾爆发，完成闭环"
        }
    }
    
    # 双线类型
    DUAL_STORYLINE_TYPES = {
        "bright": {
            "name": "明线",
            "focus": "表层事件（古玩鉴定冒险）"
        },
        "dark": {
            "name": "暗线",
            "focus": "核心真相（家族秘密和阴谋）"
        }
    }
    
    # 伏笔层级
    FORESHADOWING_LAYERS = {
        "short": {"max_chapters": 3, "description": "短伏笔，2-3章回收"},
        "medium": {"max_chapters": 20, "description": "中伏笔，10-20章回收"},
        "long": {"max_chapters": 999, "description": "长伏笔，全书回收"}
    }
    
    def __init__(self, total_chapters: int = 40):
        """
        初始化规划器
        
        Args:
            total_chapters: 预计总章节数
        """
        self.total_chapters = total_chapters
        self.phase_boundaries = self._calculate_phase_boundaries()
        
    def _calculate_phase_boundaries(self) -> Dict[str, Dict]:
        """计算各阶段的章节边界"""
        boundaries = {}
        current_chapter = 1
        
        for phase_key, phase_info in self.STORY_PHASES.items():
            phase_chapters = int(self.total_chapters * phase_info["chapters_ratio"])
            boundaries[phase_key] = {
                "start": current_chapter,
                "end": current_chapter + phase_chapters - 1,
                "chapters_count": phase_chapters
            }
            current_chapter += phase_chapters
        
        return boundaries
    
    def get_current_phase(self, chapter_number: int) -> Dict[str, Any]:
        """
        获取当前章节所在的剧情阶段
        
        Args:
            chapter_number: 章节号
        
        Returns:
            阶段信息
        """
        for phase_key, boundary in self.phase_boundaries.items():
            if boundary["start"] <= chapter_number <= boundary["end"]:
                phase_info = self.STORY_PHASES[phase_key].copy()
                phase_info["chapter_number"] = chapter_number
                phase_info["progress_in_phase"] = (
                    (chapter_number - boundary["start"]) / boundary["chapters_count"]
                )
                phase_info["is_phase_start"] = (chapter_number == boundary["start"])
                phase_info["is_phase_end"] = (chapter_number == boundary["end"])
                return phase_info
        
        # 如果超出范围，返回结局阶段
        return self.STORY_PHASES["ending"].copy()
    
    def get_conflict_escalation_guidance(self, chapter_number: int) -> str:
        """
        获取矛盾升级指导
        
        Args:
            chapter_number: 章节号
        
        Returns:
            升级指导文本
        """
        phase = self.get_current_phase(chapter_number)
        
        guidance = f"""
【剧情阶段】：{phase['name']}
【阶段描述】：{phase['description']}
【冲突级别】：{phase['conflict_level']}
【赌注范围】：{phase['stakes']}
【阶段进度】：{phase.get('progress_in_phase', 0) * 100:.0f}%

【矛盾升级要求】：
{self._get_phase_specific_guidance(phase)}
"""
        return guidance
    
    def _get_phase_specific_guidance(self, phase: Dict) -> str:
        """获取阶段特定的升级指导"""
        phase_name = phase["name"]
        
        if phase_name == "开端":
            return """
1. 冲突焦点：个人层面的危机和目标
2. 赌注范围：主角个人或身边人的安危
3. 反派威胁：初露锋芒，但还未完全展现
4. 主角状态：觉醒异能，开始了解真相
5. 升级方向：从个人危机向局部危机过渡
"""
        elif phase_name == "中段":
            return """
1. 冲突焦点：组织/体系层面的对抗
2. 赌注范围：团队、朋友、信念的存亡
3. 反派威胁：全力出击，给主角造成重大损失
4. 主角状态：能力提升，但面临更大挑战
5. 升级方向：从局部危机向全局危机过渡
"""
        else:  # 结局
            return """
1. 冲突焦点：世界观/终极真相的对抗
2. 赌注范围：全城/天下/世界的命运
3. 反派威胁：终极底牌，不死不休
4. 主角状态：完成蜕变，直面终极挑战
5. 升级方向：解决终极矛盾，完成闭环
"""
    
    def get_dual_storyline_plan(self, chapter_number: int) -> Dict[str, Any]:
        """
        获取双层故事线规划
        
        Args:
            chapter_number: 章节号
        
        Returns:
            双线规划
        """
        phase = self.get_current_phase(chapter_number)
        
        # 每3章必须有一次双线交汇
        needs_intersection = chapter_number % 3 == 0
        
        # 根据阶段确定双线比重
        if phase["name"] == "开端":
            bright_focus = 0.7  # 明线为主
            dark_focus = 0.3
        elif phase["name"] == "中段":
            bright_focus = 0.5  # 平衡
            dark_focus = 0.5
        else:  # 结局
            bright_focus = 0.3  # 暗线为主
            dark_focus = 0.7
        
        return {
            "chapter_number": chapter_number,
            "phase": phase["name"],
            "needs_intersection": needs_intersection,
            "bright_line_focus": bright_focus,
            "dark_line_focus": dark_focus,
            "guidance": self._get_dual_storyline_guidance(needs_intersection, phase)
        }
    
    def _get_dual_storyline_guidance(self, needs_intersection: bool, phase: Dict) -> str:
        """获取双线指导"""
        guidance = ""
        
        if needs_intersection:
            guidance += """
【双线交汇要求】：
本章必须包含明暗线的交汇点！

交汇方式：
1. 明线事件直接关联暗线真相
2. 暗线伏笔影响明线发展
3. 让读者产生"原来如此"的爽感
"""
        
        phase_name = phase["name"]
        if phase_name == "开端":
            guidance += """
【开端阶段双线重点】：
- 明线：建立主角的日常生活，引出异能觉醒
- 暗线：埋下十二年前事件的伏笔，暗示阴谋存在
- 咬合：明线的每个发现都指向暗线的谜团
"""
        elif phase_name == "中段":
            guidance += """
【中段阶段双线重点】：
- 明线：主角深入调查，遭遇重重阻碍
- 暗线：真相逐渐浮出，但仍有重大谜团
- 咬合：明线的突破都由暗线的进展推动
"""
        else:  # 结局
            guidance += """
【结局阶段双线重点】：
- 明线：主角直面终极反派，解决核心冲突
- 暗线：十二年前真相大白，家族秘密揭开
- 咬合：双线汇合，共同推向大高潮
"""
        
        return guidance
    
    def get_foreshadowing_plan(self, chapter_number: int, 
                               active_foreshadowing: List[Dict]) -> Dict[str, Any]:
        """
        获取伏笔回收计划
        
        Args:
            chapter_number: 章节号
            active_foreshadowing: 当前活跃的伏笔列表
        
        Returns:
            伏笔计划
        """
        # 分类活跃伏笔
        categorized = {
            "short": [],
            "medium": [],
            "long": []
        }
        
        for fs in active_foreshadowing:
            planted_chapter = fs.get("planted_chapter", chapter_number)
            chapters_elapsed = chapter_number - planted_chapter
            
            if chapters_elapsed <= self.FORESHADOWING_LAYERS["short"]["max_chapters"]:
                categorized["short"].append(fs)
            elif chapters_elapsed <= self.FORESHADOWING_LAYERS["medium"]["max_chapters"]:
                categorized["medium"].append(fs)
            else:
                categorized["long"].append(fs)
        
        # 检查哪些伏笔需要回收
        should_recycle = []
        for layer, max_chapters in [
            ("short", 3),
            ("medium", 20),
            ("long", 999)
        ]:
            for fs in categorized[layer]:
                planted_chapter = fs.get("planted_chapter", 1)
                if chapter_number - planted_chapter >= max_chapters:
                    should_recycle.append(fs)
        
        return {
            "chapter_number": chapter_number,
            "categorized_foreshadowing": categorized,
            "should_recycle": should_recycle,
            "should_plant_new": len(should_recycle) > 0,  # 回收后需要埋新伏笔
            "guidance": self._get_foreshadowing_guidance(categorized, should_recycle)
        }
    
    def _get_foreshadowing_guidance(self, categorized: Dict, should_recycle: List) -> str:
        """获取伏笔指导"""
        guidance = f"""
【伏笔状态】：
- 短伏笔：{len(categorized['short'])}个活跃
- 中伏笔：{len(categorized['medium'])}个活跃
- 长伏笔：{len(categorized['long'])}个活跃
"""
        
        if should_recycle:
            guidance += f"""
【需要回收的伏笔】：
本章必须回收以下{len(should_recycle)}个伏笔：
"""
            for fs in should_recycle:
                guidance += f"- {fs.get('content', '未知伏笔')}\n"
        
        guidance += """
【伏笔管理规则】：
1. 短伏笔：2-3章内回收，维持单章爽感
2. 中伏笔：10-20章回收，推动阶段高潮
3. 长伏笔：全书回收，完成闭环
4. 回收一个伏笔后，可以埋下新的伏笔
"""
        
        return guidance
    
    def get_progression_summary(self, chapter_number: int) -> str:
        """获取完整的推进规划摘要"""
        phase = self.get_current_phase(chapter_number)
        dual_plan = self.get_dual_storyline_plan(chapter_number)
        
        summary = f"""
{'='*50}
第{chapter_number}章 故事线推进规划
{'='*50}

【剧情阶段】：{phase['name']} ({phase['chapters_ratio']*100:.0f}%)
【阶段进度】：{phase.get('progress_in_phase', 0)*100:.0f}%
【冲突级别】：{phase['conflict_level']}
【赌注范围】：{phase['stakes']}

【双线规划】：
- 明线焦点：{dual_plan['bright_line_focus']*100:.0f}%
- 暗线焦点：{dual_plan['dark_line_focus']*100:.0f}%
- 是否需要交汇：{'是' if dual_plan['needs_intersection'] else '否'}
"""
        return summary


def get_progression_guidance(chapter_number: int, total_chapters: int = 40) -> str:
    """获取推进指导的便捷函数"""
    planner = StorylineProgressionPlanner(total_chapters)
    return planner.get_progression_summary(chapter_number)
