"""
agents/genre_pack_generator.py —— LLM 一键造题材包

输入：用户的一段自由描述（如"末世废土 × 赛博侦探"）
输出：完整的 GenrePack JSON dict，结构与 data/genres/*.json 完全一致，
      可直接落盘成 data/genres/<name>.json 然后被前端识别。

设计原则：
- 输出严格遵循 GenrePack 数据结构（core/genre_pack.py），无多余/缺失字段
- 风格指引、禁忌、白名单全部由 LLM 自由发挥但必须互相自洽
- 所有 default_tags / default_themes 等字段必须能立刻喂给 OutlinePlanner
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from base_agent import BaseAgent


class GenrePackGenerator(BaseAgent):
    """根据自由描述生成 GenrePack JSON。"""

    def __init__(self):
        super().__init__("题材包生成器")

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        description = (input_data.get("description") or "").strip()
        suggested_name = (input_data.get("name") or "").strip()
        if not description:
            return {"error": "description 不能为空"}

        prompt = self._build_prompt(description, suggested_name)
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位经验丰富的小说题材策划师，精通各种类型小说的核心要素、"
                    "风格惯例、读者期待、写作禁忌。你的任务是把用户给出的题材描述，"
                    "转换成一份结构化、可执行、互相自洽的题材配置包，"
                    "用于驱动一个多智能体 LLM 小说写作系统。"
                ),
            },
            {"role": "user", "content": prompt},
        ]
        try:
            raw = self.call_llm(messages, temperature=0.5)
            data = self.parse_json_response(raw)
            if not isinstance(data, dict):
                return {"error": "LLM 输出不是 JSON 对象"}
            return self._validate_and_normalize(data, description, suggested_name)
        except Exception as exc:
            return {"error": f"题材生成失败：{exc}"}

    # ---------------------------------------------------------------- prompt
    def _build_prompt(self, description: str, suggested_name: str) -> str:
        name_hint = (
            f"建议把 name 字段定为 `{suggested_name}`"
            if suggested_name
            else "请你根据题材描述自己选一个简洁的英文 name（2-20 字符，仅小写字母/数字/下划线）"
        )

        return f"""
请根据以下用户描述，生成一份完整的 **GenrePack** 题材配置 JSON。

【用户题材描述】
{description}

【输出 JSON 的字段结构（每个字段都必须出现，可参考下方说明）】
{{
  "name": "<英文 name；{name_hint}>",
  "display_name": "<中文显示名，例：东方仙侠玄幻>",
  "one_liner": "<一句话描述题材，<=40 字>",
  "style_guide": "<3-6 句话的风格 / 语感指引；告诉写手该用什么腔调、节奏、意象密度、情绪温度>",
  "allowed_elements": ["<5-12 个可出现元素，如：内功、轻功、暗器、江湖恩怨>"],
  "forbidden_elements": ["<3-8 个题材禁忌，如：现代科技、魔法咒语、超能力>"],
  "banned_phrases": ["<8-20 条题材级别绝对不能出现的词/短语，写实细致一些>"],
  "default_tags": {{
    "类型标签": ["<2-4 个>"],
    "主题标签": ["<2-4 个>"],
    "风格标签": ["<2-4 个>"],
    "受众标签": ["<1-3 个>"]
  }},
  "default_world_setting": {{
    "era": "<时代设定>",
    "world_archetype": "<世界形态简述>",
    "power_system": "<力量/能力体系；若无，写"无超自然力量">",
    "tech_baseline": "<科技水平>",
    "key_locations": ["<3-6 个标志性地点类型>"]
  }},
  "default_themes": ["<3-5 条核心主题，每条 <=20 字>"],
  "spec_template": {{
    "user_requirements_template": "<一段对作者的提示模版，可含 {{title}} / {{protagonist_name}} / {{total_chapters}} 三个占位符；用来引导生成 storyline，3-6 句话>",
    "protagonist_skeleton": {{
      "basic_info": {{
        "age": <典型主角年龄整数>,
        "gender": "<男/女>",
        "occupation": "<典型主角职业/身份>",
        "background": "<2-3 句话主角通用出身设定>"
      }},
      "personality": {{
        "traits": ["<3-5 个性格关键词>"],
        "weakness": ["<1-3 条典型弱点>"]
      }},
      "abilities": ["<2-4 条典型能力关键词>"],
      "story_role": "<一句话主角在故事中的功能>"
    }},
    "supporting_skeletons": [
      {{
        "basic_info": {{ "age": <数字>, "gender": "<男/女>", "occupation": "<职业>", "background": "<1 句>" }},
        "personality": {{ "traits": ["<2-3>"] }},
        "story_role": "<一句配角功能>"
      }},
      {{ "basic_info": {{ "age": <数字>, "gender": "<男/女>", "occupation": "<职业>", "background": "<1 句>" }},
         "personality": {{ "traits": ["<2-3>"] }},
         "story_role": "<一句>" }}
    ]
  }}
}}

【重要规则】
1. 只返回纯 JSON，**不要**包含任何 markdown 代码块标记、注释、解释文字
2. 所有字段都必须出现，缺一不可；如果某字段实在没内容，用空数组/空字符串
3. allowed_elements / forbidden_elements / banned_phrases 三组之间不能矛盾
4. supporting_skeletons 至少 2 项；不要包含具体姓名（name 字段留空或不写），只放骨架
5. user_requirements_template 必须自然地用上 {{title}} 和 {{protagonist_name}} 两个占位符
6. name 字段：纯英文小写 + 下划线，长度 2-20，全局唯一标识
""".strip()

    # ---------------------------------------------------------------- normalize
    def _validate_and_normalize(
        self, d: Dict[str, Any], description: str, suggested_name: str
    ) -> Dict[str, Any]:
        """把 LLM 输出补齐成合规结构。"""
        import re

        # name 兜底
        name = (d.get("name") or suggested_name or "").strip()
        name = re.sub(r"[^a-z0-9_]", "_", name.lower())
        if len(name) < 2:
            name = "custom_genre"
        d["name"] = name[:20]

        # 兜底空字段
        for key, default in [
            ("display_name", name),
            ("one_liner", description[:40]),
            ("style_guide", ""),
        ]:
            if not d.get(key):
                d[key] = default

        for key in ("allowed_elements", "forbidden_elements",
                    "banned_phrases", "default_themes"):
            if not isinstance(d.get(key), list):
                d[key] = []

        if not isinstance(d.get("default_tags"), dict):
            d["default_tags"] = {}
        if not isinstance(d.get("default_world_setting"), dict):
            d["default_world_setting"] = {}
        if not isinstance(d.get("spec_template"), dict):
            d["spec_template"] = {}

        # spec_template 内部兜底
        st = d["spec_template"]
        st.setdefault("user_requirements_template", "")
        st.setdefault("protagonist_skeleton", {})
        st.setdefault("supporting_skeletons", [])
        if not isinstance(st["supporting_skeletons"], list):
            st["supporting_skeletons"] = []

        return d
