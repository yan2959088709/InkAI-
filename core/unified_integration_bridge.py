"""
UnifiedIntegrationBridge - 统一集成桥接器

核心职责:
1. 整合所有新组件到一个统一接口
2. 管理组件间的依赖关系
3. 提供向后兼容的API
4. 支持分步骤启用/禁用

组件:
- NarrativeStateMonitor: 叙事状态监控
- EnhancedVolumeManager: 增强卷管理
- SlidingWindowContext: 滑动窗口上下文
- VolumeStorylinePlanner: 卷剧情规划

使用方式:
```python
bridge = UnifiedIntegrationBridge(
    legacy_workflow=workflow,
    data_manager=data_manager
)

# 初始化所有组件
bridge.initialize_all()

# 获取当前上下文
context = bridge.get_context(novel_id, chapter_num)

# 更新状态
bridge.update_chapter(novel_id, chapter_num, chapter_data)

# 获取写作指导
guidance = bridge.get_writing_guidance(novel_id, chapter_num)
```
"""

import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger("unified_integration_bridge")


@dataclass
class IntegrationStatus:
    """集成状态"""
    all_initialized: bool = False
    narrative_monitor_ready: bool = False
    volume_manager_ready: bool = False
    sliding_window_ready: bool = False
    storyline_planner_ready: bool = False
    enabled_features: List[str] = field(default_factory=list)


