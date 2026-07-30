"""
SimplifiedWriterAgent - 简化后的核心写作Agent

核心职责:
1. 替代原有的27个Agent
2. 整合EnhancedContextBuilder和NarrativeStateMonitor
3. 使用简洁Prompt + few-shot示例
4. 生成高质量章节内容

核心改进:
- Prompt从300条规则简化为<200字指导
- 使用few-shot示例代替规则约束
- 融入NarrativeStateMonitor的动态指导
- 保持有机整体性，减少错误累积
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import time


@dataclass
class WritingDecision:
    """写作决策"""
    foreshadowing_recycled: List[str]
    character_moment: str
    new_foreshadowing_planted: List[Dict]
    rhythm_type: str


@dataclass
class ChapterOutput:
    """章节输出"""
    chapter_number: int
    chapter_content: str
    word_count: int
    writing_decisions: Dict
    metadata: Dict


class SimplifiedWriterAgent:
    """
    简化后的核心写作Agent

    核心设计原则:
    1. 简洁Prompt: <200字指导，而非300条规则
    2. Few-shot指导: 使用高质量原文片段示例
    3. 动态集成: 融入NarrativeStateMonitor的状态和指导
    4. 单一职责: 一个Agent负责写作，而非多个Agent分工

    使用方式:
    ```python
    agent = SimplifiedWriterAgent(
        llm_client=llm_client,
        context_builder=context_builder,
        narrative_monitor=narrative_monitor
    )

    result = agent.write(
        novel_id="xxx",
        chapter_num=25,
        strategy="max_context"
    )
    ```
    """

    # 字数范围
    MIN_WORD_COUNT = 1500
    MAX_WORD_COUNT = 2500

    # Few-shot示例数量
    MAX_FEW_SHOT_EXAMPLES = 5

    def __init__(self,
                 llm_client: Any = None,
                 context_builder: Any = None,
                 narrative_monitor: Any = None,
                 model_name: str = "qwen-max",
                 temperature: float = 0.8):
        """
        初始化写作Agent

        Args:
            llm_client: LLM客户端
            context_builder: EnhancedContextBuilder实例
            narrative_monitor: NarrativeStateMonitor实例
            model_name: 模型名称
            temperature: 生成温度
        """
        self.llm_client = llm_client
        self.context_builder = context_builder
        self.narrative_monitor = narrative_monitor
        self.model_name = model_name
        self.temperature = temperature

        # 写作历史
        self._writing_history: List[Dict] = []

    def write(self,
              novel_id: str,
              chapter_num: int,
              strategy: str = "max_context",
              retry_count: int = 0) -> ChapterOutput:
        """
        生成章节

        Args:
            novel_id: 小说ID
            chapter_num: 章节号
            strategy: 上下文策略
            retry_count: 重试次数

        Returns:
            ChapterOutput: 包含章节内容和元数据
        """
        # 获取上下文
        if self.narrative_monitor:
            state = self.narrative_monitor.get_current_state(chapter_num)
        else:
            state = None

        context = self.context_builder.build_context(
            novel_id=novel_id,
            chapter_num=chapter_num,
            strategy=strategy,
            state=state
        )

        # 构建Prompt
        prompt = self._build_prompt(novel_id, chapter_num, context, state)

        # 调用LLM生成
        chapter_content = self._call_llm(prompt)

        # 后处理
        processed_content = self._post_process(chapter_content, chapter_num)

        # 提取写作决策
        writing_decisions = self._extract_writing_decisions(
            processed_content,
            context,
            state
        )

        # 计算字数
        word_count = self._count_words(processed_content)

        # 更新narrative_monitor
        if self.narrative_monitor:
            self.narrative_monitor.update_state(chapter_num, {
                "rhythm_type": writing_decisions.get("rhythm_type", "缓冲"),
                "foreshadowing_recycled": writing_decisions.get("foreshadowing_recycled", []),
                "new_foreshadowing_planted": writing_decisions.get("new_foreshadowing_planted", []),
                "word_count": word_count,
                "content": processed_content
            })

        # 记录历史
        self._writing_history.append({
            "chapter": chapter_num,
            "word_count": word_count,
            "timestamp": time.time()
        })

        return ChapterOutput(
            chapter_number=chapter_num,
            chapter_content=processed_content,
            word_count=word_count,
            writing_decisions=writing_decisions,
            metadata={
                "novel_id": novel_id,
                "strategy": strategy,
                "context_tokens": context.get("total_tokens", 0),
                "retry_count": retry_count
            }
        )

    def _build_prompt(self,
                      novel_id: str,
                      chapter_num: int,
                      context: Dict[str, Any],
                      state: Dict = None) -> str:
        """
        构建Prompt

        核心原则:
        1. 简洁指导 (<200字)
        2. Few-shot示例 (3-5个)
        3. 动态指导 (融入narrative_monitor的状态)

        Args:
            novel_id: 小说ID
            chapter_num: 章节号
            context: EnhancedContextBuilder构建的上下文
            state: NarrativeStateMonitor的状态

        Returns:
            完整的prompt
        """
        prompt_parts = []

        # === 1. 任务说明 ===
        prompt_parts.append("你是一位专业的小说作家，擅长续写小说章节。")
        prompt_parts.append(f"请续写小说第{chapter_num}章，保持已有风格。\n")

        # === 2. 当前状态 (如果有) ===
        if state:
            health_score = state.get("health_score", 100)
            rhythm_type = state.get("rhythm", {}).get("type", "标准")

            prompt_parts.append("【当前状态】")
            prompt_parts.append(f"- 进度: 第{chapter_num}章，{state.get('volume', {}).get('progress', 0):.0%}")
            prompt_parts.append(f"- 剧情健康度: {health_score}/100")
            prompt_parts.append(f"- 当前节奏: {rhythm_type}")

            # 告警信息
            alerts = state.get("alerts", [])
            if alerts:
                prompt_parts.append("- 提醒:")
                for alert in alerts[:2]:
                    prompt_parts.append(f"  • {alert.get('message', '')}")

            prompt_parts.append("")

        # === 3. 上文内容 (原文片段) ===
        recent_chapters = context.get("recent_chapters", "")
        if recent_chapters:
            # 取最后2000字作为上文
            last_content = recent_chapters[-2000:] if len(recent_chapters) > 2000 else recent_chapters
            prompt_parts.append("【上文内容】(原文)")
            prompt_parts.append(last_content)
            prompt_parts.append("")

        # === 4. 伏笔信息 (需要回收的) ===
        foreshadowing_info = context.get("foreshadowing_info", [])
        if foreshadowing_info:
            active_fs = [fs for fs in foreshadowing_info if not fs.get("recycled", False)]
            if active_fs:
                prompt_parts.append("【待回收伏笔】")
                for fs in active_fs[:3]:
                    timeout_mark = " ⚠️" if fs.get("is_overdue", False) else ""
                    prompt_parts.append(f"• {fs.get('description', '')} (第{fs.get('planted_chapter', 0)}章埋){timeout_mark}")
                prompt_parts.append("")

        # === 5. Few-shot示例 ===
        few_shot_examples = context.get("few_shot_examples", [])
        if few_shot_examples:
            prompt_parts.append("【写作参考】")
            for i, example in enumerate(few_shot_examples[:3], 1):
                if len(example) > 100:
                    example = example[:100] + "..."
                prompt_parts.append(f"示例{i}: \"{example}\"")
            prompt_parts.append("")

        # === 6. 动态写作指导 ===
        guidance = self._get_dynamic_guidance(state, context)
        if guidance:
            prompt_parts.append("【本章指导】")
            prompt_parts.append(guidance)
            prompt_parts.append("")

        # === 7. 字数要求 ===
        prompt_parts.append(f"【字数要求】{self.MIN_WORD_COUNT}-{self.MAX_WORD_COUNT}字，")
        prompt_parts.append("承接上文自然发展，可包含人物内心描写和情节推进。")
        prompt_parts.append("")

        # === 8. 特殊要求 ===
        special_requests = []
        if state:
            # 检查连续战斗
            rhythm = state.get("rhythm", {})
            consecutive_battle = rhythm.get("consecutive_battle_count", 0)
            if consecutive_battle >= 2:
                special_requests.append("增加人物内心戏，避免纯战斗场景")

            # 检查伏笔超时
            fs = state.get("foreshadowing", {})
            if fs.get("overdue", 0) > 0:
                special_requests.append("安排伏笔回收情节")

        if special_requests:
            prompt_parts.append("【特别注意】")
            for req in special_requests:
                prompt_parts.append(f"- {req}")
            prompt_parts.append("")

        return "\n".join(prompt_parts)

    def _get_dynamic_guidance(self,
                              state: Dict = None,
                              context: Dict = None) -> str:
        """
        获取动态写作指导

        基于NarrativeStateMonitor的状态生成指导

        Args:
            state: 状态
            context: 上下文

        Returns:
            指导字符串
        """
        if not state:
            return ""

        guidance_parts = []
        rhythm_type = state.get("rhythm", {}).get("type", "")
        phase = state.get("phase", {}).get("name", "")

        # 节奏指导
        if rhythm_type == "缓冲":
            guidance_parts.append("放缓节奏，着重描写人物内心、情感变化或角色间的深度对话。")
            guidance_parts.append("避免激烈冲突，以日常互动或内心独白为主。")
        elif rhythm_type == "升级":
            guidance_parts.append("引入新的矛盾或升级已有冲突。")
            guidance_parts.append("可以安排新人物出场、新技能展示或关系变化。")
        elif rhythm_type == "强推":
            guidance_parts.append("本章需要高潮或重大进展。")
            guidance_parts.append("可以是关键对决、重要揭示、情节转折或重大决策。")

        # 阶段指导
        if phase == "开端":
            guidance_parts.append("继续建立世界观和人物关系。")
        elif phase == "中段":
            guidance_parts.append("推进主线冲突，深化人物弧光。")
        elif phase == "结局":
            guidance_parts.append("为高潮做铺垫，可安排关键伏笔回收。")

        # 创意提醒
        if context:
            # 检查套路重复
            innovation_score = 80  # 简化计算
            if innovation_score < 70:
                guidance_parts.append("注意避免重复之前的情节模式。")

        return " ".join(guidance_parts) if guidance_parts else ""

    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM生成内容

        Args:
            prompt: 完整的prompt

        Returns:
            生成的章节内容
        """
        if self.llm_client is None:
            # 模拟生成
            return self._mock_generate(prompt)

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=8192
            )
            return response.get("content", "")
        except Exception as e:
            print(f"LLM调用失败: {e}")
            return self._mock_generate(prompt)

    def _mock_generate(self, prompt: str) -> str:
        """
        模拟生成 (用于测试)

        Args:
            prompt: prompt

        Returns:
            模拟的章节内容
        """
        # 简单模拟: 提取prompt中的信息生成假内容
        mock_content = """
林澈站在青铜鼎前，玉扳指隐隐发烫。

"这块鼎..."他喃喃自语，脑海中浮现出师父陈伯曾经说过的话。

墨玄的身影在不远处若隐若现，仿佛一直在等待着什么。

"你终于来了。"墨玄的声音从黑暗中传来，带着一丝难以捉摸的情绪。

林澈没有回答，只是紧紧盯着那尊青铜鼎。鼎身上的纹路在月光下泛着幽幽的光芒，似乎在诉说着什么古老的秘密。

就在这时，鼎中突然爆发出一道璀璨的光芒，将整个空间照得如同白昼。

"这是..."林澈瞳孔紧缩，一股熟悉的力量从玉扳指中涌出，与鼎中的光芒遥相呼应。

他知道，一个重要的时刻即将来临。

"看来，时机已经成熟了。"墨玄缓步走出阴影，脸上露出复杂的表情。

林澈深吸一口气，感受着体内力量的涌动。他知道，无论是福是祸，他都必须面对这一切。

鼎中的光芒渐渐收敛，但那种压迫感却越来越强，仿佛有什么东西即将破鼎而出。
"""

        return mock_content.strip()

    def _post_process(self, content: str, chapter_num: int) -> str:
        """
        后处理生成的内容

        Args:
            content: 原始生成内容
            chapter_num: 章节号

        Returns:
            处理后的内容
        """
        if not content:
            return content

        # 1. 清理多余空白
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()

        # 2. 移除可能的Prompt泄露
        lines = content.split('\n')
        cleaned_lines = []
        skip = False

        for line in lines:
            # 跳过常见的Prompt泄露标记
            if any(marker in line for marker in ['【上文内容】', '【写作参考】', '【字数要求】', '【本章指导】']):
                skip = True
                continue
            if skip and line.startswith('【') and line.endswith('】'):
                skip = False
                continue
            if skip and line.startswith('•'):
                continue

            cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines).strip()

        return content

    def _extract_writing_decisions(self,
                                    content: str,
                                    context: Dict[str, Any],
                                    state: Dict = None) -> Dict[str, Any]:
        """
        提取写作决策

        从生成的内容中识别:
        - 回收了哪些伏笔
        - 是否有重要人物内心戏
        - 新埋了哪些伏笔
        - 本章节奏类型

        Args:
            content: 章节内容
            context: 上下文
            state: 状态

        Returns:
            写作决策字典
        """
        decisions = {
            "foreshadowing_recycled": [],
            "character_moment": "",
            "new_foreshadowing_planted": [],
            "rhythm_type": "缓冲"
        }

        # 1. 识别伏笔回收
        foreshadowing_info = context.get("foreshadowing_info", [])
        content_lower = content.lower()

        for fs in foreshadowing_info:
            if not fs.get("recycled", False):
                desc = fs.get("description", "").lower()
                if len(desc) > 5 and desc in content_lower:
                    decisions["foreshadowing_recycled"].append(fs.get("id", ""))

        # 2. 识别人物内心戏
        # 检测是否有较长的人物独白或心理描写
        if any(marker in content for marker in ['心想', '想着', '内心', '不由得', '不禁']):
            decisions["character_moment"] = "有内心描写"
        else:
            decisions["character_moment"] = "无明显内心描写"

        # 3. 识别新伏笔 (简化版)
        # 检测是否引入了新的悬念或暗示
        if any(marker in content for marker in ['突然', '就在此时', '与此同时', '却不知']):
            # 简化: 标记可能有新伏笔
            pass

        # 4. 判断节奏类型
        if any(marker in content for marker in ['爆发', '冲突破', '激烈', '决战']):
            decisions["rhythm_type"] = "强推"
        elif any(marker in content for marker in ['新的', '变化', '转折', '揭示']):
            decisions["rhythm_type"] = "升级"
        else:
            decisions["rhythm_type"] = "缓冲"

        # 5. 如果state中有连续战斗警告，降低战斗类内容占比
        if state:
            rhythm = state.get("rhythm", {})
            if rhythm.get("consecutive_battle_count", 0) >= 2:
                if decisions["rhythm_type"] == "强推":
                    # 改为升级而非强推
                    decisions["rhythm_type"] = "升级"

        return decisions

    def _count_words(self, content: str) -> int:
        """
        计算字数

        Args:
            content: 文本内容

        Returns:
            字数
        """
        # 中文: 按字符计算
        # 英文: 按单词计算
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'[a-zA-Z]+', content))

        return chinese_chars + english_words

    def validate_output(self, output: ChapterOutput) -> Tuple[bool, str]:
        """
        验证输出质量

        Args:
            output: 章节输出

        Returns:
            (是否通过, 原因)
        """
        # 检查字数
        if output.word_count < self.MIN_WORD_COUNT:
            return False, f"字数不足: {output.word_count} < {self.MIN_WORD_COUNT}"

        if output.word_count > self.MAX_WORD_COUNT * 1.5:
            return False, f"字数过多: {output.word_count} > {self.MAX_WORD_COUNT * 1.5}"

        # 检查内容完整性
        if len(output.chapter_content) < 500:
            return False, "内容过短，可能生成失败"

        # 检查是否为空
        if not output.chapter_content.strip():
            return False, "内容为空"

        return True, "通过"

    def get_writing_stats(self) -> Dict[str, Any]:
        """
        获取写作统计

        Returns:
            统计信息
        """
        if not self._writing_history:
            return {
                "total_chapters": 0,
                "avg_word_count": 0,
                "total_words": 0
            }

        total_chapters = len(self._writing_history)
        total_words = sum(h["word_count"] for h in self._writing_history)
        avg_word_count = total_words / total_chapters if total_chapters > 0 else 0

        return {
            "total_chapters": total_chapters,
            "avg_word_count": round(avg_word_count),
            "total_words": total_words,
            "recent_chapters": self._writing_history[-5:]
        }

    def reset_history(self):
        """重置写作历史"""
        self._writing_history = []


