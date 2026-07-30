"""
OptimizationBridge - 优化桥接层

核心职责:
1. 管理新旧组件的切换
2. 提供统一的接口
3. 处理回退逻辑
4. 确保现有系统稳定

使用方式:
```python
bridge = OptimizationBridge(legacy_workflow)
bridge.initialize_all()

# 正常使用原有系统
result = bridge.legacy_context_selector.select_context(...)

# 或使用新组件
if bridge.narrative_monitor:
    state = bridge.narrative_monitor.get_current_state()
```
"""

from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger("optimization_bridge")


class OptimizationBridge:
    """
    优化桥接层

    特点:
    1. 非侵入式 - 不修改原有系统代码
    2. 可切换 - 通过配置控制启用/禁用
    3. 可回退 - 失败时自动回退到原有逻辑
    """

    def __init__(self, legacy_workflow: Any):
        """
        初始化桥接层

        Args:
            legacy_workflow: 原有工作流对象 (InkAIWorkflowOptimized)
        """
        self.legacy = legacy_workflow
        self.legacy_novel_id = getattr(legacy_workflow, 'novel_id', None)
        self.legacy_data_manager = getattr(legacy_workflow, 'data_manager', None)

        # 新组件 (按需初始化)
        self.narrative_monitor = None
        self.enhanced_context = None
        self.simplified_agent = None

        # 初始化状态
        self._initialized = False

        # 导入配置
        from config_optimization import global_config
        self.config = global_config

        logger.info("[Bridge] 桥接层已创建")

    def initialize_all(self):
        """
        初始化所有启用的组件

        按依赖顺序初始化:
        1. NarrativeStateMonitor
        2. EnhancedContextBuilder
        3. SimplifiedWriterAgent
        """
        if self._initialized:
            logger.warning("[Bridge] 桥接层已初始化,跳过")
            return

        logger.info("[Bridge] 开始初始化组件...")

        # Step 1: NarrativeStateMonitor
        if self.config.is_enabled("step1_narrative_monitor"):
            self._initialize_narrative_monitor()

        # Step 2: EnhancedContextBuilder
        if self.config.is_enabled("step2_enhanced_context"):
            self._initialize_enhanced_context()

        # Step 3: SimplifiedWriterAgent
        if self.config.is_enabled("step3_simplified_agents"):
            self._initialize_simplified_agent()

        self._initialized = True
        logger.info(f"[Bridge] 初始化完成. 启用组件: {self.config.get_all_enabled()}")

    def _initialize_narrative_monitor(self):
        """初始化NarrativeStateMonitor"""
        try:
            from core.narrative_state_monitor import NarrativeStateMonitor

            self.narrative_monitor = NarrativeStateMonitor(
                novel_id=self.legacy_novel_id,
                data_manager=self.legacy_data_manager
            )

            # 如果legacy有integrated_knowledge或dynamic_knowledge_manager,尝试设置
            if hasattr(self.legacy, 'integrated_knowledge'):
                self.narrative_monitor._integrated_knowledge = self.legacy.integrated_knowledge

            if hasattr(self.legacy, 'dynamic_knowledge_manager'):
                self.narrative_monitor._foreshadowing_manager = getattr(
                    self.legacy.intelligent_context_selector,
                    'foreshadowing_manager',
                    None
                )

            logger.info("[Bridge] NarrativeStateMonitor 初始化成功")
        except Exception as e:
            logger.error(f"[Bridge] NarrativeStateMonitor 初始化失败: {e}")
            self.narrative_monitor = None

    def _initialize_enhanced_context(self):
        """初始化EnhancedContextBuilder"""
        if not self.narrative_monitor:
            logger.warning("[Bridge] EnhancedContextBuilder 需要 NarrativeStateMonitor,先初始化Step 1")
            self._initialize_narrative_monitor()

        try:
            from core.enhanced_context_builder import EnhancedContextBuilder

            strategy = self.config.get_config("step2_enhanced_context").get("strategy", "max_context")

            self.enhanced_context = EnhancedContextBuilder(
                data_manager=self.legacy_data_manager,
                narrative_monitor=self.narrative_monitor,
                default_strategy=strategy
            )

            logger.info(f"[Bridge] EnhancedContextBuilder 初始化成功 (strategy={strategy})")
        except Exception as e:
            logger.error(f"[Bridge] EnhancedContextBuilder 初始化失败: {e}")
            self.enhanced_context = None

    def _initialize_simplified_agent(self):
        """初始化SimplifiedWriterAgent"""
        if not self.enhanced_context:
            logger.warning("[Bridge] SimplifiedWriterAgent 需要 EnhancedContextBuilder")
            self._initialize_enhanced_context()

        try:
            from agents.simplified_writer_agent import SimplifiedWriterAgent

            # 获取LLM客户端
            llm_client = getattr(self.legacy, 'llm_client', None) or getattr(self.legacy, 'llm', None)

            self.simplified_agent = SimplifiedWriterAgent(
                llm_client=llm_client,
                context_builder=self.enhanced_context,
                narrative_monitor=self.narrative_monitor
            )

            logger.info("[Bridge] SimplifiedWriterAgent 初始化成功")
        except Exception as e:
            logger.error(f"[Bridge] SimplifiedWriterAgent 初始化失败: {e}")
            self.simplified_agent = None

    def get_narrative_state(self, chapter_num: int = None) -> Optional[Dict[str, Any]]:
        """
        获取剧情状态

        Returns:
            状态字典,如果未启用则返回None
        """
        if not self.narrative_monitor:
            return None

        try:
            return self.narrative_monitor.get_current_state(chapter_num)
        except Exception as e:
            logger.error(f"[Bridge] 获取剧情状态失败: {e}")
            return None

    def get_context_with_fallback(self,
                                  novel_id: str,
                                  chapter_num: int,
                                  user_requirements: str = "",
                                  **kwargs) -> Dict[str, Any]:
        """
        获取上下文 (带回退)

        优先使用EnhancedContextBuilder,失败时回退到原有Selector

        Args:
            novel_id: 小说ID
            chapter_num: 章节号
            user_requirements: 用户需求
            **kwargs: 其他参数

        Returns:
            上下文字典
        """
        # 检查是否启用新组件
        if not self.config.is_enabled("step2_enhanced_context"):
            return self._get_legacy_context(novel_id, chapter_num, user_requirements, **kwargs)

        # 尝试使用EnhancedContextBuilder
        if self.enhanced_context:
            try:
                state = self.get_narrative_state(chapter_num)
                context = self.enhanced_context.build_context(
                    novel_id=novel_id,
                    chapter_num=chapter_num,
                    state=state
                )
                logger.info(f"[Bridge] 使用EnhancedContextBuilder获取上下文 (chapter={chapter_num})")
                return context
            except Exception as e:
                logger.error(f"[Bridge] EnhancedContextBuilder失败: {e}")

                # 回退检查
                if self.config.get_config("step2_enhanced_context").get("fallback_to_legacy", True):
                    logger.info("[Bridge] 回退到原有Selector")
                    return self._get_legacy_context(novel_id, chapter_num, user_requirements, **kwargs)
                raise

        # 默认使用原有Selector
        return self._get_legacy_context(novel_id, chapter_num, user_requirements, **kwargs)

    def _get_legacy_context(self,
                           novel_id: str,
                           chapter_num: int,
                           user_requirements: str,
                           **kwargs) -> Dict[str, Any]:
        """
        获取原有Selector的上下文

        Args:
            novel_id: 小说ID
            chapter_num: 章节号
            user_requirements: 用户需求
            **kwargs: 其他参数

        Returns:
            原有Selector返回的上下文
        """
        if hasattr(self.legacy, 'intelligent_context_selector'):
            try:
                return self.legacy.intelligent_context_selector.select_context(
                    novel_id=novel_id,
                    current_chapter=chapter_num,
                    user_requirements=user_requirements,
                    **kwargs
                )
            except Exception as e:
                logger.error(f"[Bridge] Legacy Selector失败: {e}")
                return {}

        # 没有原有Selector时的备用
        logger.warning("[Bridge] 没有找到原有Selector,返回空上下文")
        return {}

    def update_narrative_state(self, chapter_num: int, chapter_data: Dict[str, Any]):
        """
        更新剧情状态

        Args:
            chapter_num: 章节号
            chapter_data: 章节数据
        """
        if self.narrative_monitor:
            try:
                self.narrative_monitor.update_state(chapter_num, chapter_data)
            except Exception as e:
                logger.error(f"[Bridge] 更新剧情状态失败: {e}")

    def get_health_report(self) -> Optional[Dict[str, Any]]:
        """
        获取健康度报告

        Returns:
            健康度报告,如果未启用则返回None
        """
        if not self.narrative_monitor:
            return None

        try:
            return self.narrative_monitor.run_full_diagnostic()
        except Exception as e:
            logger.error(f"[Bridge] 获取健康度报告失败: {e}")
            return None

    def get_status_summary(self) -> Dict[str, Any]:
        """
        获取桥接层状态摘要

        Returns:
            状态字典
        """
        return {
            "initialized": self._initialized,
            "enabled_steps": self.config.get_all_enabled(),
            "components": {
                "narrative_monitor": self.narrative_monitor is not None,
                "enhanced_context": self.enhanced_context is not None,
                "simplified_agent": self.simplified_agent is not None
            },
            "legacy_available": hasattr(self.legacy, 'intelligent_context_selector')
        }