class UnifiedIntegrationBridge:
    """
    统一集成桥接器

    特点:
    1. 单一入口点 - 所有新功能通过这个桥接器访问
    2. 组件自检 - 每个组件独立初始化和状态检查
    3. 优雅降级 - 某个组件失败不影响其他组件
    4. 配置驱动 - 通过配置启用/禁用功能
    """

    def __init__(self,
                 legacy_workflow: Any = None,
                 data_manager: Any = None,
                 config: Dict[str, Any] = None):
        """
        初始化统一集成桥接器

        Args:
            legacy_workflow: 原有工作流对象
            data_manager: 数据管理器
            config: 配置字典
        """
        self.legacy = legacy_workflow
        self.data_manager = data_manager
        self.config = config or self._default_config()

        self._status = IntegrationStatus()
        self._components: Dict[str, Any] = {}
        self._initialized = False

    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "enable_narrative_monitor": True,
            "enable_enhanced_volume": True,
            "enable_sliding_window": True,
            "enable_storyline_planner": True,
            "sliding_window_tokens": 250000,
            "chapters_per_volume": 40,
            "default_strategy": "symmetric"
        }

    def initialize_all(self) -> IntegrationStatus:
        """
        初始化所有启用的组件

        Returns:
            集成状态
        """
        if self._initialized:
            logger.info("[Bridge] 桥接器已初始化，跳过")
            return self._status

        logger.info("[Bridge] 开始初始化统一集成桥接器...")

        if self.config.get("enable_narrative_monitor", True):
            self._initialize_narrative_monitor()

        if self.config.get("enable_enhanced_volume", True):
            self._initialize_enhanced_volume_manager()

        if self.config.get("enable_sliding_window", True):
            self._initialize_sliding_window()

        if self.config.get("enable_storyline_planner", True):
            self._initialize_storyline_planner()

        self._update_status()

        self._initialized = True
        logger.info(f"[Bridge] 初始化完成: {self.get_status_summary()}")

        return self._status

    def _initialize_narrative_monitor(self):
        """初始化叙事状态监控"""
        try:
            from core.narrative_state_monitor import NarrativeStateMonitor

            novel_id = self._get_novel_id()
            self._components["narrative_monitor"] = NarrativeStateMonitor(
                novel_id=novel_id,
                data_manager=self.data_manager
            )

            if hasattr(self, '_volume_manager') and self._components.get("volume_manager"):
                self._components["narrative_monitor"].set_managers(
                    volume_manager=self._components["volume_manager"]
                )

            self._status.narrative_monitor_ready = True
            logger.info("[Bridge] NarrativeMonitor 初始化成功")
        except Exception as e:
            logger.error(f"[Bridge] NarrativeMonitor 初始化失败: {e}")
            self._components["narrative_monitor"] = None

    def _initialize_enhanced_volume_manager(self):
        """初始化增强卷管理器"""
        try:
            from core.enhanced_volume_manager import EnhancedVolumeManager

            self._components["volume_manager"] = EnhancedVolumeManager(
                data_manager=self.data_manager
            )
            self._status.volume_manager_ready = True
            logger.info("[Bridge] EnhancedVolumeManager 初始化成功")
        except Exception as e:
            logger.error(f"[Bridge] EnhancedVolumeManager 初始化失败: {e}")
            self._components["volume_manager"] = None

    def _initialize_sliding_window(self):
        """初始化滑动窗口"""
        try:
            from core.sliding_window_context import SlidingWindowContext

            max_tokens = self.config.get("sliding_window_tokens", 250000)

            self._components["sliding_window"] = SlidingWindowContext(
                data_manager=self.data_manager,
                max_context_tokens=max_tokens
            )
            self._status.sliding_window_ready = True
            logger.info(f"[Bridge] SlidingWindowContext 初始化成功 (max_tokens={max_tokens})")
        except Exception as e:
            logger.error(f"[Bridge] SlidingWindowContext 初始化失败: {e}")
            self._components["sliding_window"] = None

    def _initialize_storyline_planner(self):
        """初始化剧情规划器"""
        try:
            from core.volume_storyline_planner import VolumeStorylinePlanner

            chapters_per_volume = self.config.get("chapters_per_volume", 40)
            self._components["storyline_planner"] = VolumeStorylinePlanner(
                chapters_per_volume=chapters_per_volume
            )
            self._status.storyline_planner_ready = True
            logger.info(f"[Bridge] VolumeStorylinePlanner 初始化成功 (chapters_per_volume={chapters_per_volume})")
        except Exception as e:
            logger.error(f"[Bridge] VolumeStorylinePlanner 初始化失败: {e}")
            self._components["storyline_planner"] = None

    def _get_novel_id(self) -> str:
        """获取小说ID"""
        if self.legacy and hasattr(self.legacy, 'novel_id'):
            return self.legacy.novel_id
        if self.data_manager and hasattr(self.data_manager, 'current_novel_id'):
            return self.data_manager.current_novel_id
        return "default_novel"

    def _update_status(self):
        """更新集成状态"""
        self._status.all_initialized = all([
            self._status.narrative_monitor_ready,
            self._status.volume_manager_ready,
            self._status.sliding_window_ready,
            self._status.storyline_planner_ready
        ])

        self._status.enabled_features = [
            name for name, ready in [
                ("narrative_monitor", self._status.narrative_monitor_ready),
                ("enhanced_volume", self._status.volume_manager_ready),
                ("sliding_window", self._status.sliding_window_ready),
                ("storyline_planner", self._status.storyline_planner_ready)
            ] if ready
        ]

    def get_context(self,
                    novel_id: str,
                    chapter_num: int,
                    strategy: str = "symmetric") -> Dict[str, Any]:
        """
        获取统一的上下文

        整合所有组件的信息，提供给LLM使用

        Args:
            novel_id: 小说ID
            chapter_num: 章节号
            strategy: 滑动窗口策略

        Returns:
            统一上下文
        """
        context = {
            "novel_id": novel_id,
            "chapter_num": chapter_num,
            "timestamp": datetime.now().isoformat()
        }

        if self._components.get("volume_manager"):
            try:
                volume_context = self._components["volume_manager"].get_cross_volume_context(
                    novel_id, chapter_num, window_size=5
                )
                context["volume"] = volume_context
            except Exception as e:
                logger.error(f"[Bridge] 获取卷上下文失败: {e}")

        if self._components.get("narrative_monitor"):
            try:
                narrative_state = self._components["narrative_monitor"].get_current_state(chapter_num)
                context["narrative"] = narrative_state
            except Exception as e:
                logger.error(f"[Bridge] 获取叙事状态失败: {e}")

        if self._components.get("sliding_window"):
            try:
                narrative_state = context.get("narrative", {})
                window_context = self._components["sliding_window"].build_window_context(
                    novel_id=novel_id,
                    current_chapter=chapter_num,
                    strategy=strategy,
                    narrative_state=narrative_state
                )
                context["window"] = window_context
            except Exception as e:
                logger.error(f"[Bridge] 获取窗口上下文失败: {e}")

        if self._components.get("storyline_planner"):
            try:
                chapters_per_volume = self.config.get("chapters_per_volume", 40)
                volume_number = ((chapter_num - 1) // chapters_per_volume) + 1
                chapter_in_volume = ((chapter_num - 1) % chapters_per_volume) + 1

                storyline_context = {
                    "volume_number": volume_number,
                    "chapter_in_volume": chapter_in_volume,
                    "guidance": self._components["storyline_planner"].get_volume_guidance(
                        volume_number, chapter_in_volume
                    )
                }
                context["storyline"] = storyline_context
            except Exception as e:
                logger.error(f"[Bridge] 获取剧情规划失败: {e}")

        return context

    def get_writing_guidance(self,
                             novel_id: str,
                             chapter_num: int) -> str:
        """
        获取写作指导

        综合所有组件的信息，生成统一的写作指导

        Args:
            novel_id: 小说ID
            chapter_num: 章节号

        Returns:
            写作指导字符串
        """
        guidance_parts = []

        chapters_per_volume = self.config.get("chapters_per_volume", 40)
        volume_number = ((chapter_num - 1) // chapters_per_volume) + 1
        chapter_in_volume = ((chapter_num - 1) % chapters_per_volume) + 1

        guidance_parts.append(f"【基本信息】第{volume_number}卷 第{chapter_in_volume}章 (总第{chapter_num}章)")

        if self._components.get("volume_manager"):
            try:
                volume_guidance = self._components["volume_manager"].get_volume_guidance(
                    novel_id, chapter_num, chapters_per_volume
                )
                if volume_guidance:
                    guidance_parts.append("\n" + volume_guidance)
            except Exception:
                pass

        if self._components.get("narrative_monitor"):
            try:
                state = self._components["narrative_monitor"].get_current_state(chapter_num)
                dynamic_guidance = self._components["narrative_monitor"].get_dynamic_guidance(chapter_num)
                if dynamic_guidance:
                    guidance_parts.append("\n" + dynamic_guidance)

                if state.get("alerts"):
                    guidance_parts.append("\n【告警】")
                    for alert in state["alerts"]:
                        guidance_parts.append(f"- {alert.get('message', '')}")
            except Exception:
                pass

        if self._components.get("storyline_planner"):
            try:
                storyline_guidance = self._components["storyline_planner"].get_volume_guidance(
                    volume_number, chapter_in_volume
                )
                if storyline_guidance:
                    guidance_parts.append("\n" + storyline_guidance)
            except Exception:
                pass

        return "\n".join(guidance_parts)

    def update_chapter(self,
                       novel_id: str,
                       chapter_num: int,
                       chapter_data: Dict[str, Any]) -> bool:
        """
        更新章节状态

        Args:
            novel_id: 小说ID
            chapter_num: 章节号
            chapter_data: 章节数据

        Returns:
            是否成功
        """
        success = True

        if self._components.get("volume_manager"):
            try:
                self._components["volume_manager"].update_chapter_in_volume(
                    novel_id, chapter_num, chapter_data
                )
            except Exception as e:
                logger.error(f"[Bridge] 更新卷状态失败: {e}")
                success = False

        if self._components.get("narrative_monitor"):
            try:
                self._components["narrative_monitor"].update_state(chapter_num, chapter_data)
            except Exception as e:
                logger.error(f"[Bridge] 更新叙事状态失败: {e}")
                success = False

        return success

    def get_volume_progress(self, novel_id: str, volume_number: int) -> Optional[Dict]:
        """
        获取卷进度

        Args:
            novel_id: 小说ID
            volume_number: 卷号

        Returns:
            卷进度信息
        """
        if not self._components.get("volume_manager"):
            return None

        try:
            progress = self._components["volume_manager"].get_volume_progress(
                novel_id, volume_number
            )
            from dataclasses import asdict
            return asdict(progress)
        except Exception as e:
            logger.error(f"[Bridge] 获取卷进度失败: {e}")
            return None

    def get_narrative_health(self, chapter_num: int) -> Optional[Dict]:
        """
        获取叙事健康度

        Args:
            chapter_num: 章节号

        Returns:
            健康度报告
        """
        if not self._components.get("narrative_monitor"):
            return None

        try:
            return self._components["narrative_monitor"].run_full_diagnostic()
        except Exception as e:
            logger.error(f"[Bridge] 获取健康度失败: {e}")
            return None

    def generate_volume_plan(self,
                              volume_number: int,
                              total_novel_chapters: int = 1000) -> Optional[Dict]:
        """
        生成卷剧情规划

        Args:
            volume_number: 卷号
            total_novel_chapters: 小说总章节数

        Returns:
            卷剧情规划
        """
        if not self._components.get("storyline_planner"):
            return None

        try:
            plan = self._components["storyline_planner"].generate_volume_plan(
                volume_number=volume_number,
                total_novel_chapters=total_novel_chapters
            )
            return self._components["storyline_planner"].export_volume_plan(plan)
        except Exception as e:
            logger.error(f"[Bridge] 生成卷规划失败: {e}")
            return None

    def get_status_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要

        Returns:
            状态字典
        """
        return {
            "initialized": self._initialized,
            "all_ready": self._status.all_initialized,
            "components": {
                "narrative_monitor": self._components.get("narrative_monitor") is not None,
                "volume_manager": self._components.get("volume_manager") is not None,
                "sliding_window": self._components.get("sliding_window") is not None,
                "storyline_planner": self._components.get("storyline_planner") is not None
            },
            "enabled_features": self._status.enabled_features,
            "config": self.config
        }

    def reset(self):
        """重置桥接器"""
        self._components.clear()
        self._initialized = False
        self._status = IntegrationStatus()
        logger.info("[Bridge] 桥接器已重置")


def create_unified_bridge(legacy_workflow: Any = None,
                           data_manager: Any = None,
                           **kwargs) -> UnifiedIntegrationBridge:
    """
    创建统一集成桥接器的便捷函数

    Args:
        legacy_workflow: 原有工作流
        data_manager: 数据管理器
        **kwargs: 其他配置参数

    Returns:
        UnifiedIntegrationBridge实例
    """
    bridge = UnifiedIntegrationBridge(
        legacy_workflow=legacy_workflow,
        data_manager=data_manager,
        config=kwargs
    )
    bridge.initialize_all()
    return bridge


if __name__ == "__main__":
    print("=== UnifiedIntegrationBridge 测试 ===\n")

    bridge = UnifiedIntegrationBridge()

    print("初始状态:")
    print(f"  {bridge.get_status_summary()}\n")

    bridge.initialize_all()

    print("\n初始化后状态:")
    status = bridge.get_status_summary()
    print(f"  组件状态: {status['components']}")
    print(f"  启用功能: {status['enabled_features']}")

    print("\n测试获取上下文 (章节50):")
    context = bridge.get_context("test_novel", 50)
    print(f"  卷信息: {context.get('volume', {}).get('current_volume', 'N/A')}")
    print(f"  健康度: {context.get('narrative', {}).get('health_score', 'N/A')}")

    print("\n测试写作指导:")
    guidance = bridge.get_writing_guidance("test_novel", 50)
    print(guidance[:500])
