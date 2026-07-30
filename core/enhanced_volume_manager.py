"""
EnhancedVolumeManager - 增强版卷管理器

核心职责:
1. 卷状态进度跟踪 - 实时跟踪每卷的写作状态
2. 卷剧情规划 - 支持卷级别的剧情规划
3. 窗口滑动上下文支持 - 与SlidingWindowContext集成
4. 卷状态持久化 - 保存和恢复卷进度

基于现有VolumeManager的增强版本
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum

from utils.logger import get_logger

logger = get_logger("enhanced_volume_manager")


class VolumePhase(Enum):
    """卷内阶段"""
    PLANNING = "planning"           # 规划中
    WRITING_START = "writing_start" # 开始写作
    WRITING_MIDDLE = "writing_middle" # 写作中段
    WRITING_CLIMAX = "writing_climax" # 高潮阶段
    WRITING_END = "writing_end"     # 收尾阶段
    COMPLETED = "completed"          # 已完成


class VolumeStatus(Enum):
    """卷状态"""
    NOT_STARTED = "not_started"     # 未开始
    IN_PROGRESS = "in_progress"     # 写作中
    REVIEWING = "reviewing"         # 审核中
    COMPLETED = "completed"         # 已完成
    ON_HOLD = "on_hold"             # 暂停


@dataclass
class VolumeProgress:
    """卷进度"""
    volume_number: int
    total_chapters: int
    written_chapters: int
    planned_chapters: int
    start_chapter: int
    end_chapter: int
    progress_percentage: float
    phase: str
    word_count: int = 0
    estimated_word_count: int = 0


@dataclass
class ChapterInVolume:
    """卷内章节信息"""
    chapter_number: int
    chapter_in_volume: int
    title: str = ""
    word_count: int = 0
    is_key_chapter: bool = False
    rhythm_type: str = ""
    summary: str = ""
    foreshadowing_recycled: List[str] = field(default_factory=list)
    foreshadowing_planted: List[str] = field(default_factory=list)
    key_events: List[str] = field(default_factory=list)


@dataclass
class VolumeStoryline:
    """卷剧情线"""
    volume_number: int
    main_conflict: str = ""
    main_goal: str = ""
    sub_goals: List[str] = field(default_factory=list)
    key_climax_points: List[int] = field(default_factory=list)  # 章节号列表
    planned_reveals: List[Dict] = field(default_factory=list)
    character_arcs: Dict[str, str] = field(default_factory=dict)
    foreshadowing_plan: List[Dict] = field(default_factory=list)


class EnhancedVolumeManager:
    """
    增强版卷管理器

    核心功能:
    1. 卷状态进度跟踪 - 实时跟踪每卷的详细进度
    2. 卷剧情规划 - 支持卷级别的剧情规划
    3. 窗口滑动支持 - 提供滑动窗口所需的信息
    4. 跨卷衔接管理 - 确保卷与卷之间的连贯性

    使用方式:
    ```python
    manager = EnhancedVolumeManager(data_manager=data_manager)

    # 获取增强的卷信息
    volume_info = manager.get_enhanced_volume_info(novel_id, chapter_num)

    # 更新卷进度
    manager.update_chapter_in_volume(novel_id, chapter_num, chapter_data)

    # 获取卷剧情规划
    storyline = manager.get_volume_storyline(novel_id, volume_number)
    ```
    """

    DEFAULT_CHAPTERS_PER_VOLUME = 40
    DEFAULT_WORDS_PER_CHAPTER = 2500

    def __init__(self, data_manager: Any = None):
        self.data_manager = data_manager

    def get_enhanced_volume_info(self,
                                  novel_id: str,
                                  chapter_number: int,
                                  chapters_per_volume: int = None) -> Dict[str, Any]:
        """
        获取增强的卷信息

        包含:
        - 基本卷信息
        - 当前卷的详细进度
        - 前一卷的摘要
        - 下一卷的预览（如果存在）

        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            chapters_per_volume: 每卷章节数

        Returns:
            增强的卷信息
        """
        if chapters_per_volume is None:
            chapters_per_volume = self.DEFAULT_CHAPTERS_PER_VOLUME

        volume_number = ((chapter_number - 1) // chapters_per_volume) + 1
        chapter_in_volume = ((chapter_number - 1) % chapters_per_volume) + 1
        volume_start = (volume_number - 1) * chapters_per_volume + 1
        volume_end = volume_number * chapters_per_volume

        base_info = {
            "novel_id": novel_id,
            "chapter_number": chapter_number,
            "volume_number": volume_number,
            "chapter_in_volume": chapter_in_volume,
            "chapters_per_volume": chapters_per_volume,
            "volume_start": volume_start,
            "volume_end": volume_end,
            "volume_progress": chapter_in_volume / chapters_per_volume,
            "volume_phase": self._get_volume_phase(chapter_in_volume, chapters_per_volume),
            "is_volume_start": chapter_in_volume == 1,
            "is_volume_end": chapter_in_volume == chapters_per_volume,
            "is_volume_middle": chapter_in_volume == chapters_per_volume // 2,
        }

        volume_state = self._load_volume_state(novel_id, volume_number)
        if volume_state:
            base_info["volume_state"] = volume_state

        written_chapters = self._get_written_chapters_in_volume(novel_id, volume_start, chapter_number)
        base_info["written_chapters"] = written_chapters
        base_info["remaining_chapters"] = chapters_per_volume - chapter_in_volume

        if volume_number > 1:
            prev_summary = self._load_volume_summary(novel_id, volume_number - 1)
            if prev_summary:
                base_info["previous_volume"] = {
                    "number": volume_number - 1,
                    "summary": prev_summary.get("summary", ""),
                    "ending_hook": prev_summary.get("ending_hook", "")
                }

        next_preview = self._generate_next_volume_preview(novel_id, volume_number, volume_state)
        if next_preview:
            base_info["next_volume_preview"] = next_preview

        return base_info

    def _get_volume_phase(self, chapter_in_volume: int, chapters_per_volume: int) -> str:
        """计算卷内阶段"""
        ratio = chapter_in_volume / chapters_per_volume

        if ratio <= 0.15:
            return VolumePhase.WRITING_START.value
        elif ratio <= 0.35:
            return VolumePhase.WRITING_MIDDLE.value
        elif ratio <= 0.75:
            return VolumePhase.WRITING_MIDDLE.value
        elif ratio <= 0.90:
            return VolumePhase.WRITING_CLIMAX.value
        else:
            return VolumePhase.WRITING_END.value

    def _load_volume_state(self, novel_id: str, volume_number: int) -> Optional[Dict]:
        """加载卷状态"""
        state_path = self._get_volume_state_path(novel_id, volume_number)
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载卷状态失败: {e}")
        return None

    def _save_volume_state(self, novel_id: str, volume_number: int, state: Dict) -> bool:
        """保存卷状态"""
        try:
            state_path = self._get_volume_state_path(novel_id, volume_number)
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            state["updated_at"] = datetime.now().isoformat()
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存卷状态失败: {e}")
            return False

    def _get_volume_state_path(self, novel_id: str, volume_number: int) -> str:
        """获取卷状态文件路径"""
        base_dir = self.data_manager.novels_dir if self.data_manager else "data/novels"
        return os.path.join(base_dir, novel_id, f"volume_{volume_number:03d}_state.json")

    def _get_written_chapters_in_volume(self, novel_id: str,
                                         volume_start: int,
                                         current_chapter: int) -> List[int]:
        """获取卷内已完成的章节列表"""
        written = []
        for ch in range(volume_start, current_chapter):
            if self._chapter_exists(novel_id, ch):
                written.append(ch)
        return written

    def _chapter_exists(self, novel_id: str, chapter_number: int) -> bool:
        """检查章节是否存在"""
        if not self.data_manager:
            return False
        try:
            chapter_data = self.data_manager.load_chapter(novel_id, chapter_number)
            return chapter_data is not None and len(str(chapter_data)) > 100
        except Exception:
            return False

    def _load_volume_summary(self, novel_id: str, volume_number: int) -> Optional[Dict]:
        """加载卷摘要"""
        summary_path = self._get_volume_summary_path(novel_id, volume_number)
        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _get_volume_summary_path(self, novel_id: str, volume_number: int) -> str:
        """获取卷摘要路径"""
        base_dir = self.data_manager.novels_dir if self.data_manager else "data/novels"
        return os.path.join(base_dir, novel_id, f"volume_{volume_number:03d}_summary.json")

    def _generate_next_volume_preview(self, novel_id: str,
                                       current_volume: int,
                                       current_state: Optional[Dict]) -> Optional[Dict]:
        """生成下一卷的预览信息"""
        next_volume = current_volume + 1
        next_summary = self._load_volume_summary(novel_id, next_volume)

        if next_summary:
            return {
                "number": next_volume,
                "planned_start": (next_volume - 1) * self.DEFAULT_CHAPTERS_PER_VOLUME + 1,
                "title": next_summary.get("title", ""),
                "main_conflict": next_summary.get("main_conflict", ""),
                "planned_chapters": next_summary.get("planned_chapters", self.DEFAULT_CHAPTERS_PER_VOLUME)
            }

        if current_state:
            next_goals = current_state.get("next_volume_goals", [])
            if next_goals:
                return {
                    "number": next_volume,
                    "planned_start": (next_volume - 1) * self.DEFAULT_CHAPTERS_PER_VOLUME + 1,
                    "planned_goals": next_goals
                }

        return None

    def update_chapter_in_volume(self,
                                  novel_id: str,
                                  chapter_number: int,
                                  chapter_data: Dict[str, Any],
                                  chapters_per_volume: int = None) -> bool:
        """
        更新卷内章节信息

        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            chapter_data: 章节数据，包含:
                - title: 章节标题
                - word_count: 字数
                - summary: 摘要
                - rhythm_type: 节奏类型
                - is_key_chapter: 是否关键章节
                - foreshadowing_recycled: 回收的伏笔列表
                - foreshadowing_planted: 新埋的伏笔列表
                - key_events: 关键事件列表
            chapters_per_volume: 每卷章节数

        Returns:
            是否成功
        """
        if chapters_per_volume is None:
            chapters_per_volume = self.DEFAULT_CHAPTERS_PER_VOLUME

        volume_number = ((chapter_number - 1) // chapters_per_volume) + 1

        state = self._load_volume_state(novel_id, volume_number) or {}
        if "chapters" not in state:
            state["chapters"] = {}

        chapter_in_volume = ((chapter_number - 1) % chapters_per_volume) + 1

        state["chapters"][str(chapter_number)] = {
            "chapter_in_volume": chapter_in_volume,
            "title": chapter_data.get("title", ""),
            "word_count": chapter_data.get("word_count", 0),
            "summary": chapter_data.get("summary", ""),
            "rhythm_type": chapter_data.get("rhythm_type", ""),
            "is_key_chapter": chapter_data.get("is_key_chapter", False),
            "foreshadowing_recycled": chapter_data.get("foreshadowing_recycled", []),
            "foreshadowing_planted": chapter_data.get("foreshadowing_planted", []),
            "key_events": chapter_data.get("key_events", []),
            "updated_at": datetime.now().isoformat()
        }

        total_word_count = sum(
            ch.get("word_count", 0)
            for ch in state["chapters"].values()
        )
        state["total_word_count"] = total_word_count
        state["last_updated_chapter"] = chapter_number

        return self._save_volume_state(novel_id, volume_number, state)

    def get_volume_progress(self,
                             novel_id: str,
                             volume_number: int,
                             chapters_per_volume: int = None) -> VolumeProgress:
        """
        获取卷进度

        Args:
            novel_id: 小说ID
            volume_number: 卷号
            chapters_per_volume: 每卷章节数

        Returns:
            卷进度信息
        """
        if chapters_per_volume is None:
            chapters_per_volume = self.DEFAULT_CHAPTERS_PER_VOLUME

        start_chapter = (volume_number - 1) * chapters_per_volume + 1
        end_chapter = volume_number * chapters_per_volume

        state = self._load_volume_state(novel_id, volume_number)
        written_chapters = 0
        word_count = 0
        planned_chapters = chapters_per_volume

        if state and "chapters" in state:
            written_chapters = len(state["chapters"])
            word_count = state.get("total_word_count", 0)

        current_chapter = start_chapter + written_chapters - 1 if written_chapters > 0 else start_chapter

        progress_percentage = written_chapters / chapters_per_volume if chapters_per_volume > 0 else 0

        current_phase = VolumePhase.WRITING_START.value
        if written_chapters > 0:
            ratio = written_chapters / chapters_per_volume
            if ratio <= 0.15:
                current_phase = VolumePhase.WRITING_START.value
            elif ratio <= 0.35:
                current_phase = VolumePhase.WRITING_MIDDLE.value
            elif ratio <= 0.75:
                current_phase = VolumePhase.WRITING_MIDDLE.value
            elif ratio <= 0.90:
                current_phase = VolumePhase.WRITING_CLIMAX.value
            else:
                current_phase = VolumePhase.WRITING_END.value

        return VolumeProgress(
            volume_number=volume_number,
            total_chapters=chapters_per_volume,
            written_chapters=written_chapters,
            planned_chapters=planned_chapters,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            progress_percentage=progress_percentage,
            phase=current_phase,
            word_count=word_count,
            estimated_word_count=chapters_per_volume * self.DEFAULT_WORDS_PER_CHAPTER
        )

    def create_volume_storyline(self,
                                 novel_id: str,
                                 volume_number: int,
                                 storyline_data: Dict[str, Any],
                                 chapters_per_volume: int = None) -> bool:
        """
        创建卷剧情规划

        Args:
            novel_id: 小说ID
            volume_number: 卷号
            storyline_data: 剧情规划数据，包含:
                - main_conflict: 主要冲突
                - main_goal: 主要目标
                - sub_goals: 次要目标列表
                - key_climax_points: 关键高潮点章节列表
                - planned_reveals: 计划揭示的信息
                - character_arcs: 角色弧线
                - foreshadowing_plan: 伏笔计划
            chapters_per_volume: 每卷章节数

        Returns:
            是否成功
        """
        if chapters_per_volume is None:
            chapters_per_volume = self.DEFAULT_CHAPTERS_PER_VOLUME

        state = self._load_volume_state(novel_id, volume_number) or {}

        volume_storyline = VolumeStoryline(
            volume_number=volume_number,
            main_conflict=storyline_data.get("main_conflict", ""),
            main_goal=storyline_data.get("main_goal", ""),
            sub_goals=storyline_data.get("sub_goals", []),
            key_climax_points=storyline_data.get("key_climax_points", []),
            planned_reveals=storyline_data.get("planned_reveals", []),
            character_arcs=storyline_data.get("character_arcs", {}),
            foreshadowing_plan=storyline_data.get("foreshadowing_plan", [])
        )

        state["storyline"] = asdict(volume_storyline)
        state["status"] = VolumeStatus.IN_PROGRESS.value

        return self._save_volume_state(novel_id, volume_number, state)

    def get_volume_storyline(self, novel_id: str, volume_number: int) -> Optional[Dict]:
        """
        获取卷剧情规划

        Args:
            novel_id: 小说ID
            volume_number: 卷号

        Returns:
            卷剧情规划，如果不存在返回None
        """
        state = self._load_volume_state(novel_id, volume_number)
        if state and "storyline" in state:
            return state["storyline"]
        return None

    def get_volume_guidance(self,
                             novel_id: str,
                             chapter_number: int,
                             chapters_per_volume: int = None) -> str:
        """
        获取卷写作指导

        Args:
            novel_id: 小说ID
            chapter_number: 章节号
            chapters_per_volume: 每卷章节数

        Returns:
            写作指导字符串
        """
        volume_info = self.get_enhanced_volume_info(novel_id, chapter_number, chapters_per_volume)

        guidance_parts = []
        guidance_parts.append(f"【卷信息】第{volume_info['volume_number']}卷")
        guidance_parts.append(f"卷内进度：第{volume_info['chapter_in_volume']}章/共{volume_info['chapters_per_volume']}章 ({volume_info['volume_progress']*100:.0f}%)")
        guidance_parts.append(f"当前阶段：{self._get_phase_description(volume_info['volume_phase'])}")

        if volume_info.get("previous_volume"):
            prev = volume_info["previous_volume"]
            guidance_parts.append(f"\n【上卷回顾】{prev.get('summary', '')[:100]}...")
            if prev.get("ending_hook"):
                guidance_parts.append(f"上卷钩子：{prev['ending_hook']}")

        guidance_parts.append(self._get_phase_writing_guidance(volume_info))

        if volume_info.get("next_volume_preview"):
            next_vol = volume_info["next_volume_preview"]
            guidance_parts.append(f"\n【下卷预告】")
            if next_vol.get("title"):
                guidance_parts.append(f"下卷标题：{next_vol['title']}")
            if next_vol.get("main_conflict"):
                guidance_parts.append(f"下卷主线：{next_vol['main_conflict']}")

        return "\n".join(guidance_parts)

    def _get_phase_description(self, phase: str) -> str:
        """获取阶段描述"""
        descriptions = {
            VolumePhase.PLANNING.value: "规划中",
            VolumePhase.WRITING_START.value: "开篇",
            VolumePhase.WRITING_MIDDLE.value: "中段发展",
            VolumePhase.WRITING_CLIMAX.value: "高潮阶段",
            VolumePhase.WRITING_END.value: "收尾阶段",
            VolumePhase.COMPLETED.value: "已完成"
        }
        return descriptions.get(phase, phase)

    def _get_phase_writing_guidance(self, volume_info: Dict) -> str:
        """获取阶段写作指导"""
        phase = volume_info["volume_phase"]
        chapter_in_volume = volume_info["chapter_in_volume"]
        chapters_per_volume = volume_info["chapters_per_volume"]
        ratio = chapter_in_volume / chapters_per_volume

        if phase == VolumePhase.WRITING_START.value:
            return """
