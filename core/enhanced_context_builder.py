"""
EnhancedContextBuilder - 增强上下文构建器

核心职责:
1. 构建高质量上下文，替代原有的IntelligentContextSelector
2. 支持多种上下文策略:
   - STRATEGY_A (大上下文): 最近30章原文 + 摘要
   - STRATEGY_B (关键片段): 伏笔/高潮原文片段
   - STRATEGY_C (混合): 可配置配比
3. 保留原文片段用于few-shot指导
4. 与NarrativeStateMonitor集成获取状态

核心改进:
- 传入原文而非压缩后的结构化数据
- 保留语言风格、情感细节、场景氛围
- 为LLM提供高质量的few-shot示例
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class ContextStrategy:
    """上下文策略配置"""
    name: str
    recent_chapters_count: int
    recent_chapters_full: bool
    early_summary_ratio: float
    include_key_fragments: bool
    include_foreshadowing: bool
    include_state_info: bool
    max_total_tokens: int


class EnhancedContextBuilder:
    """
    增强上下文构建器

    核心原则:
    1. 传入原文而非压缩摘要 (保留语言风格)
    2. 提供关键片段用于few-shot指导
    3. 与NarrativeStateMonitor状态集成
    4. 支持多种策略配置

    使用方式:
    ```python
    builder = EnhancedContextBuilder(
        data_manager=data_manager,
        narrative_monitor=narrative_monitor
    )

    context = builder.build_context(
        novel_id="xxx",
        chapter_num=25,
        strategy="max_context"
    )
    ```
    """

    # 内置策略配置
    STRATEGIES = {
        "max_context": ContextStrategy(
            name="max_context",
            recent_chapters_count=30,
            recent_chapters_full=True,
            early_summary_ratio=0.3,
            include_key_fragments=True,
            include_foreshadowing=True,
            include_state_info=True,
            max_total_tokens=250000
        ),
        "key_fragment": ContextStrategy(
            name="key_fragment",
            recent_chapters_count=5,
            recent_chapters_full=True,
            early_summary_ratio=0.5,
            include_key_fragments=True,
            include_foreshadowing=True,
            include_state_info=True,
            max_total_tokens=100000
        ),
        "hybrid": ContextStrategy(
            name="hybrid",
            recent_chapters_count=15,
            recent_chapters_full=True,
            early_summary_ratio=0.4,
            include_key_fragments=True,
            include_foreshadowing=True,
            include_state_info=True,
            max_total_tokens=150000
        )
    }

    # Token估算 (中文)
    TOKENS_PER_CHAR = 0.5
    TOKENS_PER_CHAPTER_SUMMARY = 250
    TOKENS_PER_FRAGMENT = 300

    def __init__(self,
                 data_manager: Any = None,
                 narrative_monitor: Any = None,
                 default_strategy: str = "max_context"):
        """
        初始化增强上下文构建器

        Args:
            data_manager: 数据管理器
            narrative_monitor: 剧情状态监控中心
            default_strategy: 默认策略
        """
        self.data_manager = data_manager
        self.narrative_monitor = narrative_monitor
        self.default_strategy = default_strategy

        # 缓存
        self._chapter_cache: Dict[str, Dict] = {}
        self._summary_cache: Dict[str, str] = {}

    def build_context(self,
                      novel_id: str,
                      chapter_num: int,
                      strategy: str = None,
                      state: Dict = None) -> Dict[str, Any]:
        """
        构建上下文

        Args:
            novel_id: 小说ID
            chapter_num: 当前章节号
            strategy: 策略名称 (默认使用配置的default_strategy)
            state: 剧情状态 (如果为None，从narrative_monitor获取)

        Returns:
            上下文字典
        """
        strategy_name = strategy or self.default_strategy
        strategy_config = self.STRATEGIES.get(strategy_name, self.STRATEGIES["max_context"])

        # 获取状态
        if state is None and self.narrative_monitor:
            state = self.narrative_monitor.get_current_state(chapter_num)

        # 构建各部分上下文
        context_parts = {}

        # 1. 最近章节原文
        recent_text, recent_tokens = self._build_recent_chapters(
            novel_id, chapter_num, strategy_config
        )
        context_parts["recent_chapters"] = recent_text
        context_parts["recent_chapters_tokens"] = recent_tokens

        # 2. 早期章节摘要
        early_summary, early_tokens = self._build_early_summary(
            novel_id, chapter_num, strategy_config
        )
        context_parts["early_summary"] = early_summary
        context_parts["early_summary_tokens"] = early_tokens

        # 3. 关键片段 (伏笔/高潮原文)
        if strategy_config.include_key_fragments:
            key_fragments, fragments_tokens = self._build_key_fragments(
                novel_id, chapter_num, state
            )
            context_parts["key_fragments"] = key_fragments
            context_parts["key_fragments_tokens"] = fragments_tokens
        else:
            context_parts["key_fragments"] = []
            context_parts["key_fragments_tokens"] = 0

        # 4. 伏笔信息
        if strategy_config.include_foreshadowing:
            foreshadowing_info, fs_tokens = self._build_foreshadowing_info(
                novel_id, chapter_num, state
            )
            context_parts["foreshadowing_info"] = foreshadowing_info
            context_parts["foreshadowing_tokens"] = fs_tokens
        else:
            context_parts["foreshadowing_info"] = []
            context_parts["foreshadowing_tokens"] = 0

        # 5. 状态信息
        if strategy_config.include_state_info and state:
            state_info, state_tokens = self._build_state_info(state)
            context_parts["state_info"] = state_info
            context_parts["state_tokens"] = state_tokens
        else:
            context_parts["state_info"] = {}
            context_parts["state_tokens"] = 0

        # 计算总token数
        total_tokens = (
            recent_tokens +
            early_tokens +
            fragments_tokens +
            fs_tokens +
            context_parts["state_tokens"]
        )
        context_parts["total_tokens"] = total_tokens

        # 6. 生成用于few-shot的原文片段
        context_parts["few_shot_examples"] = self._build_few_shot_examples(
            context_parts["recent_chapters"],
            context_parts["key_fragments"]
        )

        # 7. 生成完整prompt
        context_parts["full_prompt"] = self._build_full_prompt(
            novel_id, chapter_num, context_parts
        )

        return context_parts

    def _build_recent_chapters(self,
                               novel_id: str,
                               chapter_num: int,
                               strategy: ContextStrategy) -> Tuple[str, int]:
        """
        构建最近章节原文

        Args:
            novel_id: 小说ID
            chapter_num: 当前章节号
            strategy: 策略配置

        Returns:
            (原文字符串, token数)
        """
        chapters = []
        total_tokens = 0

        recent_count = strategy.recent_chapters_count
        start_chapter = max(1, chapter_num - recent_count + 1)

        for ch in range(start_chapter, chapter_num + 1):
            chapter_text = self._load_chapter_text(novel_id, ch)

            if chapter_text:
                # 标记章节开头
                formatted_chapter = f"\n{'='*40}\n第{ch}章\n{'='*40}\n\n{chapter_text}\n"
                chapters.append(formatted_chapter)
                total_tokens += len(chapter_text) * self.TOKENS_PER_CHAR

        return "\n".join(chapters), int(total_tokens)

    def _build_early_summary(self,
                             novel_id: str,
                             chapter_num: int,
                             strategy: ContextStrategy) -> Tuple[str, int]:
        """
        构建早期章节摘要

        Args:
            novel_id: 小说ID
            chapter_num: 当前章节号
            strategy: 策略配置

        Returns:
            (摘要字符串, token数)
        """
        if chapter_num <= strategy.recent_chapters_count:
            return "", 0

        # 计算需要摘要的章节范围
        early_end = max(1, chapter_num - strategy.recent_chapters_count)
        summary_parts = []
        total_tokens = 0

        # 动态决定摘要密度
        early_chapters = early_end - 1
        if early_chapters > 50:
            # 早期章节: 每10章一个摘要
            for ch in range(1, early_end, 10):
                summary = self._load_chapter_summary(novel_id, ch)
                if summary:
                    summary_parts.append(f"第{ch}-{min(ch+9, early_end-1)}章: {summary}")
                    total_tokens += self.TOKENS_PER_CHAPTER_SUMMARY * 10
        else:
            # 较近的早期: 每5章一个摘要
            for ch in range(1, early_end, 5):
                summary = self._load_chapter_summary(novel_id, ch)
                if summary:
                    summary_parts.append(f"第{ch}-{min(ch+4, early_end-1)}章: {summary}")
                    total_tokens += self.TOKENS_PER_CHAPTER_SUMMARY * 5

        header = f"\n{'='*40}\n前情摘要 (第1-{early_end-1}章)\n{'='*40}\n\n"
        return header + "\n".join(summary_parts), int(total_tokens)

    def _build_key_fragments(self,
                             novel_id: str,
                             chapter_num: int,
                             state: Dict = None) -> Tuple[List[Dict], int]:
        """
        构建关键片段

        包含:
        - 伏笔埋入原文
        - 高潮/转折原文
        - 重要对话片段

        Args:
            novel_id: 小说ID
            chapter_num: 当前章节号
            state: 剧情状态

        Returns:
            (片段列表, token数)
        """
        fragments = []
        total_tokens = 0

        # 加载伏笔记录
        foreshadowing_list = []
        if self.data_manager and hasattr(self.data_manager, 'load_foreshadowing_records'):
            try:
                foreshadowing_list = self.data_manager.load_foreshadowing_records(novel_id)
            except Exception:
                foreshadowing_list = []

        # 添加伏笔原文片段
        for fs in foreshadowing_list:
            if not fs.get("recycled", False):
                planted_ch = fs.get("planted_chapter", 1)
                if abs(planted_ch - chapter_num) <= 30:  # 只包含近30章的伏笔
                    fs_text = self._load_chapter_text(novel_id, planted_ch)
                    if fs_text and fs.get("description"):
                        # 尝试提取伏笔相关的片段
                        fragment_text = self._extract_relevant_fragment(
                            fs_text, fs.get("description", "")
                        )

                        fragments.append({
                            "type": "foreshadowing",
                            "planted_chapter": planted_ch,
                            "description": fs.get("description", ""),
                            "text": fragment_text
                        })
                        total_tokens += self.TOKENS_PER_FRAGMENT

        # 添加高潮片段 (最近3个)
        climax_chapters = []
        if self.data_manager and hasattr(self.data_manager, 'get_climax_chapters'):
            try:
                climax_chapters = self.data_manager.get_climax_chapters(novel_id, limit=3)
            except Exception:
                climax_chapters = []

        for ch in climax_chapters[-3:]:
            if ch != chapter_num:  # 不包含当前章节
                climax_text = self._load_chapter_text(novel_id, ch)
                if climax_text:
                    # 提取前500字作为高潮片段
                    fragment_text = climax_text[:500] + "..."

                    fragments.append({
                        "type": "climax",
                        "chapter": ch,
                        "text": fragment_text
                    })
                    total_tokens += self.TOKENS_PER_FRAGMENT

        # 添加重要对话片段 (从最近章节)
        recent_text = self._build_recent_chapters_text(novel_id, chapter_num, 5)
        if recent_text:
            dialogue_fragments = self._extract_dialogue_fragments(recent_text, max_count=3)
            for df in dialogue_fragments:
                fragments.append({
                    "type": "dialogue",
                    "text": df
                })
                total_tokens += self.TOKENS_PER_FRAGMENT

        return fragments, int(total_tokens)

    def _build_foreshadowing_info(self,
                                   novel_id: str,
                                   chapter_num: int,
                                   state: Dict = None) -> Tuple[List[Dict], int]:
        """
        构建伏笔信息

        Args:
            novel_id: 小说ID
            chapter_num: 当前章节号
            state: 剧情状态

        Returns:
            (伏笔信息列表, token数)
        """
        foreshadowing_list = []
        total_tokens = 0

        if self.data_manager and hasattr(self.data_manager, 'load_foreshadowing_records'):
            try:
                foreshadowing_list = self.data_manager.load_foreshadowing_records(novel_id)
            except Exception:
                pass

        fs_info = []
        for fs in foreshadowing_list:
            planted_ch = fs.get("planted_chapter", 1)
            chapters_since_planted = chapter_num - planted_ch

            fs_data = {
                "id": fs.get("id", ""),
                "description": fs.get("description", ""),
                "planted_chapter": planted_ch,
                "type": fs.get("type", "medium"),
                "recycled": fs.get("recycled", False),
                "recycled_chapter": fs.get("recycled_chapter", None),
                "chapters_since_planted": chapters_since_planted,
                "is_overdue": chapters_since_planted > self._get_timeout(fs.get("type", "medium"))
            }

            fs_info.append(fs_data)
            total_tokens += 100  # 每个伏笔约100 token

        # 按超时和类型排序
        fs_info.sort(key=lambda x: (x["is_overdue"], -x["chapters_since_planted"]), reverse=True)

        return fs_info, int(total_tokens)

    def _build_state_info(self, state: Dict) -> Tuple[Dict, int]:
        """
        构建状态信息

        Args:
            state: NarrativeStateMonitor的状态

        Returns:
            (状态信息字典, token数)
        """
        state_info = {
            "chapter": state.get("chapter", 0),
            "health_score": state.get("health_score", 100),
            "health_level": state.get("health_level", "unknown"),
            "volume_progress": state.get("volume", {}).get("progress", 0),
            "phase": state.get("phase", {}).get("name", ""),
            "phase_progress": state.get("phase", {}).get("progress", 0),
            "rhythm_type": state.get("rhythm", {}).get("type", ""),
            "foreshadowing": {
                "active": state.get("foreshadowing", {}).get("active", 0),
                "overdue": state.get("foreshadowing", {}).get("overdue", 0),
                "recovery_rate": state.get("foreshadowing", {}).get("recovery_rate", 0)
            },
            "alerts": [
                {
                    "level": a.get("level", ""),
                    "message": a.get("message", "")
                }
                for a in state.get("alerts", [])[:3]  # 只取前3个告警
            ]
        }

        # 估算token
        state_tokens = 500

        return state_info, state_tokens

    def _build_few_shot_examples(self,
                                  recent_chapters: str,
                                  key_fragments: List[Dict]) -> List[str]:
        """
        构建few-shot示例

        从最近章节和关键片段中提取高质量示例

        Args:
            recent_chapters: 最近章节原文
            key_fragments: 关键片段

        Returns:
            few-shot示例列表
        """
        examples = []

        # 从高潮片段提取
        for fragment in key_fragments:
            if fragment.get("type") == "climax":
                examples.append(fragment.get("text", "")[:300])

        # 从伏笔片段提取
        for fragment in key_fragments[:2]:
            if fragment.get("type") == "foreshadowing":
                examples.append(fragment.get("text", "")[:200])

        # 从最近章节提取对话片段
        if recent_chapters:
            dialogues = self._extract_dialogue_fragments(recent_chapters, max_count=2)
            examples.extend(dialogues)

        return examples[:5]  # 最多5个示例

    def _build_full_prompt(self,
                           novel_id: str,
                           chapter_num: int,
                           context: Dict[str, Any]) -> str:
        """
        构建完整的Prompt

        Args:
            novel_id: 小说ID
            chapter_num: 当前章节号
            context: 上下文内容

        Returns:
            完整的prompt字符串
        """
        prompt_parts = []

        # Header
        prompt_parts.append(f"续写小说第{chapter_num}章。\n")

        # 当前状态
        if context.get("state_info"):
            state = context["state_info"]
            prompt_parts.append(f"【当前状态】")
            prompt_parts.append(f"- 已完成{state['chapter']}章，整体进度{state['volume_progress']:.0%}")
            prompt_parts.append(f"- 当前阶段: {state['phase']} (进度{state['phase_progress']:.0%})")
            prompt_parts.append(f"- 剧情健康度: {state['health_score']} ({state['health_level']})")

            if state['foreshadowing']['active'] > 0:
                overdue = state['foreshadowing']['overdue']
                prompt_parts.append(f"- 伏笔: 活跃{state['foreshadowing']['active']}个" +
                                  (f"，其中{overdue}个超时" if overdue > 0 else ""))

            # 添加告警
            if state.get("alerts"):
                prompt_parts.append("- 提醒:")
                for alert in state["alerts"]:
                    prompt_parts.append(f"  * {alert['message']}")

            prompt_parts.append("")

        # 最近章节原文
        if context.get("recent_chapters"):
            prompt_parts.append("【上文内容】(原文)")
            prompt_parts.append(context["recent_chapters"][-2000:] if len(context["recent_chapters"]) > 2000
                              else context["recent_chapters"])
            prompt_parts.append("")

        # 伏笔信息
        if context.get("foreshadowing_info"):
            active_fs = [fs for fs in context["foreshadowing_info"] if not fs["recycled"]]
            if active_fs:
                prompt_parts.append("【待回收伏笔】")
                for fs in active_fs[:5]:
                    status = "⚠️超时" if fs["is_overdue"] else ""
                    prompt_parts.append(f"- {fs['description']} (第{fs['planted_chapter']}章){status}")
                prompt_parts.append("")

        # 关键片段 (few-shot)
        if context.get("key_fragments"):
            prompt_parts.append("【参考片段】")
            for i, fragment in enumerate(context["key_fragments"][:3], 1):
                fragment_type = fragment.get("type", "")
                if fragment_type == "foreshadowing":
                    prompt_parts.append(f"{i}. 伏笔片段(第{fragment['planted_chapter']}章): \"{fragment['text'][:150]}...\"")
                elif fragment_type == "climax":
                    prompt_parts.append(f"{i}. 高潮片段(第{fragment['chapter']}章): \"{fragment['text'][:150]}...\"")
            prompt_parts.append("")

        # 写作指导
        if context.get("state_info"):
            rhythm_type = context["state_info"].get("rhythm_type", "")
            if rhythm_type == "缓冲":
                guidance = "本章适合放缓节奏，着重人物内心和关系发展。"
            elif rhythm_type == "升级":
                guidance = "本章需要矛盾升级或新发展。"
            elif rhythm_type == "强推":
                guidance = "本章需要高潮或重大进展。"
            else:
                guidance = "按正常节奏推进。"

            # 检查告警
            alerts = context["state_info"].get("alerts", [])
            for alert in alerts:
                if "战斗" in alert.get("message", ""):
                    guidance += " 注意增加非战斗内容平衡节奏。"
                    break

            prompt_parts.append(f"【写作指导】{guidance}")
            prompt_parts.append("")

        # 字数指导
        prompt_parts.append("【字数要求】1500-2500字，承接上文，自然结束。")

        return "\n".join(prompt_parts)

    def _load_chapter_text(self, novel_id: str, chapter_num: int) -> str:
        """加载章节原文"""
        cache_key = f"{novel_id}_{chapter_num}"

        if cache_key in self._chapter_cache:
            return self._chapter_cache[cache_key]

        text = ""

        if self.data_manager:
            try:
                chapter_data = self.data_manager.load_chapter(novel_id, chapter_num)
                if isinstance(chapter_data, dict):
                    text = chapter_data.get("content", "")
                elif isinstance(chapter_data, str):
                    text = chapter_data
            except Exception:
                text = ""

        # 缓存
        if text and len(self._chapter_cache) < 100:
            self._chapter_cache[cache_key] = text

        return text

    def _build_recent_chapters_text(self, novel_id: str, chapter_num: int, count: int) -> str:
        """构建最近N章的原文"""
        chapters = []
        start_ch = max(1, chapter_num - count)

        for ch in range(start_ch, chapter_num + 1):
            text = self._load_chapter_text(novel_id, ch)
            if text:
                chapters.append(text)

        return "\n".join(chapters)

    def _load_chapter_summary(self, novel_id: str, chapter_num: int) -> str:
        """加载章节摘要"""
        cache_key = f"{novel_id}_summary_{chapter_num}"

        if cache_key in self._summary_cache:
            return self._summary_cache[cache_key]

        summary = ""

        if self.data_manager:
            try:
                summary_data = self.data_manager.load_chapter_summary(novel_id, chapter_num)
                if isinstance(summary_data, dict):
                    summary = summary_data.get("summary", "")
                elif isinstance(summary_data, str):
                    summary = summary_data
            except Exception:
                summary = ""

        # 缓存
        if summary and len(self._summary_cache) < 100:
            self._summary_cache[cache_key] = summary

        return summary

    def _extract_relevant_fragment(self, text: str, keyword: str) -> str:
        """
        提取与关键词相关的文本片段

        Args:
            text: 原文
            keyword: 关键词

        Returns:
            相关片段 (约200字)
        """
        # 简单实现: 查找包含关键词的位置，返回周围200字
        keyword = keyword[:10]  # 取前10字
        pos = text.find(keyword)

        if pos == -1:
            return text[:200]

        start = max(0, pos - 100)
        end = min(len(text), pos + 100)

        return text[start:end]

    def _extract_dialogue_fragments(self, text: str, max_count: int = 3) -> List[str]:
        """
        从文本中提取对话片段

        Args:
            text: 原文
            max_count: 最大提取数量

        Returns:
            对话片段列表
        """
        fragments = []

        # 简单实现: 匹配引号内的内容
        pattern = r'"([^"]{20,200})"'
        matches = re.findall(pattern, text)

        for match in matches[:max_count]:
            fragments.append(f'"{match}"')

        return fragments

    def _get_timeout(self, fs_type: str) -> int:
        """获取伏笔超时阈值"""
        timeouts = {
            "short": 5,
            "medium": 15,
            "long": 30
        }
        return timeouts.get(fs_type, 15)

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            name: {
                "recent_chapters": s.recent_chapters_count,
                "max_tokens": s.max_total_tokens,
                "description": self._get_strategy_description(name)
            }
            for name, s in self.STRATEGIES.items()
        }

    def _get_strategy_description(self, name: str) -> str:
        """获取策略描述"""
        descriptions = {
            "max_context": "最大上下文策略，约25万token，包含30章原文和摘要",
            "key_fragment": "关键片段策略，约10万token，包含伏笔/高潮原文",
            "hybrid": "混合策略，约15万token，平衡上下文长度和信息量"
        }
        return descriptions.get(name, "")

    def clear_cache(self):
        """清除缓存"""
        self._chapter_cache.clear()
        self._summary_cache.clear()


if __name__ == "__main__":
    builder = EnhancedContextBuilder()

    print("=== 上下文构建器测试 ===")
    print("\n可用策略:")
    for name, info in builder.get_strategy_info().items():
        print(f"\n{name}:")
        print(f"  最近章节数: {info['recent_chapters']}")
        print(f"  最大token: {info['max_tokens']}")
        print(f"  描述: {info['description']}")

    print("\n=== 构建示例上下文 ===")
    context = builder.build_context(
        novel_id="test_novel",
        chapter_num=25,
        strategy="max_context",
        state={
            "chapter": 25,
            "health_score": 72,
            "health_level": "good",
            "volume": {"progress": 0.625},
            "phase": {"name": "中段", "progress": 0.5},
            "rhythm": {"type": "强推"},
            "foreshadowing": {"active": 12, "overdue": 2, "recovery_rate": 0.65},
            "alerts": [
                {"level": "warning", "message": "前5章连续战斗"}
            ]
        }
    )

    print(f"\n上下文统计:")
    print(f"- 最近章节token: {context['recent_chapters_tokens']}")
    print(f"- 早期摘要token: {context['early_summary_tokens']}")
    print(f"- 关键片段token: {context['key_fragments_tokens']}")
    print(f"- 伏笔信息token: {context['foreshadowing_tokens']}")
    print(f"- 状态信息token: {context['state_tokens']}")
    print(f"- 总token: {context['total_tokens']}")

    print(f"\nFew-shot示例数: {len(context['few_shot_examples'])}")
    print(f"\n完整Prompt预览 (前500字):")
    print(context['full_prompt'][:500])
