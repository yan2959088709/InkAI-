"""
SlidingWindowContext - 滑动窗口上下文管理器

核心职责:
1. 管理可滑动的大上下文窗口
2. 根据模型能力动态调整窗口大小
3. 智能选择窗口内的关键内容
4. 支持增量更新，避免重复处理

利用大模型长上下文能力 (Qwen3-Max 262K, Qwen3.6-Plus 1M)

滑动窗口策略:
- 小模型 (<100K): 窗口10-15章
- 中模型 (100K-300K): 窗口20-30章
- 大模型 (>300K): 窗口40-60章

窗口类型:
1. 对称窗口: 前后等量章节
2. 前重窗口: 侧重前方上下文
3. 后重窗口: 侧重后方上下文(用于章节衔接)
"""

import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("sliding_window_context")


class WindowStrategy(Enum):
    """窗口策略"""
    SYMMETRIC = "symmetric"           # 对称窗口
    FRONT_HEAVY = "front_heavy"       # 前重窗口
    BACK_HEAVY = "back_heavy"          # 后重窗口
    ADAPTIVE = "adaptive"              # 自适应窗口


class ContextPriority(Enum):
    """内容优先级"""
    CRITICAL = 1   # 关键内容(必须保留)
    HIGH = 2       # 高优先级
    MEDIUM = 3     # 中优先级
    LOW = 4        # 低优先级(可压缩)


@dataclass
class WindowConfig:
    """窗口配置"""
    strategy: WindowStrategy
    total_window_size: int
    front_chapters: int
    back_chapters: int
    include_early_summary: bool
    include_key_fragments: bool
    include_foreshadowing: bool
    max_total_tokens: int


