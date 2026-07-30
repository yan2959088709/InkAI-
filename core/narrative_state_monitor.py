"""
NarrativeStateMonitor - 剧情状态监控中心

核心职责:
1. 整合所有状态信息 (卷/阶段/伏笔/节奏)
2. 计算剧情健康度 (0-100分)
3. 检测异常并触发告警
4. 提供动态写作指导

这是新架构的核心组件，实现"实时监控+提前预警"而非"事后打分"
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class VolumeInfo:
    """卷信息"""
    number: int
    total_chapters: int
    chapters_in_volume: int
    progress: float
    name: str = ""
    summary: str = ""


@dataclass
class PhaseInfo:
    """阶段信息"""
    name: str
    total_chapters: int
    current_chapter: int
    progress: float
    is_climax: bool = False


@dataclass
class RhythmInfo:
    """节奏信息"""
    type: str
    health: float
    consecutive_battle_count: int = 0
    consecutive_slow_count: int = 0


@dataclass
class ForeshadowingStatus:
    """伏笔状态"""
    total: int
    active: int
    overdue: int
    recycled: int
    recovery_rate: float


@dataclass
class NarrativeAlert:
    """告警信息"""
    level: str
    component: str
    message: str
    suggestion: str


@dataclass
class NarrativeHealth:
    """剧情健康度"""
    overall: float
    foreshadowing_score: float
    rhythm_score: float
    phase_progress_score: float
    consistency_score: float
    innovation_score: float


class NarrativeStateMonitor:
    """
    剧情状态监控中心

    核心职责:
    1. 整合所有状态信息
    2. 计算剧情健康度
    3. 检测并触发修正
    4. 提供统一的状态查询接口

    使用方式:
    ```python
    monitor = NarrativeStateMonitor(novel_id="xxx", data_manager=data_manager)
    state = monitor.get_current_state()
    health = monitor.calculate_health_score()
    alerts = monitor.check_and_alert()
    guidance = monitor.get_dynamic_guidance(chapter_num)
    ```
    """

    # 健康度阈值
    HEALTH_THRESHOLDS = {
        "critical": 40,
        "warning": 60,
        "good": 80
    }

    # 伏笔超时阈值 (章节数)
    FORESHADOWING_TIMEOUT = {
        "short": 5,
        "medium": 15,
        "long": 30
    }

    # 连续战斗/缓和我持数阈值
    CONSECUTIVE_ACTION_THRESHOLD = 3
    CONSECUTIVE_SLOW_THRESHOLD = 3

    def __init__(self, novel_id: str, data_manager: Any = None):
        """
        初始化剧情状态监控中心

        Args:
            novel_id: 小说ID
            data_manager: 数据管理器 (用于获取章节数据)
        """
        self.novel_id = novel_id
        self.data_manager = data_manager

        # 内部状态缓存
        self._current_chapter: int = 0
        self._volume_info: Optional[VolumeInfo] = None
        self._phase_info: Optional[PhaseInfo] = None
        self._rhythm_info: Optional[RhythmInfo] = None
        self._foreshadowing_status: Optional[ForeshadowingStatus] = None
        self._health_score: float = 100.0

        # 历史记录
        self._rhythm_history: List[Dict] = []
        self._health_history: List[float] = []
        self._chapter_states: Dict[int, Dict] = {}

        # 组件引用 (将在后续初始化)
        self._volume_manager = None
        self._foreshadowing_manager = None
        self._rhythm_keeper = None

    def set_managers(self, volume_manager: Any = None,
                     foreshadowing_manager: Any = None,
                     rhythm_keeper: Any = None):
        """
        设置关联的管理器

        Args:
            volume_manager: 卷管理器
            foreshadowing_manager: 伏笔管理器
            rhythm_keeper: 节奏控制器
        """
        self._volume_manager = volume_manager
        self._foreshadowing_manager = foreshadowing_manager
        self._rhythm_keeper = rhythm_keeper

    def get_current_state(self, chapter_num: int = None) -> Dict[str, Any]:
        """
        获取当前剧情状态快照

        Args:
            chapter_num: 章节号 (如果为None，使用内部缓存)

        Returns:
            完整状态快照
        """
        if chapter_num is not None:
            self._current_chapter = chapter_num

        if self._current_chapter == 0:
            return self._get_empty_state()

        # 更新各维度状态
        self._update_volume_info()
        self._update_phase_info()
        self._update_rhythm_info()
        self._update_foreshadowing_status()

        # 计算健康度
        self._health_score = self.calculate_health_score()

        return {
            "chapter": self._current_chapter,
            "volume": asdict(self._volume_info) if self._volume_info else {},
            "phase": asdict(self._phase_info) if self._phase_info else {},
            "rhythm": asdict(self._rhythm_info) if self._rhythm_info else {},
            "foreshadowing": asdict(self._foreshadowing_status) if self._foreshadowing_status else {},
            "health_score": self._health_score,
            "health_level": self._get_health_level(self._health_score),
            "alerts": [asdict(a) for a in self.check_and_alert()],
            "timestamp": datetime.now().isoformat()
        }

    def _get_empty_state(self) -> Dict[str, Any]:
        """返回空状态"""
        return {
            "chapter": 0,
            "volume": {},
            "phase": {},
            "rhythm": {},
            "foreshadowing": {},
            "health_score": 0,
            "health_level": "unknown",
            "alerts": [],
            "timestamp": datetime.now().isoformat()
        }

    def _update_volume_info(self):
        """更新卷信息"""
        if self._volume_manager:
            try:
                vol_info = self._volume_manager.get_volume_info(self.novel_id, self._current_chapter)
                self._volume_info = VolumeInfo(**vol_info) if isinstance(vol_info, dict) else vol_info
            except Exception:
                self._volume_info = self._calculate_volume_info()
        else:
            self._volume_info = self._calculate_volume_info()

    def _calculate_volume_info(self) -> VolumeInfo:
        """计算卷信息 (当没有volume_manager时)"""
        estimated_total = 100
        chapters_per_volume = 40

        volume_number = (self._current_chapter - 1) // chapters_per_volume + 1
        chapter_in_volume = (self._current_chapter - 1) % chapters_per_volume + 1
        progress = chapter_in_volume / chapters_per_volume

        return VolumeInfo(
            number=volume_number,
            total_chapters=estimated_total,
            chapters_in_volume=chapter_in_volume,
            progress=progress,
            name=f"第{volume_number}卷"
        )

    def _update_phase_info(self):
        """更新阶段信息"""
        total_chapters = 100

        # 三段式: 开端25% / 中段50% / 结局25%
        chapter_ratio = self._current_chapter / total_chapters

        if chapter_ratio <= 0.25:
            phase_name = "开端"
            phase_length = int(total_chapters * 0.25)
        elif chapter_ratio <= 0.75:
            phase_name = "中段"
            phase_length = int(total_chapters * 0.5)
        else:
            phase_name = "结局"
            phase_length = int(total_chapters * 0.25)

        phase_progress = min(1.0, (self._current_chapter % phase_length) / phase_length) if phase_length > 0 else 0

        self._phase_info = PhaseInfo(
            name=phase_name,
            total_chapters=total_chapters,
            current_chapter=self._current_chapter,
            progress=phase_progress,
            is_climax=(phase_name == "结局")
        )

    def _update_rhythm_info(self):
        """更新节奏信息"""
        if not self._rhythm_history:
            rhythm_type = "缓冲"
            rhythm_health = 1.0
        else:
            last_rhythm = self._rhythm_history[-1].get("type", "缓冲")

            # 检查连续性
            consecutive_battle = 0
            consecutive_slow = 0

            for i in range(len(self._rhythm_history) - 1, -1, -1):
                if self._rhythm_history[i].get("type") in ["战斗", "升级"]:
                    consecutive_battle += 1
                elif self._rhythm_history[i].get("type") in ["缓冲", "铺垫"]:
                    consecutive_slow += 1
                else:
                    break

            # 根据历史决定当前节奏类型
            if consecutive_battle >= self.CONSECUTIVE_ACTION_THRESHOLD:
                rhythm_type = "缓冲"  # 强制切换到缓冲
            elif consecutive_slow >= self.CONSECUTIVE_SLOW_THRESHOLD:
                rhythm_type = "强推"  # 强制切换到强推
            else:
                # 标准3章循环
                cycle_position = (self._current_chapter - 1) % 3
                if cycle_position == 0:
                    rhythm_type = "缓冲"
                elif cycle_position == 1:
                    rhythm_type = "升级"
                else:
                    rhythm_type = "强推"

            rhythm_health = 1.0 - (max(0, consecutive_battle - 2) * 0.2 +
                                   max(0, consecutive_slow - 2) * 0.2)

        self._rhythm_info = RhythmInfo(
            type=rhythm_type,
            health=rhythm_health,
            consecutive_battle_count=consecutive_battle if 'consecutive_battle' in dir() else 0,
            consecutive_slow_count=consecutive_slow if 'consecutive_slow' in dir() else 0
        )

    def _update_foreshadowing_status(self):
        """更新伏笔状态"""
        if self._foreshadowing_manager:
            try:
                fs_data = self._foreshadowing_manager.get_foreshadowing_status(self.novel_id)
                self._foreshadowing_status = ForeshadowingStatus(
                    total=fs_data.get("total", 0),
                    active=fs_data.get("active", 0),
                    overdue=fs_data.get("overdue", 0),
                    recycled=fs_data.get("recycled", 0),
                    recovery_rate=fs_data.get("recovery_rate", 0.0)
                )
            except Exception:
                self._foreshadowing_status = self._calculate_foreshadowing_status()
        else:
            self._foreshadowing_status = self._calculate_foreshadowing_status()

    def _calculate_foreshadowing_status(self) -> ForeshadowingStatus:
        """计算伏笔状态 (当没有foreshadowing_manager时)"""
        if not hasattr(self, '_foreshadowing_records'):
            self._foreshadowing_records = []

        total = len(self._foreshadowing_records)
        recycled = sum(1 for fs in self._foreshadowing_records if fs.get("recycled", False))
        active = total - recycled

        overdue = 0
        for fs in self._foreshadowing_records:
            if not fs.get("recycled", False):
                planted_chapter = fs.get("planted_chapter", 1)
                fs_type = fs.get("type", "medium")
                timeout = self.FORESHADOWING_TIMEOUT.get(fs_type, 15)

                if self._current_chapter - planted_chapter > timeout:
                    overdue += 1

        recovery_rate = recycled / total if total > 0 else 0.0

        return ForeshadowingStatus(
            total=total,
            active=active,
            overdue=overdue,
            recycled=recycled,
            recovery_rate=recovery_rate
        )

    def calculate_health_score(self) -> float:
        """
        计算剧情健康度 (0-100)

        评分维度:
        - 伏笔管理 (25%): 回收率 × 准时性
        - 节奏控制 (20%): 节奏一致性
        - 阶段进展 (20%): 阶段进度对齐度
        - 连贯性 (20%): 前后文一致性
        - 创新性 (15%): 套路重复率 (反向)

        Returns:
            健康度分数 (0-100)
        """
        # 伏笔管理评分 (25%)
        if self._foreshadowing_status and self._foreshadowing_status.total > 0:
            recovery_score = self._foreshadowing_status.recovery_rate * 100
            overdue_penalty = (self._foreshadowing_status.overdue /
                             max(1, self._foreshadowing_status.active)) * 30
            foreshadowing_score = max(0, recovery_score - overdue_penalty)
        else:
            foreshadowing_score = 100.0

        # 节奏控制评分 (20%)
        rhythm_score = (self._rhythm_info.health * 100) if self._rhythm_info else 80.0

        # 阶段进展评分 (20%)
        if self._phase_info:
            expected_progress = self._current_chapter / self._phase_info.total_chapters
            phase_diff = abs(expected_progress - self._phase_info.progress)
            phase_progress_score = max(0, 100 - phase_diff * 200)
        else:
            phase_progress_score = 80.0

        # 连贯性评分 (20%) - 基于历史健康度
        if len(self._health_history) >= 5:
            recent_avg = sum(self._health_history[-5:]) / 5
            consistency_score = recent_avg
        else:
            consistency_score = 80.0

        # 创新性评分 (15%) - 基于套路检测
        innovation_score = self._calculate_innovation_score()

        # 加权计算
        overall = (
            foreshadowing_score * 0.25 +
            rhythm_score * 0.20 +
            phase_progress_score * 0.20 +
            consistency_score * 0.20 +
            innovation_score * 0.15
        )

        return round(overall, 1)

    def _calculate_innovation_score(self) -> float:
        """
        计算创新性评分

        基于连续相同类型情节的数量
        连续同类情节越多，分数越低
        """
        if len(self._rhythm_history) < 3:
            return 100.0

        # 统计最近10章的情节类型
        recent_types = [h.get("type", "缓冲") for h in self._rhythm_history[-10:]]

        # 计算最大重复次数
        max_consecutive = 1
        current_consecutive = 1

        for i in range(1, len(recent_types)):
            if recent_types[i] == recent_types[i-1]:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1

        # 每超过3次重复，降低10分
        penalty = max(0, (max_consecutive - 3) * 10)
        return max(0, 100 - penalty)

    def _get_health_level(self, score: float) -> str:
        """获取健康度等级"""
        if score >= self.HEALTH_THRESHOLDS["good"]:
            return "good"
        elif score >= self.HEALTH_THRESHOLDS["warning"]:
            return "warning"
        elif score >= self.HEALTH_THRESHOLDS["critical"]:
            return "critical"
        else:
            return "dangerous"

    def check_and_alert(self) -> List[NarrativeAlert]:
        """
        检查状态并生成告警

        Returns:
            分级告警列表
        """
        alerts = []

        if not self._foreshadowing_status or not self._rhythm_info:
            return alerts

        # 检查伏笔堆积
        if self._foreshadowing_status.overdue > 3:
            alerts.append(NarrativeAlert(
                level="critical",
                component="foreshadowing",
                message=f"伏笔堆积严重: {self._foreshadowing_status.overdue}个伏笔超时未回收",
                suggestion="建议: 优先回收伏笔，暂停新情节发展"
            ))
        elif self._foreshadowing_status.overdue > 0:
            alerts.append(NarrativeAlert(
                level="warning",
                component="foreshadowing",
                message=f"伏笔超时: {self._foreshadowing_status.overdue}个需要回收",
                suggestion="建议: 本章或下章安排伏笔回收"
            ))

        # 检查伏笔回收率
        expected_recovery_rate = min(0.8, self._current_chapter / 100 * 0.8)
        if self._foreshadowing_status.recovery_rate < expected_recovery_rate - 0.2:
            alerts.append(NarrativeAlert(
                level="warning",
                component="foreshadowing",
                message=f"伏笔回收率偏低: {self._foreshadowing_status.recovery_rate:.1%}",
                suggestion="建议: 增加伏笔回收情节"
            ))

        # 检查连续战斗
        if self._rhythm_info.consecutive_battle_count >= self.CONSECUTIVE_ACTION_THRESHOLD:
            alerts.append(NarrativeAlert(
                level="warning",
                component="rhythm",
                message=f"连续战斗过多: {self._rhythm_info.consecutive_battle_count}章连续战斗/升级",
                suggestion="建议: 增加人物内心戏或缓冲情节"
            ))

        # 检查连续缓和平淡
        if self._rhythm_info.consecutive_slow_count >= self.CONSECUTIVE_SLOW_THRESHOLD:
            alerts.append(NarrativeAlert(
                level="info",
                component="rhythm",
                message=f"连续缓冲过多: {self._rhythm_info.consecutive_slow_count}章连续缓冲",
                suggestion="建议: 可以安排一个小高潮"
            ))

        # 检查健康度
        if self._health_score < self.HEALTH_THRESHOLDS["critical"]:
            alerts.append(NarrativeAlert(
                level="critical",
                component="overall",
                message=f"剧情健康度危险: {self._health_score}",
                suggestion="建议: 暂停生成，进行人工审核"
            ))
        elif self._health_score < self.HEALTH_THRESHOLDS["warning"]:
            alerts.append(NarrativeAlert(
                level="warning",
                component="overall",
                message=f"剧情健康度偏低: {self._health_score}",
                suggestion="建议: 关注当前章节质量"
            ))

        return alerts

    def get_dynamic_guidance(self, chapter_num: int = None) -> str:
        """
        获取动态写作指导

        替代固定3章循环的动态节奏指导

        Args:
            chapter_num: 章节号

        Returns:
            写作指导字符串
        """
        if chapter_num:
            self._current_chapter = chapter_num
            self.get_current_state()

        guidance_parts = []

        # 基于告警生成指导
        alerts = self.check_and_alert()
        critical_alerts = [a for a in alerts if a.level == "critical"]
        warning_alerts = [a for a in alerts if a.level == "warning"]

        # 1. 如果有严重问题，先解决
        if critical_alerts:
            guidance_parts.append("【紧急修正】")
            for alert in critical_alerts:
                guidance_parts.append(alert.suggestion)
            return "\n".join(guidance_parts)

        # 2. 伏笔回收指导
        if self._foreshadowing_status and self._foreshadowing_status.overdue > 0:
            guidance_parts.append(f"【伏笔回收】本章需要回收{self._foreshadowing_status.overdue}个超时伏笔。")
            guidance_parts.append("在情节中自然融入伏笔的揭示。")

        # 3. 节奏指导
        if self._rhythm_info:
            if self._rhythm_info.type == "缓冲":
                guidance_parts.append("【节奏: 缓冲】本章适合放缓节奏，着重描写人物内心和关系发展。")
                guidance_parts.append("可以增加日常互动、内心独白或角色间的深度对话。")
            elif self._rhythm_info.type == "升级":
                guidance_parts.append("【节奏: 升级】本章需要矛盾升级或新发展。")
                guidance_parts.append("可以引入新的冲突、揭示新信息或推进人物关系。")
            elif self._rhythm_info.type == "强推":
                guidance_parts.append("【节奏: 强推】本章需要高潮或重大进展。")
                guidance_parts.append("可以安排关键对决、重要揭示或情节转折。")

        # 4. 连续战斗提醒
        if self._rhythm_info and self._rhythm_info.consecutive_battle_count >= 2:
            guidance_parts.append(f"注意: 前{self._rhythm_info.consecutive_battle_count}章都是战斗/升级情节。")
            guidance_parts.append("建议增加一些非战斗内容平衡节奏。")

        # 5. 阶段特定指导
        if self._phase_info:
            if self._phase_info.is_climax and self._phase_info.progress > 0.7:
                guidance_parts.append("【高潮阶段】即将进入尾声，本章应为主线冲突的高潮点。")
            elif self._phase_info.name == "开端" and self._phase_info.progress < 0.5:
                guidance_parts.append("【开端阶段】适合建立世界观、人物关系和初期冲突。")

        # 6. 套路重复提醒
        innovation_score = self._calculate_innovation_score()
        if innovation_score < 70:
            guidance_parts.append("【创意提醒】近期情节模式重复较多，请尝试新的情节元素。")

        if not guidance_parts:
            guidance_parts.append("【标准节奏】按正常节奏推进即可。")
            if self._rhythm_info:
                guidance_parts.append(f"当前节奏类型: {self._rhythm_info.type}")

        return "\n".join(guidance_parts)

    def get_recovery_guidance(self) -> str:
        """
        获取恢复指导 (当健康度低于阈值时)

        Returns:
            恢复指导字符串
        """
        guidance = ["【剧情修复指导】", "", "当前剧情存在以下问题:"]

        alerts = self.check_and_alert()
        for i, alert in enumerate(alerts, 1):
            guidance.append(f"{i}. {alert.message}")

        guidance.append("")
        guidance.append("建议的修复方向:")

        # 按优先级排序
        priority_fixes = {
            "foreshadowing": [],
            "rhythm": [],
            "overall": []
        }

        for alert in alerts:
            if alert.component in priority_fixes:
                priority_fixes[alert.component].append(alert.suggestion)

        if priority_fixes["foreshadowing"]:
            guidance.append("- 伏笔管理: " + " ".join(priority_fixes["foreshadowing"]))
        if priority_fixes["rhythm"]:
            guidance.append("- 节奏控制: " + " ".join(priority_fixes["rhythm"]))
        if priority_fixes["overall"]:
            guidance.append("- 整体调整: " + " ".join(priority_fixes["overall"]))

        return "\n".join(guidance)

    def get_standard_guidance(self) -> str:
        """
        获取标准指导 (当健康度正常时)

        Returns:
            标准指导字符串
        """
        return self.get_dynamic_guidance()

    def update_state(self, chapter_num: int, chapter_data: Dict[str, Any]):
        """
        更新状态

        Args:
            chapter_num: 章节号
            chapter_data: 章节数据，包含:
                - content: 正文
                - rhythm_type: 本章节奏类型
                - foreshadowing_recycled: 回收的伏笔列表
                - new_foreshadowing_planted: 新埋的伏笔列表
                - word_count: 字数
                - summary: 摘要
        """
        self._current_chapter = chapter_num

        # 记录节奏历史
        rhythm_type = chapter_data.get("rhythm_type", self._rhythm_info.type if self._rhythm_info else "缓冲")
        self._rhythm_history.append({
            "chapter": chapter_num,
            "type": rhythm_type,
            "timestamp": datetime.now().isoformat()
        })

        # 限制历史长度
        if len(self._rhythm_history) > 50:
            self._rhythm_history = self._rhythm_history[-50:]

        # 更新伏笔记录
        if hasattr(self, '_foreshadowing_records'):
            # 标记回收的伏笔
            recycled = chapter_data.get("foreshadowing_recycled", [])
            for fs in self._foreshadowing_records:
                if fs.get("id") in recycled:
                    fs["recycled"] = True
                    fs["recycled_chapter"] = chapter_num

            # 添加新伏笔
            new_fs = chapter_data.get("new_foreshadowing_planted", [])
            for fs_data in new_fs:
                self._foreshadowing_records.append({
                    "id": fs_data.get("id", f"fs_{chapter_num}_{len(self._foreshadowing_records)}"),
                    "planted_chapter": chapter_num,
                    "type": fs_data.get("type", "medium"),
                    "description": fs_data.get("description", ""),
                    "recycled": False
                })

        # 记录章节状态
        self._chapter_states[chapter_num] = {
            "health_score": self._health_score,
            "rhythm_type": rhythm_type,
            "word_count": chapter_data.get("word_count", 0),
            "timestamp": datetime.now().isoformat()
        }

        # 记录健康度历史
        self._health_history.append(self._health_score)
        if len(self._health_history) > 100:
            self._health_history = self._health_history[-100:]

        # 更新各维度状态
        self.get_current_state()

    def run_full_diagnostic(self) -> Dict[str, Any]:
        """
        运行完整诊断

        Returns:
            诊断报告
        """
        state = self.get_current_state()
        health = self.calculate_health_score()

        # 计算趋势
        trend = "stable"
        if len(self._health_history) >= 5:
            recent = self._health_history[-5:]
            if all(recent[i] >= recent[i+1] for i in range(len(recent)-1)):
                trend = "declining"
            elif all(recent[i] <= recent[i+1] for i in range(len(recent)-1)):
                trend = "improving"

        # 识别主要问题
        major_issues = []
        if self._foreshadowing_status and self._foreshadowing_status.overdue > 2:
            major_issues.append("伏笔堆积")
        if self._rhythm_info and self._rhythm_info.consecutive_battle_count >= 4:
            major_issues.append("节奏失衡")
        if health < 60:
            major_issues.append("健康度偏低")

        return {
            "chapter": self._current_chapter,
            "health_score": health,
            "health_level": self._get_health_level(health),
            "trend": trend,
            "major_issues": major_issues,
            "foreshadowing_status": asdict(self._foreshadowing_status) if self._foreshadowing_status else {},
            "rhythm_status": asdict(self._rhythm_info) if self._rhythm_info else {},
            "recommendations": self.get_recovery_guidance() if major_issues else self.get_standard_guidance(),
            "timestamp": datetime.now().isoformat()
        }

    def get_state_summary(self) -> str:
        """
        获取状态摘要字符串 (用于日志/调试)

        Returns:
            格式化的状态摘要
        """
        state = self.get_current_state()

        lines = [
            "=" * 50,
            f"剧情状态监控 - 第{state['chapter']}章",
            "=" * 50,
            f"健康度: {state['health_score']} ({state['health_level']})",
            f"卷进度: {state['volume'].get('progress', 0):.1%}" if state.get('volume') else "N/A",
            f"阶段: {state['phase'].get('name', 'N/A')} ({state['phase'].get('progress', 0):.1%})" if state.get('phase') else "N/A",
            f"节奏: {state['rhythm'].get('type', 'N/A')}" if state.get('rhythm') else "N/A",
            f"伏笔: 活跃{state['foreshadowing'].get('active', 0)} | 超时{state['foreshadowing'].get('overdue', 0)}" if state.get('foreshadowing') else "N/A",
            "-" * 50,
            "告警:"
        ]

        for alert in state.get('alerts', []):
            lines.append(f"  [{alert['level'].upper()}] {alert['message']}")

        if not state.get('alerts'):
            lines.append("  无")

        lines.append("=" * 50)

        return "\n".join(lines)

    def reset(self):
        """重置监控状态"""
        self._current_chapter = 0
        self._volume_info = None
        self._phase_info = None
        self._rhythm_info = None
        self._foreshadowing_status = None
        self._health_score = 100.0
        self._rhythm_history = []
        self._health_history = []
        self._chapter_states = {}
        if hasattr(self, '_foreshadowing_records'):
            self._foreshadowing_records = []

    def export_state(self, filepath: str):
        """
        导出状态到文件

        Args:
            filepath: 文件路径
        """
        state = self.get_current_state()
        state["rhythm_history"] = self._rhythm_history
        state["health_history"] = self._health_history
        state["chapter_states"] = self._chapter_states

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def import_state(self, filepath: str):
        """
        从文件导入状态

        Args:
            filepath: 文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)

        self._current_chapter = state.get("chapter", 0)
        self._rhythm_history = state.get("rhythm_history", [])
        self._health_history = state.get("health_history", [])
        self._chapter_states = state.get("chapter_states", {})


if __name__ == "__main__":
    monitor = NarrativeStateMonitor(novel_id="test_novel")

    print("=== 初始状态 ===")
    print(monitor.get_state_summary())

    print("\n=== 模拟章节生成 ===")
    for chapter in [1, 5, 10, 15, 20]:
        monitor.update_state(chapter, {
            "rhythm_type": ["缓冲", "升级", "强推", "缓冲", "升级"][chapter % 3],
            "foreshadowing_recycled": [],
            "new_foreshadowing_planted": [
                {"id": f"fs_{chapter}_1", "type": "short", "description": f"第{chapter}章埋下的测试伏笔"}
            ],
            "word_count": 4000
        })

        state = monitor.get_current_state()
        print(f"\n--- 第{chapter}章 ---")
        print(f"健康度: {state['health_score']}")
        print(f"节奏: {state['rhythm']['type']}")
        print(f"伏笔: {state['foreshadowing']['active']}活跃, {state['foreshadowing']['overdue']}超时")
        print(f"\n动态指导:\n{monitor.get_dynamic_guidance()}")