class OptimizationBridgeContext:
    """
    上下文管理器,用于在现有代码中集成优化桥接

    使用方式:
    ```python
    from core.optimization_bridge import with_bridge

    @with_bridge
    def my_function(bridge, arg1, arg2):
        if bridge.narrative_monitor:
            state = bridge.narrative_monitor.get_current_state()
            # 使用状态
        return result
    ```
    """

    _current_bridge: Optional[OptimizationBridge] = None

    @classmethod
    def set_bridge(cls, bridge: OptimizationBridge):
        """设置当前桥接"""
        cls._current_bridge = bridge

    @classmethod
    def get_bridge(cls) -> Optional[OptimizationBridge]:
        """获取当前桥接"""
        return cls._current_bridge

    @classmethod
    def clear_bridge(cls):
        """清除当前桥接"""
        cls._current_bridge = None


def with_bridge(func):
    """
    装饰器:自动注入桥接层

    使用方式:
    ```python
    @with_bridge
    def my_function(bridge, arg1):
        if bridge.narrative_monitor:
            state = bridge.narrative_monitor.get_current_state()
        return result
    ```
    """
    def wrapper(*args, **kwargs):
        bridge = OptimizationBridgeContext.get_bridge()
        if bridge is None:
            logger.warning(f"[Bridge] {func.__name__} 调用时没有桥接上下文")
            # 不阻止执行,只是没有bridge
            return func(None, *args, **kwargs)
        return func(bridge, *args, **kwargs)
    return wrapper


if __name__ == "__main__":
    print("=== OptimizationBridge 测试 ===\n")

    # 模拟legacy workflow
    class MockLegacyWorkflow:
        novel_id = "test_novel"
        data_manager = None

        class MockSelector:
            def select_context(self, novel_id, current_chapter, user_requirements=""):
                return {"legacy": True, "novel_id": novel_id, "chapter": current_chapter}

        intelligent_context_selector = MockSelector()

    # 创建桥接
    bridge = OptimizationBridge(MockLegacyWorkflow())

    # 检查状态
    print("初始状态:")
    print(f"  {bridge.get_status_summary()}\n")

    # 启用Step 1
    from config_optimization import enable_optimization
    enable_optimization("step1_narrative_monitor")
    bridge.initialize_all()

    print("\n启用后状态:")
    print(f"  {bridge.get_status_summary()}\n")

    # 测试获取状态
    if bridge.narrative_monitor:
        state = bridge.get_narrative_state(1)
        print(f"剧情状态: {state}")

    # 测试上下文获取
    context = bridge.get_context_with_fallback("test", 1, "")
    print(f"\n上下文 (带回退): {context}")