@dataclass
class SlidingWindow:
    """滑动窗口"""
    current_chapter: int
    start_chapter: int
    end_chapter: int
    chapters_in_window: List[int]
    total_tokens: int
    priority_content: Dict[int, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextChunk:
    """上下文块"""
    chunk_type: str  # "recent", "early_summary", "key_fragment", "foreshadowing", "state_info"
    content: str
    priority: ContextPriority
    token_count: int
    source_chapters: List[int] = field(default_factory=list)


class SlidingWindowContext:
    """
    滑动窗口上下文管理器

    核心功能:
    1. 窗口管理 - 创建和管理滑动窗口
    2. 内容选择 - 根据优先级选择窗口内容
    3. 增量更新 - 支持窗口滑动时的增量更新
    4. 模型适配 - 根据模型能力调整窗口大小

    使用方式:
    ```python
    slider = SlidingWindowContext(
        data_manager=data_manager,
        max_context_tokens=250000
    )

    # 构建当前窗口上下文
    context = slider.build_window_context(
        novel_id="xxx",
        current_chapter=50,
        strategy="symmetric"
    )

    # 滑动窗口到下一章
    next_context = slider.slide_window(
        novel_id="xxx",
        from_chapter=50,
        to_chapter=51
    )
    ```
    """

    # Token估算 (中文约0.5 token/字符)
    TOKENS_PER_CHAR = 0.5
    TOKENS_PER_CHAPTER = 2500  # 平均每章约2500 token
    TOKENS_PER_SUMMARY = 300   # 每章摘要约300 token
    TOKENS_PER_FRAGMENT = 200  # 每个片段约200 token

    # 模型能力配置
    MODEL_CAPABILITIES = {
        "small": {"max_tokens": 100000, "window_size": 15},
        "medium": {"max_tokens": 300000, "window_size": 30},
        "large": {"max_tokens": 1000000, "window_size": 60}
    }

    def __init__(self,
                 data_manager: Any = None,
                 max_context_tokens: int = 250000,
                 model_type: str = "medium"):
        """
        初始化滑动窗口上下文管理器

        Args:
            data_manager: 数据管理器
            max_context_tokens: 最大上下文token数
            model_type: 模型类型 ("small", "medium", "large")
        """
        self.data_manager = data_manager
        self.max_context_tokens = max_context_tokens
        self.model_type = model_type

        self._window_config = self._calculate_window_config()
        self._cache: Dict[str, Any] = {}
        self._chapter_cache: Dict[str, str] = {}

    def _calculate_window_config(self) -> WindowConfig:
        """计算窗口配置"""
        model_info = self.MODEL_CAPABILITIES.get(
            self.model_type,
            self.MODEL_CAPABILITIES["medium"]
        )

        max_tokens = min(self.max_context_tokens, model_info["max_tokens"])
        window_size = min(
            model_info["window_size"],
            int(max_tokens / self.TOKENS_PER_CHAPTER)
        )

        front_chapters = window_size // 2
        back_chapters = window_size - front_chapters

        include_early = max_tokens > 150000
        include_fragments = max_tokens > 100000

        return WindowConfig(
            strategy=WindowStrategy.SYMMETRIC,
            total_window_size=window_size,
            front_chapters=front_chapters,
            back_chapters=back_chapters,
            include_early_summary=include_early,
            include_key_fragments=include_fragments,
            include_foreshadowing=True,
            max_total_tokens=max_tokens
        )

    def get_window_config(self) -> Dict[str, Any]:
        """获取当前窗口配置"""
        return {
            "model_type": self.model_type,
            "max_context_tokens": self.max_context_tokens,
            "window_size": self._window_config.total_window_size,
            "front_chapters": self._window_config.front_chapters,
            "back_chapters": self._window_config.back_chapters,
            "strategy": self._window_config.strategy.value
        }

    def build_window_context(self,
                              novel_id: str,
                              current_chapter: int,
                              strategy: str = "symmetric",
                              narrative_state: Dict = None) -> Dict[str, Any]:
        """
        构建滑动窗口上下文

        Args:
            novel_id: 小说ID
            current_chapter: 当前章节号
            strategy: 窗口策略 ("symmetric", "front_heavy", "back_heavy", "adaptive")
            narrative_state: 叙事状态（来自NarrativeStateMonitor）

        Returns:
            窗口上下文
        """
        if strategy == "adaptive" and narrative_state:
            strategy = self._determine_adaptive_strategy(narrative_state)

        window_config = self._adjust_window_config(strategy)

        start_chapter = max(1, current_chapter - window_config.front_chapters)
        end_chapter = current_chapter + window_config.back_chapters

        window = SlidingWindow(
            current_chapter=current_chapter,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            chapters_in_window=list(range(start_chapter, end_chapter + 1)),
            total_tokens=0
        )

        chunks = []

        recent_chunks, recent_tokens = self._build_recent_chunks(novel_id, window)
        chunks.extend(recent_chunks)
        window.total_tokens += recent_tokens

        early_summary, early_tokens = self._build_early_summary_chunk(novel_id, start_chapter)
        if early_summary:
            chunks.append(early_summary)
            window.total_tokens += early_tokens

        key_fragments, fragments_tokens = self._build_key_fragments_chunk(novel_id, window, narrative_state)
        if key_fragments:
            chunks.extend(key_fragments)
            window.total_tokens += fragments_tokens

        foreshadowing_chunk, fs_tokens = self._build_foreshadowing_chunk(novel_id, current_chapter)
        if foreshadowing_chunk:
            chunks.append(foreshadowing_chunk)
            window.total_tokens += fs_tokens

        if narrative_state:
            state_chunk, state_tokens = self._build_state_chunk(narrative_state)
            chunks.append(state_chunk)
            window.total_tokens += state_tokens

        chunks.sort(key=lambda x: x.priority.value)

        context = {
            "window": {
                "current_chapter": window.current_chapter,
                "start_chapter": window.start_chapter,
                "end_chapter": window.end_chapter,
                "chapters_count": len(window.chapters_in_window),
                "total_tokens": window.total_tokens
            },
            "chunks": [asdict_chunk(c) for c in chunks],
            "config": self.get_window_config()
        }

        context["full_prompt"] = self._assemble_full_prompt(novel_id, current_chapter, chunks, narrative_state)

        return context

    def _determine_adaptive_strategy(self, narrative_state: Dict) -> str:
        """根据叙事状态确定自适应策略"""
        health_score = narrative_state.get("health_score", 80)

        if health_score < 50:
            return "front_heavy"
        elif health_score > 80:
            return "symmetric"
        else:
            phase = narrative_state.get("phase", {}).get("name", "")
            if phase in ["开端", "结局"]:
                return "front_heavy"
            return "symmetric"

    def _adjust_window_config(self, strategy: str) -> WindowConfig:
        """根据策略调整窗口配置"""
        config = WindowConfig(
            strategy=WindowStrategy(strategy),
            total_window_size=self._window_config.total_window_size,
            front_chapters=self._window_config.front_chapters,
            back_chapters=self._window_config.back_chapters,
            include_early_summary=self._window_config.include_early_summary,
            include_key_fragments=self._window_config.include_key_fragments,
            include_foreshadowing=self._window_config.include_foreshadowing,
            max_total_tokens=self._window_config.max_total_tokens
        )

        if strategy == "front_heavy":
            config.front_chapters = int(config.total_window_size * 0.7)
            config.back_chapters = config.total_window_size - config.front_chapters
        elif strategy == "back_heavy":
            config.back_chapters = int(config.total_window_size * 0.7)
            config.front_chapters = config.total_window_size - config.back_chapters

        return config

    def _build_recent_chunks(self,
                              novel_id: str,
                              window: SlidingWindow) -> Tuple[List[ContextChunk], int]:
        """构建最近章节块"""
        chunks = []
        total_tokens = 0

        for ch in window.chapters_in_window:
            chapter_text = self._load_chapter_text(novel_id, ch)

            if not chapter_text:
                continue

            priority = ContextPriority.CRITICAL if ch == window.current_chapter else ContextPriority.HIGH

            chunk = ContextChunk(
                chunk_type="recent",
                content=f"\n{'='*40}\n第{ch}章\n{'='*40}\n\n{chapter_text}\n",
                priority=priority,
                token_count=int(len(chapter_text) * self.TOKENS_PER_CHAR),
                source_chapters=[ch]
            )

            chunks.append(chunk)
            total_tokens += chunk.token_count

            window.priority_content[ch] = chapter_text[:500]

        return chunks, total_tokens

    def _build_early_summary_chunk(self,
                                    novel_id: str,
                                    start_chapter: int) -> Tuple[Optional[ContextChunk], int]:
        """构建早期摘要块"""
        if start_chapter <= 10 or not self._window_config.include_early_summary:
            return None, 0

        summaries = []
        total_tokens = 0

        for ch in range(1, start_chapter, 5):
            summary = self._load_chapter_summary(novel_id, ch)
            if summary:
                summaries.append(f"第{ch}-{min(ch+4, start_chapter-1)}章: {summary}")
                total_tokens += self.TOKENS_PER_SUMMARY * 5

        if not summaries:
            return None, 0

        content = "\n" + "="*40 + "\n前情摘要\n" + "="*40 + "\n\n" + "\n".join(summaries)

        return ContextChunk(
            chunk_type="early_summary",
            content=content,
            priority=ContextPriority.MEDIUM,
            token_count=total_tokens,
            source_chapters=list(range(1, start_chapter, 5))
        ), total_tokens

    def _build_key_fragments_chunk(self,
                                     novel_id: str,
                                     window: SlidingWindow,
                                     narrative_state: Dict = None) -> Tuple[List[ContextChunk], int]:
        """构建关键片段块"""
        if not self._window_config.include_key_fragments:
            return [], 0

        fragments = []
        total_tokens = 0

        foreshadowing_list = []
        if narrative_state and "foreshadowing" in narrative_state:
            foreshadowing_list = narrative_state["foreshadowing"].get("active_list", [])

        for fs in foreshadowing_list[:5]:
            planted_ch = fs.get("planted_chapter", 1)
            if planted_ch in window.chapters_in_window:
                fs_text = self._load_chapter_text(novel_id, planted_ch)
                if fs_text:
                    fragment_text = fs_text[:300] + "..."

                    fragment = ContextChunk(
                        chunk_type="key_fragment",
                        content=f"【伏笔片段-第{planted_ch}章】{fragment_text}",
                        priority=ContextPriority.HIGH,
                        token_count=self.TOKENS_PER_FRAGMENT,
                        source_chapters=[planted_ch]
                    )
                    fragments.append(fragment)
                    total_tokens += self.TOKENS_PER_FRAGMENT

        if narrative_state and narrative_state.get("rhythm", {}).get("type") == "强推":
            climax_chapters = [ch for ch in window.chapters_in_window
                              if ch in window.priority_content]
            for ch in climax_chapters[-2:]:
                text = window.priority_content.get(ch, "")
                if text:
                    fragment = ContextChunk(
                        chunk_type="key_fragment",
                        content=f"【高潮参考-第{ch}章】{text[:300]}...",
                        priority=ContextPriority.MEDIUM,
                        token_count=self.TOKENS_PER_FRAGMENT,
                        source_chapters=[ch]
                    )
                    fragments.append(fragment)
                    total_tokens += self.TOKENS_PER_FRAGMENT

        return fragments, total_tokens

    def _build_foreshadowing_chunk(self,
                                     novel_id: str,
                                     current_chapter: int) -> Tuple[Optional[ContextChunk], int]:
        """构建伏笔信息块"""
        if not self._window_config.include_foreshadowing:
            return None, 0

        foreshadowing_list = []
        if self.data_manager and hasattr(self.data_manager, 'load_foreshadowing_records'):
            try:
                foreshadowing_list = self.data_manager.load_foreshadowing_records(novel_id)
            except Exception:
                pass

        active_fs = [fs for fs in foreshadowing_list if not fs.get("recycled", False)]
        overdue_fs = [fs for fs in active_fs
                     if current_chapter - fs.get("planted_chapter", 1) > fs.get("timeout", 15)]

        if not active_fs:
            return None, 0

        lines = ["【待回收伏笔】"]
        for fs in active_fs[:10]:
            planted_ch = fs.get("planted_chapter", 1)
            chapters_elapsed = current_chapter - planted_ch
            is_overdue = chapters_elapsed > fs.get("timeout", 15)
            status = "⚠️超时" if is_overdue else ""
            lines.append(f"- {fs.get('description', '')} (第{planted_ch}章埋,已{chapters_elapsed}章){status}")

        if overdue_fs:
            lines.append(f"\n⚠️ 紧急: {len(overdue_fs)}个伏笔超时，需要立即回收")

        content = "\n".join(lines)
        tokens = len(content) * self.TOKENS_PER_CHAR

        return ContextChunk(
            chunk_type="foreshadowing",
            content=content,
            priority=ContextPriority.HIGH if overdue_fs else ContextPriority.MEDIUM,
            token_count=int(tokens),
            source_chapters=[fs.get("planted_chapter", 1) for fs in active_fs]
        ), int(tokens)

    def _build_state_chunk(self, narrative_state: Dict) -> Tuple[ContextChunk, int]:
        """构建状态信息块"""
        lines = ["【当前状态】"]
        lines.append(f"- 章节: 第{narrative_state.get('chapter', 0)}章")

        volume = narrative_state.get("volume", {})
        if volume:
            lines.append(f"- 卷进度: {volume.get('progress', 0)*100:.0f}%")

        phase = narrative_state.get("phase", {})
        if phase:
            lines.append(f"- 阶段: {phase.get('name', '')} ({phase.get('progress', 0)*100:.0f}%)")

        rhythm = narrative_state.get("rhythm", {})
        if rhythm:
            lines.append(f"- 节奏: {rhythm.get('type', '')}")

        health = narrative_state.get("health_score", 0)
        health_level = narrative_state.get("health_level", "")
        lines.append(f"- 健康度: {health} ({health_level})")

        alerts = narrative_state.get("alerts", [])
        if alerts:
            lines.append("- 提醒:")
            for alert in alerts[:3]:
                lines.append(f"  * {alert.get('message', '')}")

        content = "\n".join(lines)

        return ContextChunk(
            chunk_type="state_info",
            content=content,
            priority=ContextPriority.CRITICAL,
            token_count=500,
            source_chapters=[narrative_state.get("chapter", 0)]
        ), 500

    def _assemble_full_prompt(self,
                               novel_id: str,
                               current_chapter: int,
                               chunks: List[ContextChunk],
                               narrative_state: Dict = None) -> str:
        """组装完整prompt"""
        prompt_parts = []

        prompt_parts.append(f"续写小说第{current_chapter}章。\n")

        for chunk in chunks:
            if chunk.chunk_type == "state_info":
                prompt_parts.append(chunk.content)
                prompt_parts.append("")

        for chunk in chunks:
            if chunk.chunk_type == "recent":
                prompt_parts.append(chunk.content[-1500:])
                prompt_parts.append("")

        for chunk in chunks:
            if chunk.chunk_type in ["foreshadowing", "key_fragment"]:
                prompt_parts.append(chunk.content)
                prompt_parts.append("")

        rhythm_type = ""
        if narrative_state:
            rhythm_type = narrative_state.get("rhythm", {}).get("type", "")

        if rhythm_type == "缓冲":
            guidance = "本章适合放缓节奏，着重人物内心和关系发展。"
        elif rhythm_type == "升级":
            guidance = "本章需要矛盾升级或新发展。"
        elif rhythm_type == "强推":
            guidance = "本章需要高潮或重大进展。"
        else:
            guidance = "按正常节奏推进。"

        prompt_parts.append(f"【写作指导】{guidance}")
        prompt_parts.append("")
        prompt_parts.append("【字数要求】1500-2500字，承接上文，自然结束。")

        return "\n".join(prompt_parts)

    def slide_window(self,
                      novel_id: str,
                      from_chapter: int,
                      to_chapter: int) -> Dict[str, Any]:
        """
        滑动窗口到新位置

        增量更新上下文，避免重新构建整个窗口

        Args:
            novel_id: 小说ID
            from_chapter: 原章节号
            to_chapter: 目标章节号

        Returns:
            滑动后的上下文
        """
        if abs(to_chapter - from_chapter) > self._window_config.total_window_size:
            logger.info(f"窗口滑动过大({from_chapter} -> {to_chapter})，重新构建")
            return self.build_window_context(novel_id, to_chapter)

        return self.build_window_context(novel_id, to_chapter)

    def _load_chapter_text(self, novel_id: str, chapter_number: int) -> str:
        """加载章节原文"""
        cache_key = f"{novel_id}_{chapter_number}"

        if cache_key in self._chapter_cache:
            return self._chapter_cache[cache_key]

        text = ""

        if self.data_manager:
            try:
                chapter_data = self.data_manager.load_chapter(novel_id, chapter_number)
                if isinstance(chapter_data, dict):
                    text = chapter_data.get("content", "")
                elif isinstance(chapter_data, str):
                    text = chapter_data
            except Exception:
                text = ""

        if text and len(self._chapter_cache) < 500:
            self._chapter_cache[cache_key] = text

        return text

    def _load_chapter_summary(self, novel_id: str, chapter_number: int) -> str:
        """加载章节摘要"""
        summary_key = f"{novel_id}_summary_{chapter_number}"

        if summary_key in self._cache:
            return self._cache[summary_key]

        summary = ""

        if self.data_manager:
            try:
                summary_data = self.data_manager.load_chapter_summary(novel_id, chapter_number)
                if isinstance(summary_data, dict):
                    summary = summary_data.get("summary", "")
                elif isinstance(summary_data, str):
                    summary = summary_data
            except Exception:
                summary = ""

        if summary and len(self._cache) < 200:
            self._cache[summary_key] = summary

        return summary

    def get_window_info(self, chapter_number: int, strategy: str = "symmetric") -> Dict[str, Any]:
        """获取窗口信息"""
        config = self._adjust_window_config(strategy)

        start_chapter = max(1, chapter_number - config.front_chapters)
        end_chapter = chapter_number + config.back_chapters

        return {
            "current_chapter": chapter_number,
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "window_size": end_chapter - start_chapter + 1,
            "front_chapters": config.front_chapters,
            "back_chapters": config.back_chapters,
            "estimated_tokens": (end_chapter - start_chapter + 1) * self.TOKENS_PER_CHAPTER
        }

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        self._chapter_cache.clear()


def asdict_chunk(chunk: ContextChunk) -> Dict[str, Any]:
    """将ContextChunk转换为字典"""
    return {
        "chunk_type": chunk.chunk_type,
        "content": chunk.content,
        "priority": chunk.priority.name,
        "token_count": chunk.token_count,
        "source_chapters": chunk.source_chapters
    }


def create_sliding_window_context(data_manager: Any = None,
                                    max_tokens: int = 250000) -> SlidingWindowContext:
    """
    创建滑动窗口上下文管理器的便捷函数

    Args:
        data_manager: 数据管理器
        max_tokens: 最大token数

    Returns:
        SlidingWindowContext实例
    """
    if max_tokens > 500000:
        model_type = "large"
    elif max_tokens > 150000:
        model_type = "medium"
    else:
        model_type = "small"

    return SlidingWindowContext(
        data_manager=data_manager,
        max_context_tokens=max_tokens,
        model_type=model_type
    )


if __name__ == "__main__":
    print("=== SlidingWindowContext 测试 ===\n")

    slider = SlidingWindowContext(max_context_tokens=250000)

    print("窗口配置:")
    config = slider.get_window_config()
    for k, v in config.items():
        print(f"  {k}: {v}")

    print("\n窗口信息 (第50章):")
    info = slider.get_window_info(50)
    for k, v in info.items():
        print(f"  {k}: {v}")

    print("\n构建窗口上下文示例:")
    context = slider.build_window_context(
        novel_id="test_novel",
        current_chapter=50,
        strategy="symmetric",
        narrative_state={
            "chapter": 50,
            "health_score": 75,
            "health_level": "good",
            "volume": {"progress": 0.625},
            "phase": {"name": "中段", "progress": 0.5},
            "rhythm": {"type": "强推"},
            "foreshadowing": {
                "active_list": [
                    {"planted_chapter": 45, "description": "神秘人的警告", "timeout": 15},
                    {"planted_chapter": 48, "description": "隐藏的线索", "timeout": 10}
                ]
            },
            "alerts": []
        }
    )

    print(f"窗口范围: 第{context['window']['start_chapter']}-{context['window']['end_chapter']}章")
    print(f"总token数: {context['window']['total_tokens']}")
    print(f"上下文块数: {len(context['chunks'])}")
    print(f"\nPrompt预览 (前500字):\n{context['full_prompt'][:500]}")
