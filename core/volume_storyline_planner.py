"""
VolumeStorylinePlanner - 卷剧情规划器

核心职责:
1. 卷剧情规划 - 为每卷生成详细的剧情规划
2. 卷内节奏控制 - 管理卷内章节的节奏分布
3. 卷间衔接管理 - 确保卷与卷之间的连贯性
4. 卷高潮设计 - 规划卷级别的高潮点

基于现有StorylineProgressionPlanner的增强，专注于卷级别的规划

每卷结构:
- 开端 (25%): 建立卷基调，引入核心冲突
- 中段 (50%): 展开冲突，逐步升级
- 结尾 (25%): 解决核心冲突，留下钩子
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("volume_storyline_planner")


@dataclass
class VolumeArc:
    """卷故事弧"""
    volume_number: int
    arc_type: str  # "setup", "confrontation", "resolution"
    main_conflict: str
    main_goal: str
    sub_goals: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)
    planned_reveals: List[Dict] = field(default_factory=list)


@dataclass
class ChapterBeat:
    """章节节奏点"""
    chapter_in_volume: int
    beat_type: str  # "setup", "rising", "climax", "falling", "resolution"
    description: str
    rhythm_type: str  # "缓冲", "升级", "强推"
    foreshadowing_recycled: List[str] = field(default_factory=list)
    foreshadowing_planted: List[str] = field(default_factory=list)
    is_key_chapter: bool = False


@dataclass
class VolumeStorylinePlan:
    """卷剧情规划"""
    volume_number: int
    arc: VolumeArc
    total_chapters: int
    title: str = ""
    chapter_beats: List[ChapterBeat] = field(default_factory=list)
    climax_chapters: List[int] = field(default_factory=list)
    ending_hook: str = ""
    connection_to_previous: str = ""
    connection_to_next: str = ""


class VolumeStorylinePlanner:
    """
    卷剧情规划器

    核心功能:
    1. 卷剧情规划生成
    2. 卷内节奏设计
    3. 卷高潮点规划
    4. 卷间衔接设计

    使用方式:
    ```python
    planner = VolumeStorylinePlanner()

    # 生成卷剧情规划
    plan = planner.generate_volume_plan(
        volume_number=1,
        total_novel_chapters=1000,
        previous_volume_summary="上卷摘要",
        novel_theme="探险"
    )

    # 获取章节节奏设计
    beat = planner.get_chapter_beat(1, 10)
    ```
    """

    # 卷内章节节奏分布
    VOLUME_RHYTHM_DISTRIBUTION = {
        1: {"type": "缓冲", "weight": 0.15},   # 卷开头需要缓冲
        2: {"type": "升级", "weight": 0.20},
        3: {"type": "强推", "weight": 0.15},   # 小高潮
        4: {"type": "缓冲", "weight": 0.10},
        5: {"type": "升级", "weight": 0.15},
        6: {"type": "强推", "weight": 0.25},   # 卷高潮
    }

    def __init__(self, chapters_per_volume: int = 40):
        """
        初始化卷剧情规划器

        Args:
            chapters_per_volume: 每卷章节数
        """
        self.chapters_per_volume = chapters_per_volume

    def generate_volume_plan(self,
                              volume_number: int,
                              total_novel_chapters: int = 1000,
                              previous_volume_summary: str = "",
                              novel_theme: str = "",
                              user_requirements: str = "") -> VolumeStorylinePlan:
        """
        生成卷剧情规划

        Args:
            volume_number: 卷号
            total_novel_chapters: 小说总章节数
            previous_volume_summary: 上卷摘要
            novel_theme: 小说主题
            user_requirements: 用户需求

        Returns:
            卷剧情规划
        """
        total_volumes = (total_novel_chapters + self.chapters_per_volume - 1) // self.chapters_per_volume

        arc_type = self._determine_arc_type(volume_number, total_volumes)

        arc = self._create_volume_arc(
            volume_number=volume_number,
            arc_type=arc_type,
            total_volumes=total_volumes,
            novel_theme=novel_theme,
            user_requirements=user_requirements
        )

        chapter_beats = self._design_chapter_beats(volume_number, arc)

        climax_chapters = self._identify_climax_points(chapter_beats)

        connection_to_previous = self._create_previous_connection(
            volume_number, previous_volume_summary, arc
        )

        connection_to_next = self._create_next_connection(volume_number, total_volumes, arc)

        title = self._generate_volume_title(volume_number, arc)

        return VolumeStorylinePlan(
            volume_number=volume_number,
            arc=arc,
            total_chapters=self.chapters_per_volume,
            title=title,
            chapter_beats=chapter_beats,
            climax_chapters=climax_chapters,
            ending_hook=self._generate_ending_hook(arc),
            connection_to_previous=connection_to_previous,
            connection_to_next=connection_to_next
        )

    def _determine_arc_type(self, volume_number: int, total_volumes: int) -> str:
        """确定卷故事弧类型"""
        ratio = volume_number / total_volumes

        if ratio <= 0.25:
            return "setup"
        elif ratio <= 0.75:
            return "confrontation"
        else:
            return "resolution"

    def _create_volume_arc(self,
                           volume_number: int,
                           arc_type: str,
                           total_volumes: int,
                           novel_theme: str,
                           user_requirements: str) -> VolumeArc:
        """创建卷故事弧"""
        if arc_type == "setup":
            main_conflict = self._generate_setup_conflict(volume_number, novel_theme)
            main_goal = "建立主角目标，引入核心矛盾"
            sub_goals = [
                "展示主角日常生活和能力",
                "引入核心配角和对立角色",
                "埋设全书级别的伏笔"
            ]
        elif arc_type == "confrontation":
            main_conflict = self._generate_confrontation_conflict(volume_number, novel_theme)
            main_goal = "深化核心冲突，展现主角成长"
            sub_goals = [
                "升级主要矛盾",
                "展现主角能力提升",
                "揭示更多背景和真相"
            ]
        else:
            main_conflict = self._generate_resolution_conflict(volume_number, novel_theme)
            main_goal = "解决核心冲突，完成全书高潮"
            sub_goals = [
                "终极对决",
                "所有伏笔回收",
                "完美结局"
            ]

        planned_reveals = self._plan_reveals(volume_number, arc_type)

        return VolumeArc(
            volume_number=volume_number,
            arc_type=arc_type,
            main_conflict=main_conflict,
            main_goal=main_goal,
            sub_goals=sub_goals,
            planned_reveals=planned_reveals
        )

    def _generate_setup_conflict(self, volume_number: int, theme: str) -> str:
        """生成开篇卷冲突"""
        conflicts = {
            1: f"主角意外获得{theme}能力，必须面对随之而来的挑战",
            2: f"主角卷入{theme}世界的阴谋，必须证明自己",
            3: f"主角发现{theme}背后的秘密，必须找到真相",
        }
        return conflicts.get(volume_number, f"第{volume_number}卷核心冲突")

    def _generate_confrontation_conflict(self, volume_number: int, theme: str) -> str:
        """生成中段卷冲突"""
        return f"主角深入{theme}核心，面对越来越强大的对手和更复杂的真相"

    def _generate_resolution_conflict(self, volume_number: int, theme: str) -> str:
        """生成结局卷冲突"""
        return f"主角必须最终解决{theme}的终极威胁，完成自己的使命"

    def _plan_reveals(self, volume_number: int, arc_type: str) -> List[Dict]:
        """规划信息揭示"""
        reveals = []

        if arc_type == "setup":
            reveals.extend([
                {"reveal_type": "能力展示", "chapter_position": 0.2, "description": "主角能力的初次展示"},
                {"reveal_type": "世界观", "chapter_position": 0.4, "description": "引入{theme}世界观"},
                {"reveal_type": "对立角色", "chapter_position": 0.6, "description": "核心对手登场"}
            ])
        elif arc_type == "confrontation":
            reveals.extend([
                {"reveal_type": "能力升级", "chapter_position": 0.3, "description": "主角能力突破"},
                {"reveal_type": "真相碎片", "chapter_position": 0.5, "description": "背景真相逐渐揭露"},
                {"reveal_type": "重大损失", "chapter_position": 0.8, "description": "主角遭遇重大挫折"}
            ])
        else:
            reveals.extend([
                {"reveal_type": "终极真相", "chapter_position": 0.3, "description": "全部真相大白"},
                {"reveal_type": "终极对决", "chapter_position": 0.6, "description": "与终极反派决战"},
                {"reveal_type": "完美结局", "chapter_position": 0.9, "description": "所有故事线收束"}
            ])

        return reveals

    def _design_chapter_beats(self, volume_number: int, arc: VolumeArc) -> List[ChapterBeat]:
        """设计章节节奏"""
        beats = []

        for i in range(1, self.chapters_per_volume + 1):
            ratio = i / self.chapters_per_volume

            if ratio <= 0.15:
                beat_type = "setup"
                rhythm_type = "缓冲"
                description = "卷开头，建立基调"
            elif ratio <= 0.35:
                beat_type = "rising"
                rhythm_type = "升级"
                description = "冲突展开，逐步升级"
            elif ratio <= 0.45:
                beat_type = "rising"
                rhythm_type = "强推"
                description = "第一次小高潮"
            elif ratio <= 0.70:
                beat_type = "rising"
                rhythm_type = "缓冲"
                description = "缓冲调整，为高潮做准备"
            elif ratio <= 0.85:
                beat_type = "climax"
                rhythm_type = "升级"
                description = "高潮准备，矛盾激化"
            else:
                beat_type = "resolution"
                rhythm_type = "强推"
                description = "卷高潮与收尾"

            is_key = beat_type == "climax" and ratio >= 0.80

            beat = ChapterBeat(
                chapter_in_volume=i,
                beat_type=beat_type,
                description=description,
                rhythm_type=rhythm_type,
                is_key_chapter=is_key
            )
            beats.append(beat)

        return beats

    def _identify_climax_points(self, beats: List[ChapterBeat]) -> List[int]:
        """识别高潮章节"""
        climax_chapters = [b.chapter_in_volume for b in beats if b.is_key_chapter]

        if not climax_chapters:
            climax_chapters = [int(self.chapters_per_volume * 0.85)]

        minor_climaxes = [
            b.chapter_in_volume for b in beats
            if b.beat_type == "climax" and not b.is_key_chapter
        ]

        return sorted(climax_chapters + minor_climaxes)

    def _create_previous_connection(self,
                                     volume_number: int,
                                     previous_summary: str,
                                     arc: VolumeArc) -> str:
        """创建与上卷的衔接"""
        if volume_number == 1:
            return "本卷是小说开篇，直接开始"

        return f"承接上卷结尾，{previous_summary[:50] if previous_summary else '继续发展'}"

    def _create_next_connection(self,
                                 volume_number: int,
                                 total_volumes: int,
                                 arc: VolumeArc) -> str:
        """创建与下卷的衔接"""
        if volume_number == total_volumes:
            return "本卷是最后一卷，需要完成全书结局"

        return f"为第{volume_number + 1}卷埋下伏笔，引入新的冲突或升级"

    def _generate_volume_title(self, volume_number: int, arc: VolumeArc) -> str:
        """生成卷标题"""
        if arc.arc_type == "setup":
            return f"第一卷：觉醒"
        elif arc.arc_type == "confrontation":
            if arc.arc_type == "confrontation":
                stage = (volume_number - 1) % 3
                titles = ["崛起", "深化", "抉择"]
                return f"第{volume_number}卷：{titles[stage]}"
        else:
            return f"第{volume_number}卷：终章"

        return f"第{volume_number}卷"

    def _generate_ending_hook(self, arc: VolumeArc) -> str:
        """生成结尾钩子"""
        if arc.arc_type == "setup":
            return "就在主角以为一切结束的时候，更大的危机悄然来临..."
        elif arc.arc_type == "confrontation":
            return "主角发现了震惊的真相，但更大的挑战还在前方..."
        else:
            return "最终决战即将开始，主角必须做出最终抉择..."

    def get_chapter_beat(self,
                         volume_number: int,
                         chapter_in_volume: int) -> Optional[ChapterBeat]:
        """
        获取指定章节的节奏设计

        Args:
            volume_number: 卷号
            chapter_in_volume: 卷内章节号

        Returns:
            章节节奏点
        """
        if chapter_in_volume < 1 or chapter_in_volume > self.chapters_per_volume:
            return None

        ratio = chapter_in_volume / self.chapters_per_volume

        if ratio <= 0.15:
            beat_type = "setup"
            rhythm_type = "缓冲"
            description = "卷开头，建立基调"
        elif ratio <= 0.35:
            beat_type = "rising"
            rhythm_type = "升级"
            description = "冲突展开，逐步升级"
        elif ratio <= 0.45:
            beat_type = "rising"
            rhythm_type = "强推"
            description = "第一次小高潮"
        elif ratio <= 0.70:
            beat_type = "rising"
            rhythm_type = "缓冲"
            description = "缓冲调整，为高潮做准备"
        elif ratio <= 0.85:
            beat_type = "climax"
            rhythm_type = "升级"
            description = "高潮准备，矛盾激化"
        else:
            beat_type = "resolution"
            rhythm_type = "强推"
            description = "卷高潮与收尾"

        is_key = beat_type == "climax" and ratio >= 0.80

        return ChapterBeat(
            chapter_in_volume=chapter_in_volume,
            beat_type=beat_type,
            description=description,
            rhythm_type=rhythm_type,
            is_key_chapter=is_key
        )

    def get_volume_guidance(self,
                            volume_number: int,
                            chapter_in_volume: int,
                            total_novel_chapters: int = 1000) -> str:
        """
        获取卷写作指导

        Args:
            volume_number: 卷号
            chapter_in_volume: 卷内章节号
            total_novel_chapters: 小说总章节数

        Returns:
            写作指导字符串
        """
        beat = self.get_chapter_beat(volume_number, chapter_in_volume)
        if not beat:
            return "章节号超出范围"

        guidance_parts = []
        guidance_parts.append(f"【卷章节信息】第{volume_number}卷 第{chapter_in_volume}章")

        guidance_parts.append(f"【节奏类型】{beat.rhythm_type}")
        guidance_parts.append(f"【节拍类型】{beat.beat_type}")
        guidance_parts.append(f"【章节描述】{beat.description}")

        if beat.is_key_chapter:
            guidance_parts.append("【关键章节】本章是卷高潮点，需要重点描写!")

        guidance_parts.append(self._get_beat_writing_guidance(beat))

        return "\n".join(guidance_parts)

    def _get_beat_writing_guidance(self, beat: ChapterBeat) -> str:
        """获取节拍写作指导"""
        if beat.beat_type == "setup":
            return """