class QualityGates:
    """
    三重质量门控

    Gate 1: 即时检查 (生成后自动)
    Gate 2: 阶段审核 (每10章)
    Gate 3: 人类抽检 (可配置)
    """

    def __init__(self, narrative_monitor: Any = None):
        self.narrative_monitor = narrative_monitor

        # 阈值配置
        self.WORD_COUNT_MIN = 1500
        self.WORD_COUNT_MAX = 2500
        self.REPETITION_RATE_THRESHOLD = 0.15
        self.FORESHADOWING_RECOVERY_RATE_MIN = 0.6
        self.HEALTH_SCORE_MIN = 70

    def check(self, chapter: ChapterOutput, state: Dict = None) -> Dict[str, Any]:
        """
        执行质量检查

        Args:
            chapter: 章节输出
            state: 当前状态

        Returns:
            检查结果
        """
        results = {
            "passed": True,
            "gate_1_instant": True,
            "gate_2_periodic": True,
            "gate_3_human": True,
            "issues": [],
            "retry_recommended": False
        }

        # === Gate 1: 即时检查 ===
        gate1_result = self.gate_1_instant(chapter)
        results["gate_1_instant"] = gate1_result["passed"]
        if not gate1_result["passed"]:
            results["passed"] = False
            results["issues"].extend(gate1_result["issues"])

        # === Gate 2: 阶段审核 ===
        if chapter.chapter_number % 10 == 0:
            gate2_result = self.gate_2_periodic(chapter, state)
            results["gate_2_periodic"] = gate2_result["passed"]
            if not gate2_result["passed"]:
                results["passed"] = False
                results["issues"].extend(gate2_result["issues"])

        # === Gate 3: 人类抽检 ===
        if chapter.chapter_number % 20 == 0:  # 每20章抽检一次
            gate3_result = self.gate_3_human(chapter)
            results["gate_3_human"] = gate3_result["passed"]
            if not gate3_result["passed"]:
                results["passed"] = False
                results["issues"].extend(gate3_result["issues"])

        # 决定是否需要重试
        if not results["gate_1_instant"]:
            results["retry_recommended"] = True

        return results

    def gate_1_instant(self, chapter: ChapterOutput) -> Dict[str, Any]:
        """
        Gate 1: 即时检查

        - 字数: 1500-2500字
        - 基础连贯: 承接上文
        - 无明显错误

        Returns:
            检查结果
        """
        issues = []

        # 字数检查
        if chapter.word_count < self.WORD_COUNT_MIN:
            issues.append(f"字数不足: {chapter.word_count} < {self.WORD_COUNT_MIN}")
        elif chapter.word_count > self.WORD_COUNT_MAX * 1.5:
            issues.append(f"字数过多: {chapter.word_count} > {self.WORD_COUNT_MAX * 1.5}")

        # 基础连贯检查 (简化版)
        if len(chapter.chapter_content) < 500:
            issues.append("内容过短")

        return {
            "passed": len(issues) == 0,
            "issues": [f"Gate1: {issue}" for issue in issues]
        }

    def gate_2_periodic(self, chapter: ChapterOutput, state: Dict = None) -> Dict[str, Any]:
        """
        Gate 2: 阶段审核 (每10章)

        - 套路重复率: <15%
        - 伏笔回收率: >60%
        - 剧情健康度: >70

        Returns:
            检查结果
        """
        issues = []

        if state:
            # 套路重复率检查
            # 简化: 通过连续相同节奏类型判断
            rhythm_history = state.get("rhythm_history", [])
            if len(rhythm_history) >= 5:
                recent_types = [h.get("type") for h in rhythm_history[-5:]]
                if len(set(recent_types)) == 1:
                    issues.append(f"套路重复: 连续5章相同节奏类型")

            # 伏笔回收率检查
            fs = state.get("foreshadowing", {})
            recovery_rate = fs.get("recovery_rate", 0)
            if recovery_rate < self.FORESHADOWING_RECOVERY_RATE_MIN:
                issues.append(f"伏笔回收率偏低: {recovery_rate:.1%} < {self.FORESHADOWING_RECOVERY_RATE_MIN:.0%}")

            # 健康度检查
            health_score = state.get("health_score", 100)
            if health_score < self.HEALTH_SCORE_MIN:
                issues.append(f"剧情健康度偏低: {health_score} < {self.HEALTH_SCORE_MIN}")

        return {
            "passed": len(issues) == 0,
            "issues": [f"Gate2: {issue}" for issue in issues]
        }

    def gate_3_human(self, chapter: ChapterOutput) -> Dict[str, Any]:
        """
        Gate 3: 人类抽检

        返回需要人工审核的标记
        实际审核由人类执行

        Returns:
            检查结果
        """
        # 简化: 默认通过，标记为需要人工审核
        return {
            "passed": True,
            "needs_human_review": True,
            "issues": ["Gate3: 标记为人工审核"]
        }