【开篇阶段写作要求】
1. 承接上卷结尾，建立本卷基调
2. 引入本卷核心冲突或目标
3. 铺垫本卷的高潮点
4. 注意与上卷人物的衔接"""
        elif phase == VolumePhase.WRITING_MIDDLE.value:
            if ratio < 0.5:
                return """
【中段前期写作要求】
1. 展开本卷核心冲突
2. 深化人物关系
3. 埋设伏笔，为高潮做铺垫
4. 控制节奏，避免过于平淡"""
            else:
                return """
【中段后期写作要求】
1. 矛盾逐步升级
2. 为高潮做最后准备
3. 可以安排一次小高潮
4. 注意节奏变化"""
        elif phase == VolumePhase.WRITING_CLIMAX.value:
            return """
【高潮阶段写作要求】
1. 本卷核心冲突必须解决
2. 安排本卷最大高潮点
3. 完成关键角色弧线
4. 为下卷留下钩子"""
        else:
            return """
【收尾阶段写作要求】
1. 收束本卷主要情节线
2. 完成伏笔回收
3. 为下卷做铺垫
4. 确保章节完整性"""

    def get_all_volumes_status(self, novel_id: str) -> List[Dict]:
        """
        获取所有卷的状态

        Args:
            novel_id: 小说ID

        Returns:
            所有卷的状态列表
        """
        volumes_status = []

        if not self.data_manager:
            return volumes_status

        base_dir = self.data_manager.novels_dir
        novel_dir = os.path.join(base_dir, novel_id)

        if not os.path.exists(novel_dir):
            return volumes_status

        volume_files = [
            f for f in os.listdir(novel_dir)
            if f.startswith("volume_") and f.endswith("_state.json")
        ]

        for vf in volume_files:
            try:
                volume_num = int(vf.split("_")[1])
                with open(os.path.join(novel_dir, vf), 'r', encoding='utf-8') as f:
                    state = json.load(f)

                progress = self.get_volume_progress(novel_id, volume_num)

                volumes_status.append({
                    "volume_number": volume_num,
                    "status": state.get("status", VolumeStatus.NOT_STARTED.value),
                    "progress": asdict(progress),
                    "storyline": state.get("storyline", {}),
                    "updated_at": state.get("updated_at", "")
                })
            except Exception as e:
                logger.error(f"加载卷状态失败 {vf}: {e}")

        volumes_status.sort(key=lambda x: x["volume_number"])
        return volumes_status

    def get_cross_volume_context(self,
                                   novel_id: str,
                                   current_chapter: int,
                                   window_size: int = 5,
                                   chapters_per_volume: int = None) -> Dict[str, Any]:
        """
        获取跨卷上下文（用于滑动窗口）

        Args:
            novel_id: 小说ID
            current_chapter: 当前章节号
            window_size: 窗口大小（前后各多少章）
            chapters_per_volume: 每卷章节数

        Returns:
            跨卷上下文信息
        """
        if chapters_per_volume is None:
            chapters_per_volume = self.DEFAULT_CHAPTERS_PER_VOLUME

        current_volume = ((current_chapter - 1) // chapters_per_volume) + 1

        context = {
            "current_chapter": current_chapter,
            "current_volume": current_volume,
            "volumes_in_window": [],
            "previous_volume_summary": None,
            "next_volume_preview": None,
            "window_start": max(1, current_chapter - window_size),
            "window_end": current_chapter + window_size
        }

        current_vol_info = self.get_enhanced_volume_info(novel_id, current_chapter, chapters_per_volume)
        context["current_volume_info"] = current_vol_info

        if current_volume > 1:
            prev_summary = self._load_volume_summary(novel_id, current_volume - 1)
            if prev_summary:
                context["previous_volume_summary"] = prev_summary

        if current_vol_info.get("next_volume_preview"):
            context["next_volume_preview"] = current_vol_info["next_volume_preview"]

        context["volumes_in_window"].append({
            "volume_number": current_volume,
            "start": (current_volume - 1) * chapters_per_volume + 1,
            "end": current_volume * chapters_per_volume,
            "is_current": True
        })

        if current_chapter - window_size < (current_volume - 1) * chapters_per_volume + 1:
            prev_volume = current_volume - 1
            context["volumes_in_window"].append({
                "volume_number": prev_volume,
                "start": (prev_volume - 1) * chapters_per_volume + 1,
                "end": prev_volume * chapters_per_volume,
                "is_current": False
            })

        if current_chapter + window_size > current_volume * chapters_per_volume:
            next_volume = current_volume + 1
            context["volumes_in_window"].append({
                "volume_number": next_volume,
                "start": (next_volume - 1) * chapters_per_volume + 1,
                "end": next_volume * chapters_per_volume,
                "is_current": False
            })

        return context

    def finalize_volume(self, novel_id: str, volume_number: int, final_summary: Dict) -> bool:
        """
        完成卷的写作，保存最终摘要

        Args:
            novel_id: 小说ID
            volume_number: 卷号
            final_summary: 最终摘要，包含:
                - summary: 卷摘要
                - ending_hook: 结尾钩子
                - key_events: 关键事件列表
                - foreshadowing_carried: 带入下卷的伏笔
                - completed_goals: 完成的目标

        Returns:
            是否成功
        """
        state = self._load_volume_state(novel_id, volume_number) or {}
        state["status"] = VolumeStatus.COMPLETED.value
        state["final_summary"] = final_summary
        state["completed_at"] = datetime.now().isoformat()

        if self._save_volume_state(novel_id, volume_number, state):
            summary_path = self._get_volume_summary_path(novel_id, volume_number)
            summary_data = {
                "volume_number": volume_number,
                "summary": final_summary.get("summary", ""),
                "ending_hook": final_summary.get("ending_hook", ""),
                "key_events": final_summary.get("key_events", []),
                "foreshadowing_carried": final_summary.get("foreshadowing_carried", []),
                "completed_goals": final_summary.get("completed_goals", []),
                "completed_at": datetime.now().isoformat()
            }

            try:
                os.makedirs(os.path.dirname(summary_path), exist_ok=True)
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(summary_data, f, ensure_ascii=False, indent=2)
                logger.info(f"卷{volume_number}已完成，摘要已保存")
                return True
            except Exception as e:
                logger.error(f"保存卷摘要失败: {e}")
                return False

        return False


def get_enhanced_volume_info(novel_id: str, chapter_number: int,
                               chapters_per_volume: int = 40) -> Dict[str, Any]:
    """获取增强卷信息的便捷函数"""
    manager = EnhancedVolumeManager()
    return manager.get_enhanced_volume_info(novel_id, chapter_number, chapters_per_volume)


def get_volume_guidance(novel_id: str, chapter_number: int,
                         chapters_per_volume: int = 40) -> str:
    """获取卷写作指导的便捷函数"""
    manager = EnhancedVolumeManager()
    return manager.get_volume_guidance(novel_id, chapter_number, chapters_per_volume)


if __name__ == "__main__":
    print("=== EnhancedVolumeManager 测试 ===\n")

    manager = EnhancedVolumeManager()

    print("测试获取增强卷信息:")
    info = manager.get_enhanced_volume_info("test_novel", 25)
    print(f"章节25所在卷: 第{info['volume_number']}卷")
    print(f"卷内章节: 第{info['chapter_in_volume']}章")
    print(f"卷进度: {info['volume_progress']*100:.1f}%")
    print(f"卷阶段: {info['volume_phase']}")
    print(f"是否为卷开头: {info['is_volume_start']}")
    print(f"是否为卷结尾: {info['is_volume_end']}")

    print("\n测试获取卷进度:")
    progress = manager.get_volume_progress("test_novel", 1)
    print(f"卷1进度: {progress.progress_percentage*100:.1f}%")
    print(f"已写章节: {progress.written_chapters}/{progress.total_chapters}")
    print(f"当前阶段: {progress.phase}")

    print("\n测试跨卷上下文:")
    context = manager.get_cross_volume_context("test_novel", 38, window_size=5)
    print(f"当前章节: {context['current_chapter']}")
    print(f"当前卷: {context['current_volume']}")
    print(f"窗口范围: {context['window_start']}-{context['window_end']}")
    print(f"窗口内卷数: {len(context['volumes_in_window'])}")