【开篇节拍写作要求】
1. 建立本章场景和人物状态
2. 引入本章节的目标或小冲突
3. 为后续发展做铺垫
4. 保持适当的节奏，不要过于平淡"""
        elif beat.beat_type == "rising":
            if beat.rhythm_type == "缓冲":
                return """
【缓冲节拍写作要求】
1. 放缓节奏，着重人物内心
2. 深化人物关系和情感
3. 可以进行日常互动或内心独白
4. 为接下来的高潮做铺垫"""
            else:
                return """
【升级节拍写作要求】
1. 推进主要冲突
2. 展现人物能力和成长
3. 适当增加紧张感
4. 埋设新的伏笔"""
        elif beat.beat_type == "climax":
            return """
【高潮节拍写作要求】
1. 本章必须有一个明确的情感/事件高点
2. 冲突达到当前阶段的顶点
3. 重要信息揭示或关键决定
4. 给读者强烈的阅读满足感"""
        else:
            return """
【收尾节拍写作要求】
1. 解决本章主要冲突
2. 自然过渡到下章
3. 为卷高潮做最后准备
4. 可以留下小钩子增加期待"""

    def export_volume_plan(self, plan: VolumeStorylinePlan) -> Dict[str, Any]:
        """导出卷规划为字典"""
        return {
            "volume_number": plan.volume_number,
            "title": plan.title,
            "arc": asdict_arc(plan.arc),
            "total_chapters": plan.total_chapters,
            "chapter_beats": [asdict_beat(b) for b in plan.chapter_beats],
            "climax_chapters": plan.climax_chapters,
            "ending_hook": plan.ending_hook,
            "connection_to_previous": plan.connection_to_previous,
            "connection_to_next": plan.connection_to_next
        }

    def import_volume_plan(self, plan_dict: Dict[str, Any]) -> VolumeStorylinePlan:
        """从字典导入卷规划"""
        return VolumeStorylinePlan(
            volume_number=plan_dict["volume_number"],
            arc=import_arc(plan_dict["arc"]),
            total_chapters=plan_dict.get("total_chapters", self.chapters_per_volume),
            title=plan_dict.get("title", ""),
            chapter_beats=[import_beat(b) for b in plan_dict.get("chapter_beats", [])],
            climax_chapters=plan_dict.get("climax_chapters", []),
            ending_hook=plan_dict.get("ending_hook", ""),
            connection_to_previous=plan_dict.get("connection_to_previous", ""),
            connection_to_next=plan_dict.get("connection_to_next", "")
        )


def asdict_arc(arc: VolumeArc) -> Dict[str, Any]:
    """将VolumeArc转换为字典"""
    return {
        "volume_number": arc.volume_number,
        "arc_type": arc.arc_type,
        "main_conflict": arc.main_conflict,
        "main_goal": arc.main_goal,
        "sub_goals": arc.sub_goals,
        "key_events": arc.key_events,
        "planned_reveals": arc.planned_reveals
    }


def asdict_beat(beat: ChapterBeat) -> Dict[str, Any]:
    """将ChapterBeat转换为字典"""
    return {
        "chapter_in_volume": beat.chapter_in_volume,
        "beat_type": beat.beat_type,
        "description": beat.description,
        "rhythm_type": beat.rhythm_type,
        "foreshadowing_recycled": beat.foreshadowing_recycled,
        "foreshadowing_planted": beat.foreshadowing_planted,
        "is_key_chapter": beat.is_key_chapter
    }


def import_arc(arc_dict: Dict[str, Any]) -> VolumeArc:
    """从字典导入VolumeArc"""
    return VolumeArc(
        volume_number=arc_dict["volume_number"],
        arc_type=arc_dict.get("arc_type", "setup"),
        main_conflict=arc_dict.get("main_conflict", ""),
        main_goal=arc_dict.get("main_goal", ""),
        sub_goals=arc_dict.get("sub_goals", []),
        key_events=arc_dict.get("key_events", []),
        planned_reveals=arc_dict.get("planned_reveals", [])
    )


def import_beat(beat_dict: Dict[str, Any]) -> ChapterBeat:
    """从字典导入ChapterBeat"""
    return ChapterBeat(
        chapter_in_volume=beat_dict["chapter_in_volume"],
        beat_type=beat_dict.get("beat_type", "rising"),
        description=beat_dict.get("description", ""),
        rhythm_type=beat_dict.get("rhythm_type", "缓冲"),
        foreshadowing_recycled=beat_dict.get("foreshadowing_recycled", []),
        foreshadowing_planted=beat_dict.get("foreshadowing_planted", []),
        is_key_chapter=beat_dict.get("is_key_chapter", False)
    )


if __name__ == "__main__":
    print("=== VolumeStorylinePlanner 测试 ===\n")

    planner = VolumeStorylinePlanner(chapters_per_volume=40)

    print("生成第1卷规划:")
    plan = planner.generate_volume_plan(
        volume_number=1,
        total_novel_chapters=1000,
        previous_volume_summary="",
        novel_theme="探险"
    )

    print(f"卷标题: {plan.title}")
    print(f"卷弧类型: {plan.arc.arc_type}")
    print(f"主要冲突: {plan.arc.main_conflict}")
    print(f"主要目标: {plan.arc.main_goal}")
    print(f"高潮章节: {plan.climax_chapters}")
    print(f"结尾钩子: {plan.ending_hook}")

    print("\n卷内章节节奏示例:")
    for i in [1, 10, 20, 30, 40]:
        beat = planner.get_chapter_beat(1, i)
        print(f"  第{i}章: {beat.beat_type} / {beat.rhythm_type} / {'⭐关键' if beat.is_key_chapter else ''}")

    print("\n章节写作指导 (第25章):")
    guidance = planner.get_volume_guidance(1, 25, 1000)
    print(guidance)