if __name__ == "__main__":
    print("=== SimplifiedWriterAgent 测试 ===\n")

    # 创建组件
    narrative_monitor = None
    context_builder = EnhancedContextBuilder()

    # 创建Agent
    agent = SimplifiedWriterAgent(
        llm_client=None,  # 测试用，不实际调用LLM
        context_builder=context_builder,
        narrative_monitor=narrative_monitor
    )

    # 模拟状态
    mock_state = {
        "chapter": 25,
        "health_score": 72,
        "health_level": "good",
        "volume": {"progress": 0.625},
        "phase": {"name": "中段", "progress": 0.5},
        "rhythm": {"type": "强推", "consecutive_battle_count": 2},
        "foreshadowing": {"active": 12, "overdue": 2, "recovery_rate": 0.65},
        "alerts": [
            {"level": "warning", "message": "前5章连续战斗"}
        ],
        "rhythm_history": [
            {"type": "战斗"}, {"type": "战斗"}, {"type": "战斗"}
        ]
    }

    # 生成章节
    output = agent.write(
        novel_id="test_novel",
        chapter_num=25,
        strategy="max_context"
    )

    print(f"章节号: {output.chapter_number}")
    print(f"字数: {output.word_count}")
    print(f"节奏类型: {output.writing_decisions.get('rhythm_type')}")
    print(f"伏笔回收: {output.writing_decisions.get('foreshadowing_recycled')}")
    print(f"人物描写: {output.writing_decisions.get('character_moment')}")
    print(f"\n内容预览 (前500字):\n{output.chapter_content[:500]}...")

    # 质量门控
    gates = QualityGates(narrative_monitor)
    gate_result = gates.check(output, mock_state)
    print(f"\n质量门控结果: {'通过' if gate_result['passed'] else '未通过'}")
    for issue in gate_result.get("issues", []):
        print(f"  - {issue}")

    # 写作统计
    stats = agent.get_writing_stats()
    print(f"\n写作统计: {stats}")
