"""
阶段规划器
负责根据已完成的章节和故事线，生成未来10章的阶段目标
"""

from typing import Dict, List, Any, Optional
import config
import logging

logger = logging.getLogger(__name__)


class PhasePlanner:

    PHASE_LENGTH = 10

    def __init__(self, client=None):
        if client is not None:
            self.client = client
        else:
            from openai import OpenAI
            self.client = OpenAI()

    def plan_phase(self, chapters: List[Dict[str, Any]], current_chapter: int,
                   story_summary: str, user_requirements: str) -> Dict[str, Any]:
        """
        根据前50章原文和故事线，生成未来10章的阶段目标

        Args:
            chapters: 前50章的原文内容列表
            current_chapter: 当前章节号
            story_summary: 故事线概要
            user_requirements: 用户需求

        Returns:
            包含阶段目标的字典
        """
        try:
            logger.info(f"开始规划第{current_chapter + 1}到第{current_chapter + PhasePlanner.PHASE_LENGTH}章的阶段目标")

            phase_start = current_chapter + 1
            phase_end = current_chapter + PhasePlanner.PHASE_LENGTH

            formatted_chapters = self._format_chapters(chapters)

            prompt = f"""
请为小说规划第{phase_start}到第{phase_end}章（共{PhasePlanner.PHASE_LENGTH}章）的阶段目标。

=== 已有章节信息 ===
{formatted_chapters}

=== 当前故事线概要 ===
{story_summary}

=== 用户需求 ===
{user_requirements}

=== 规划要求 ===
1. 分析已有章节的故事发展、人物状态和伏笔埋设情况
2. 规划未来{PhasePlanner.PHASE_LENGTH}章的阶段目标，包括：
   - 每章的标题、概要、关键事件
   - 每章需要埋设的新伏笔
   - 每章需要回收的早期伏笔
3. 整体阶段需要有明确的高潮安排
4. 伏笔需要前后呼应，形成完整的叙事闭环
5. 每章之间需要有逻辑递进关系

=== 输出格式 ===
请以JSON格式输出，结构如下：
{{
    "phase_goals": [
        {{
            "chapter": {phase_start},
            "title": "第{phase_start}章标题",
            "summary": "本章概要",
            "key_events": ["事件1", "事件2"],
            "foreshadowing_to_plant": ["伏笔1"],
            "foreshadowing_to_reveal": ["早期伏笔1"]
        }},
        ...（共{PhasePlanner.PHASE_LENGTH}章）
    ],
    "phase_summary": "本阶段10章的整体概要",
    "climax_arrangement": "高潮安排说明"
}}

请确保输出是有效的JSON格式，不要包含其他解释性文字。
"""

            messages = [
                {"role": "system", "content": """你是一个专业的小说策划专家，擅长故事结构和伏笔设计。

【重要约束】
1. 你必须分析已有章节的内容、人物状态和伏笔
2. 规划的每章目标需要有逻辑递进关系
3. 伏笔的埋设和回收需要前后呼应
4. 阶段需要有明确的高潮安排
5. 输出必须是有效的JSON格式"""},
                {"role": "user", "content": prompt}
            ]

            response = self.call_llm(messages, max_tokens=config.CHAPTER_MAX_TOKENS)

            result = self.parse_json_response(response)

            if "error" in result:
                logger.info(f"阶段规划解析失败: {result['error']}")
                return self._create_default_phase_plan(phase_start)

            validated_result = self._validate_phase_plan(result, phase_start)
            logger.info(f"阶段规划完成，共规划{PhasePlanner.PHASE_LENGTH}章")
            return validated_result

        except Exception as e:
            import traceback
            logger.info(f"阶段规划失败: {e}")
            logger.info(f"详细错误: {traceback.format_exc()}")
            return self._create_default_phase_plan(current_chapter + 1)

    def _format_chapters(self, chapters: List[Dict[str, Any]]) -> str:
        """
        格式化章节信息用于prompt

        Args:
            chapters: 章节列表

        Returns:
            格式化后的章节字符串
        """
        if not chapters:
            return "无章节信息"

        formatted = ""
        for chapter in chapters[-50:]:
            chapter_num = chapter.get("chapter_number", 0)
            title = chapter.get("title", "未知标题")
            summary = chapter.get("summary", "")
            key_events = chapter.get("key_events", [])
            foreshadowing = chapter.get("foreshadowing", [])

            formatted += f"\n第{chapter_num}章：{title}\n"
            if summary:
                formatted += f"  概要：{summary}\n"
            if key_events:
                formatted += f"  关键事件：{', '.join(key_events)}\n"
            if foreshadowing:
                formatted += f"  伏笔：{', '.join(foreshadowing)}\n"

        return formatted

    def _generate_chapter_goals(self, phase_info: Dict[str, Any],
                                 existing_foreshadowing: List[str]) -> List[Dict[str, Any]]:
        """
        生成每章的具体目标

        Args:
            phase_info: 阶段信息
            existing_foreshadowing: 已有的伏笔列表

        Returns:
            每章的具体目标列表
        """
        chapter_goals = phase_info.get("phase_goals", [])

        for i, goal in enumerate(chapter_goals):
            if "foreshadowing_to_plant" not in goal:
                goal["foreshadowing_to_plant"] = []
            if "foreshadowing_to_reveal" not in goal:
                foreshadowing_to_reveal = []
                for fs in existing_foreshadowing:
                    if any(char in fs for char in ['关键', '重要', '核心']):
                        foreshadowing_to_reveal.append(fs)
                goal["foreshadowing_to_reveal"] = foreshadowing_to_reveal[:2]

        return chapter_goals

    def _manage_foreshadowing(self, chapters: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        管理伏笔的埋设和回收

        Args:
            chapters: 章节列表

        Returns:
            包含active和resolved伏笔的字典
        """
        all_foreshadowing = []
        resolved_foreshadowing = []

        for chapter in chapters:
            planted = chapter.get("foreshadowing", [])
            revealed = chapter.get("foreshadowing_revealed", [])

            for fs in planted:
                if fs not in all_foreshadowing:
                    all_foreshadowing.append(fs)

            for fs in revealed:
                if fs in all_foreshadowing and fs not in resolved_foreshadowing:
                    resolved_foreshadowing.append(fs)

        active_foreshadowing = [fs for fs in all_foreshadowing if fs not in resolved_foreshadowing]

        return {
            "active_foreshadowing": active_foreshadowing,
            "resolved_foreshadowing": resolved_foreshadowing,
            "all_foreshadowing": all_foreshadowing
        }

    def _validate_phase_plan(self, result: Dict[str, Any], phase_start: int) -> Dict[str, Any]:
        """
        验证阶段规划结果

        Args:
            result: 解析后的结果
            phase_start: 阶段起始章节号

        Returns:
            验证后的结果
        """
        validated = {
            "phase_goals": [],
            "phase_summary": result.get("phase_summary", ""),
            "climax_arrangement": result.get("climax_arrangement", result.get("climax arrangement", ""))
        }

        phase_goals = result.get("phase_goals", [])
        for i, goal in enumerate(phase_goals):
            chapter_num = phase_start + i
            validated_goal = {
                "chapter": goal.get("chapter", chapter_num),
                "title": goal.get("title", f"第{chapter_num}章"),
                "summary": goal.get("summary", ""),
                "key_events": goal.get("key_events", []),
                "foreshadowing_to_plant": goal.get("foreshadowing_to_plant", []),
                "foreshadowing_to_reveal": goal.get("foreshadowing_to_reveal", [])
            }
            validated["phase_goals"].append(validated_goal)

        if len(validated["phase_goals"]) < PhasePlanner.PHASE_LENGTH:
            for i in range(len(validated["phase_goals"]), PhasePlanner.PHASE_LENGTH):
                chapter_num = phase_start + i
                validated["phase_goals"].append({
                    "chapter": chapter_num,
                    "title": f"第{chapter_num}章",
                    "summary": "待规划",
                    "key_events": [],
                    "foreshadowing_to_plant": [],
                    "foreshadowing_to_reveal": []
                })

        return validated

    def _create_default_phase_plan(self, phase_start: int) -> Dict[str, Any]:
        """
        创建默认的阶段规划

        Args:
            phase_start: 阶段起始章节号

        Returns:
            默认阶段规划
        """
        phase_goals = []
        for i in range(PhasePlanner.PHASE_LENGTH):
            chapter_num = phase_start + i
            phase_goals.append({
                "chapter": chapter_num,
                "title": f"第{chapter_num}章",
                "summary": "待规划",
                "key_events": [],
                "foreshadowing_to_plant": [],
                "foreshadowing_to_reveal": []
            })

        return {
            "phase_goals": phase_goals,
            "phase_summary": "阶段规划待生成",
            "climax_arrangement": "高潮安排待确定"
        }