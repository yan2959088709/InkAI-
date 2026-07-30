"""
GenrePack —— 题材配置包（数据结构 + 加载器 + 注入器）

设计目标
--------
当前的 OutlinePlanner / ChapterCardWriter 在 system prompt 层面已经是"题材中立"的，
所有题材内容都通过 NovelSpec(metadata + characters + storyline) 间接注入。
GenrePack 不重写这套，而是在它之上加一层"题材风格指引"：

1. 一份可序列化的 JSON 描述（方便用户改、方便调试）
2. 描述中包含：
   - 题材名称、显示名、一句话简介
   - 应注入到 LLM system prompt 的题材指引（什么允许、什么禁止）
   - 题材级 banned_phrases（与 banned_endings 的"避免重复钩子"是两件事，
     这是"题材里就不能出现的词汇/概念"）
   - 推荐 tags / world_setting key / themes（用于 bootstrap 新小说时填充）
   - spec_template（一键生成 metadata.json / characters.json / storyline.json 用的骨架）

加载方式
--------
- GenrePack.from_dict(d)              ← 内存里的字典
- GenrePack.from_file(path)           ← 单个 JSON 文件
- GenrePack.from_registry(name)       ← 从 data/genres/<name>.json 读

注入方式
--------
- Planner / Writer 暂时统一调用 pack.system_prompt_addon() 拿到一段 markdown 文本，
  追加到自己原本的 system prompt 后面。这样保证"无 GenrePack 时行为完全等价于现在"。

兜底原则
--------
- 所有字段都可选；缺字段时返回空字符串/空数组，调用方自然不会注入额外内容。
- 加载失败/找不到题材时返回 None，调用方应当能"无 pack 也能跑"。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import config


@dataclass
class GenrePack:
    """题材配置包。所有字段可选；只有 name 必填。"""

    name: str
    display_name: str = ""
    one_liner: str = ""

    # —— LLM 提示注入相关 —— #
    style_guide: str = ""              # 风格/语感指引（追加到 system prompt）
    allowed_elements: List[str] = field(default_factory=list)  # 题材内允许出现的元素清单
    forbidden_elements: List[str] = field(default_factory=list)  # 题材禁忌（追加到 system prompt）
    banned_phrases: List[str] = field(default_factory=list)    # 题材级禁词（不应出现在正文）

    # —— bootstrap 一本新小说时复用的字段 —— #
    default_tags: Dict[str, Any] = field(default_factory=dict)
    default_world_setting: Dict[str, Any] = field(default_factory=dict)
    default_themes: List[str] = field(default_factory=list)
    spec_template: Dict[str, Any] = field(default_factory=dict)
    # spec_template 推荐结构：
    # {
    #   "user_requirements_template": "..."（可含 {title}/{protagonist_name} 占位符）,
    #   "protagonist_skeleton": {...},
    #   "supporting_skeletons": [{...}],
    #   "world_setting_extras": {...}
    # }

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GenrePack":
        if not isinstance(d, dict) or not d.get("name"):
            raise ValueError("GenrePack.from_dict: 缺少必填字段 name")
        return cls(
            name=str(d["name"]).strip(),
            display_name=str(d.get("display_name") or "").strip(),
            one_liner=str(d.get("one_liner") or "").strip(),
            style_guide=str(d.get("style_guide") or "").strip(),
            allowed_elements=list(d.get("allowed_elements") or []),
            forbidden_elements=list(d.get("forbidden_elements") or []),
            banned_phrases=list(d.get("banned_phrases") or []),
            default_tags=dict(d.get("default_tags") or {}),
            default_world_setting=dict(d.get("default_world_setting") or {}),
            default_themes=list(d.get("default_themes") or []),
            spec_template=dict(d.get("spec_template") or {}),
        )

    @classmethod
    def from_file(cls, path: str) -> "GenrePack":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def from_registry(cls, name: str) -> Optional["GenrePack"]:
        """按名字从 data/genres/<name>.json 加载。找不到返回 None。"""
        if not name:
            return None
        path = os.path.join(config.GENRES_DIR, f"{name}.json")
        if not os.path.exists(path):
            return None
        return cls.from_file(path)

    @staticmethod
    def list_registry() -> List[str]:
        if not os.path.isdir(config.GENRES_DIR):
            return []
        return sorted(
            os.path.splitext(fn)[0]
            for fn in os.listdir(config.GENRES_DIR)
            if fn.endswith(".json") and not fn.startswith(".")
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # ------------------------------------------------------------------
    # 注入：拼出可追加到 system prompt 的题材规则块
    # ------------------------------------------------------------------
    def system_prompt_addon(self, *, role: str = "writer") -> str:
        """生成一段题材指引文本。可空（什么都没填时）。

        role: "writer" 或 "planner"，用于轻微调整措辞口气。
        """
        bits: List[str] = []
        header_who = "本作题材"
        if self.display_name:
            header_who = f"本作题材是【{self.display_name}】"
        elif self.name:
            header_who = f"本作题材是【{self.name}】"
        if self.one_liner:
            bits.append(f"{header_who} —— {self.one_liner}")
        else:
            bits.append(header_who)

        if self.style_guide:
            bits.append(f"【题材风格指引】{self.style_guide}")

        if self.allowed_elements:
            bits.append("【允许出现的元素】" + "、".join(self.allowed_elements))

        if self.forbidden_elements:
            bits.append("【题材禁忌（绝对不要出现）】" + "、".join(self.forbidden_elements))

        if self.banned_phrases:
            preview = "、".join(self.banned_phrases[:20])
            bits.append(
                f"【题材级禁词（任何章节正文里都不要使用，会被自动校验）】{preview}"
                + ("…" if len(self.banned_phrases) > 20 else "")
            )

        if role == "planner":
            bits.append(
                "（以上题材规则会被传给章节写手；规划 ChapterCard 时请确保 must_appear / "
                "foreshadow 等字段不与上述禁忌冲突）"
            )

        # 全空 → 返回空字符串，调用方拼接时不会留下空段
        if len(bits) == 1 and bits[0] == header_who:
            return ""
        return "\n".join(bits)

    # ------------------------------------------------------------------
    # bootstrap：把 spec_template 渲染成具体 spec（用于 run_init_novel）
    # ------------------------------------------------------------------
    def render_spec(
        self,
        title: str,
        protagonist_name: str,
        total_chapters: int = 50,
        extra_user_requirements: str = "",
    ) -> Dict[str, Any]:
        """把题材模板 + 用户填写信息合并成一份可直接喂给 OutlinePlanner.generate_blueprint
        的 spec dict。"""
        tmpl = self.spec_template or {}
        ur_tmpl = tmpl.get("user_requirements_template") or ""
        try:
            user_requirements = ur_tmpl.format(
                title=title,
                protagonist_name=protagonist_name,
                total_chapters=total_chapters,
            )
        except (KeyError, IndexError):
            # 模板占位符不全也别抛，原样返回
            user_requirements = ur_tmpl

        if extra_user_requirements:
            user_requirements = (user_requirements + "\n\n" + extra_user_requirements).strip()

        proto_skel = dict(tmpl.get("protagonist_skeleton") or {})
        basic = dict(proto_skel.get("basic_info") or {})
        basic["name"] = protagonist_name
        proto_skel["basic_info"] = basic

        supporting = list(tmpl.get("supporting_skeletons") or [])

        world_setting = dict(self.default_world_setting or {})
        world_setting.update(dict(tmpl.get("world_setting_extras") or {}))

        return {
            "title": title,
            "user_requirements": user_requirements,
            "total_chapters": total_chapters,
            "protagonist": proto_skel,
            "supporting_characters": supporting,
            "tags": dict(self.default_tags or {}),
            "world_setting": world_setting,
            "themes": list(self.default_themes or []),
            "_genre": self.name,
        }
