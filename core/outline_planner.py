"""
OutlinePlanner —— 整本小说大纲规划器（独立组件，零侵入现有系统）

设计原则
--------
1. 分层规划：先出"整本卷级蓝图"（粗），再为指定卷展开"章节卡"（细）
2. 强 Schema：所有产出都是结构化 JSON，下游可直接消费
3. 单一事实源前置：蓝图里就把"主角名 / 必现配角 / 名字白名单"钉死
4. 防模板循环：章节卡里要求 ending_hook 必须各异，并提供 banned_phrases 输入
5. 温度分层：规划层用低温（0.3），保证一致性

输出 Schema
-----------
BookBlueprint（整本骨架）
{
  "meta": {
    "title": str,
    "total_chapters": int,
    "volume_count": int,
    "protagonist_name": str,
    "name_whitelist": [str],         # 所有出现的命名实体（人/组织/地点）白名单
    "core_theme": str,
    "tone": str
  },
  "global_arc": {
    "act1_range": [int, int],
    "act2_range": [int, int],
    "act3_range": [int, int],
    "midpoint_chapter": int,
    "main_thread": str,              # 明线一句话
    "sub_thread": str                # 暗线一句话
  },
  "volumes": [
    {
      "index": int,
      "title": str,
      "chapter_range": [int, int],
      "phase": "opening" | "rising" | "midpoint" | "falling" | "climax" | "denouement",
      "goal": str,                   # 本卷必须完成什么
      "core_conflict": str,          # 本卷主冲突
      "key_milestones": [str],       # 卷内 3-5 个关键里程碑
      "foreshadow_plant_hints": [str],
      "foreshadow_payoff_hints": [str],
      "ending_state": str            # 卷末主角/局势处于什么状态
    }
  ],
  "global_foreshadow_ledger": [
    {"id": "F01", "content": str, "plant_volume": int, "payoff_volume": int, "importance": "low|mid|high"}
  ]
}

ChapterCard（单章节卡）
{
  "chapter_number": int,
  "volume": int,
  "role": "opening|rising|buffer|twist|climax|denouement",
  "title": str,
  "summary": str,                    # ≤40 字
  "beats": [str],                    # 3-5 个具体节拍
  "must_appear": {
    "characters": [str],             # 必须从 name_whitelist 中选
    "locations": [str],
    "objects": [str]
  },
  "foreshadow_plant": [str],         # 本章新埋的伏笔（建议引用 ledger.id）
  "foreshadow_payoff": [str],        # 本章回收的伏笔
  "ending_hook": str,                # 一句话钩子，必须与 banned_endings 中已用过的明显不同
  "tone": str,
  "tension_level": int               # 1-10
}
"""

from typing import Dict, List, Any, Optional
import json
import os
import re

from base_agent import BaseAgent
import config


class OutlinePlanner(BaseAgent):
    """整本小说大纲规划器"""

    DEFAULT_VOLUME_COUNT = 5
    PLANNER_TEMPERATURE = 0.3

    VALID_VOLUME_PHASES = {
        "opening", "rising", "midpoint", "falling", "climax", "denouement"
    }
    VALID_CHAPTER_ROLES = {
        "opening", "rising", "buffer", "twist", "climax", "denouement"
    }

    def __init__(self, genre_pack: Any = None):
        super().__init__("整本大纲规划器")
        self.temperature = self.PLANNER_TEMPERATURE
        # genre_pack: 可选 GenrePack 实例。为 None 时行为完全等价于原版（题材中立）。
        self.genre_pack = genre_pack

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """统一入口：根据 mode 决定生成蓝图或单卷章节卡

        input_data:
          mode: "blueprint" | "volume_cards"
          spec / blueprint / volume_index / banned_endings
          dkm / dkm_snapshot / dynamic_state_snapshot   # 三选一，可选
            - dkm: DynamicKnowledgeManager 实例（有则按 volume_index 自动生成 snapshot）
            - dkm_snapshot / dynamic_state_snapshot: 已生成的 snapshot dict
        """
        mode = input_data.get("mode", "blueprint")
        if mode == "blueprint":
            return self.generate_blueprint(input_data["spec"])
        if mode == "volume_cards":
            dkm = input_data.get("dkm")
            snapshot = (
                input_data.get("dkm_snapshot")
                or input_data.get("dynamic_state_snapshot")
            )
            return self.generate_volume_chapter_cards(
                blueprint=input_data["blueprint"],
                volume_index=input_data["volume_index"],
                banned_endings=input_data.get("banned_endings", []),
                dkm=dkm,
                dkm_snapshot=snapshot,
            )
        return {"error": f"未知 mode: {mode}"}

    # ------------------------------------------------------------------
    # Stage A: 整本卷级蓝图
    # ------------------------------------------------------------------
    def generate_blueprint(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """生成整本小说的卷级蓝图（粗粒度）

        spec 必含字段：
          title, user_requirements, total_chapters,
          protagonist (dict with at least basic_info.name),
          supporting_characters (list of dict with basic_info.name)
        spec 可选字段：
          tags, world_setting, themes, volume_count
        """
        validation = self.validate_input(spec, ["title", "user_requirements", "total_chapters", "protagonist"])
        if not validation["is_valid"]:
            return {"error": validation["error"]}

        total_chapters = int(spec["total_chapters"])
        volume_count = int(spec.get("volume_count", self._suggest_volume_count(total_chapters)))
        protagonist_name = self._safe_get_name(spec["protagonist"])
        if not protagonist_name:
            return {"error": "spec.protagonist 缺少 basic_info.name"}

        supporting = spec.get("supporting_characters", []) or []
        supporting_names = [self._safe_get_name(c) for c in supporting if self._safe_get_name(c)]
        name_whitelist_seed = [protagonist_name] + supporting_names

        prompt = self._build_blueprint_prompt(
            spec=spec,
            total_chapters=total_chapters,
            volume_count=volume_count,
            protagonist_name=protagonist_name,
            supporting_names=supporting_names,
        )

        messages = [
            {"role": "system", "content": self._system_prompt_planner()},
            {"role": "user", "content": prompt},
        ]

        self.log(f"开始生成整本蓝图：title={spec['title']}, chapters={total_chapters}, volumes={volume_count}")
        response = self.call_llm(messages, temperature=self.PLANNER_TEMPERATURE, max_tokens=config.MAX_TOKENS)
        raw = self.parse_json_response(response)
        if raw.get("parse_error"):
            self.log(f"蓝图 JSON 解析失败：{raw.get('error')}，启动兜底骨架")
            return self._fallback_blueprint(spec, total_chapters, volume_count, protagonist_name, supporting_names)

        blueprint = self._normalize_blueprint(
            raw=raw,
            spec=spec,
            total_chapters=total_chapters,
            volume_count=volume_count,
            protagonist_name=protagonist_name,
            name_whitelist_seed=name_whitelist_seed,
        )
        # 把"为下游 prompt 预渲染好的人物档案/故事架构块"附加到 blueprint，
        # 让 generate_volume_chapter_cards 与 ChapterCardWriter 都能直接消费，
        # 不必每次重新读 characters.json / storyline.json。
        # 使用前缀 _source_briefs 表示"非 LLM 输出，是上游设定的派生缓存"。
        blueprint["_source_briefs"] = self._render_source_briefs(spec)
        self.log(f"蓝图生成完成：{len(blueprint['volumes'])} 卷, "
                 f"{len(blueprint['global_foreshadow_ledger'])} 条全局伏笔")
        return blueprint

    @classmethod
    def _render_source_briefs(cls, spec: Dict[str, Any]) -> Dict[str, Any]:
        """把 spec 中的人物档案/故事架构预渲染成可重用的字符串块，并保留原始结构以便按需精挑。

        - character_briefs_block_full：完整的人物档案块字符串（蓝图与卷规划阶段直接拼）
        - story_arc_block：故事架构块字符串
        - main_character / supporting_characters：保留原始 dict（不含敏感字段也不大）
          以便 ChapterCardWriter 按 must_appear.characters 精挑当前章涉及的角色再渲染。

        声明为 classmethod，便于外部调用方（如 run_chapter_demo 的兼容回填逻辑）
        在不实例化 OutlinePlanner 的情况下直接复用。
        """
        return {
            "character_briefs_block_full": cls._build_character_briefs_block(
                main_character=spec.get("protagonist"),
                supporting_characters=spec.get("supporting_characters"),
                title="人物档案（全书必须遵守）",
            ),
            "story_arc_block": cls._build_story_arc_block(spec.get("storyline_arc")),
            "main_character": spec.get("protagonist") or {},
            "supporting_characters": spec.get("supporting_characters") or [],
        }

    # ------------------------------------------------------------------
    # Stage B: 单卷的章节卡
    # ------------------------------------------------------------------
    def generate_volume_chapter_cards(
        self,
        blueprint: Dict[str, Any],
        volume_index: int,
        banned_endings: Optional[List[str]] = None,
        dkm: Any = None,
        dkm_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """为指定卷展开所有 ChapterCard

        banned_endings: 此前章节已经用过的 ending_hook 短语，要求新章节避免雷同
        dkm / dkm_snapshot: 提供动态状态后，会从中提取"必收伏笔"清单并强制 LLM 把它们
            分配到本卷某章的 foreshadow_payoff；若 LLM 没覆盖完，会单次重试。
        """
        banned_endings = banned_endings or []

        volumes = blueprint.get("volumes", [])
        target_volume = next((v for v in volumes if int(v.get("index", -1)) == volume_index), None)
        if not target_volume:
            return {"error": f"未找到 volume_index={volume_index}"}

        chapter_range = target_volume.get("chapter_range", [0, 0])
        start_ch, end_ch = int(chapter_range[0]), int(chapter_range[1])
        chapter_count = end_ch - start_ch + 1
        if chapter_count <= 0:
            return {"error": f"卷 {volume_index} 章节范围非法：{chapter_range}"}

        meta = blueprint.get("meta", {})
        protagonist_name = meta.get("protagonist_name", "")
        name_whitelist = meta.get("name_whitelist", [])

        # ---- 从 DKM 提取本卷"必收 / 建议埋设"伏笔清单 ----
        snapshot = dkm_snapshot
        if snapshot is None and dkm is not None:
            try:
                snapshot = dkm.snapshot_for_chapter(target_chapter=start_ch)
            except Exception as exc:
                self.log(f"[WARN] 从 DKM 取 snapshot 失败：{exc}，本次跳过 DKM 注入")
                snapshot = None

        debt_payload = self._extract_volume_debt(
            snapshot=snapshot,
            blueprint=blueprint,
            target_volume_index=volume_index,
        )
        must_payoff_ids = [d["id"] for d in debt_payload["must_payoff"]]
        if must_payoff_ids:
            self.log(
                f"[DKM→Planner] 卷 {volume_index} 必收伏笔 {len(must_payoff_ids)} 条："
                f"{must_payoff_ids}（含逾期 {len(debt_payload['overdue'])} 条 / "
                f"按蓝图本卷应收 {len(debt_payload['scheduled_payoff'])} 条）"
            )
        if debt_payload["due_to_plant"]:
            self.log(
                f"[DKM→Planner] 卷 {volume_index} 建议埋设伏笔 {len(debt_payload['due_to_plant'])} 条："
                f"{[d['id'] for d in debt_payload['due_to_plant']]}"
            )

        prompt = self._build_volume_cards_prompt(
            blueprint=blueprint,
            target_volume=target_volume,
            start_ch=start_ch,
            end_ch=end_ch,
            protagonist_name=protagonist_name,
            name_whitelist=name_whitelist,
            banned_endings=banned_endings,
            debt_payload=debt_payload,
        )

        messages = [
            {"role": "system", "content": self._system_prompt_planner()},
            {"role": "user", "content": prompt},
        ]

        self.log(f"开始生成卷 {volume_index} 章节卡：第 {start_ch}-{end_ch} 章 共 {chapter_count} 章")
        response = self.call_llm(messages, temperature=self.PLANNER_TEMPERATURE, max_tokens=config.MAX_TOKENS)
        raw = self.parse_json_response(response)
        if raw.get("parse_error"):
            self.log(f"卷 {volume_index} 章节卡 JSON 解析失败：{raw.get('error')}，启动兜底")
            return self._fallback_volume_cards(target_volume, protagonist_name)

        cards_payload = self._normalize_volume_cards(
            raw=raw,
            target_volume=target_volume,
            protagonist_name=protagonist_name,
            name_whitelist=name_whitelist,
            start_ch=start_ch,
            end_ch=end_ch,
        )

        # ---- 必收伏笔覆盖硬校验 + 单次 retry ----
        coverage = self._check_payoff_coverage(cards_payload["chapter_cards"], must_payoff_ids)
        cards_payload["debt_coverage"] = coverage
        if coverage["uncovered"]:
            self.log(
                f"[DKM→Planner] 卷 {volume_index} 必收伏笔未覆盖：{coverage['uncovered']}，启动单次重试"
            )
            retry_prompt = self._build_volume_cards_prompt(
                blueprint=blueprint,
                target_volume=target_volume,
                start_ch=start_ch,
                end_ch=end_ch,
                protagonist_name=protagonist_name,
                name_whitelist=name_whitelist,
                banned_endings=banned_endings,
                debt_payload=debt_payload,
                retry_uncovered=coverage["uncovered"],
            )
            retry_messages = [
                {"role": "system", "content": self._system_prompt_planner()},
                {"role": "user", "content": retry_prompt},
            ]
            retry_resp = self.call_llm(
                retry_messages,
                temperature=self.PLANNER_TEMPERATURE,
                max_tokens=config.MAX_TOKENS,
            )
            retry_raw = self.parse_json_response(retry_resp)
            if not retry_raw.get("parse_error"):
                retry_payload = self._normalize_volume_cards(
                    raw=retry_raw,
                    target_volume=target_volume,
                    protagonist_name=protagonist_name,
                    name_whitelist=name_whitelist,
                    start_ch=start_ch,
                    end_ch=end_ch,
                )
                retry_coverage = self._check_payoff_coverage(
                    retry_payload["chapter_cards"], must_payoff_ids
                )
                if len(retry_coverage["uncovered"]) < len(coverage["uncovered"]):
                    self.log(
                        f"[DKM→Planner] 重试后未覆盖减少 "
                        f"{len(coverage['uncovered'])} → {len(retry_coverage['uncovered'])}，采用重试结果"
                    )
                    cards_payload = retry_payload
                    cards_payload["debt_coverage"] = retry_coverage
                else:
                    self.log("[DKM→Planner] 重试未带来改善，保留首次结果")
            cards_payload["debt_coverage"]["retried"] = True

        self.log(
            f"卷 {volume_index} 章节卡生成完成：{len(cards_payload['chapter_cards'])} 张"
            f"（必收伏笔覆盖 {cards_payload['debt_coverage']['covered_count']}/"
            f"{cards_payload['debt_coverage']['must_count']}）"
        )
        return cards_payload

    # ------------------------------------------------------------------
    # Prompt 构建
    # ------------------------------------------------------------------
    def _system_prompt_planner(self) -> str:
        base = (
            "你是一位资深的长篇小说总策划，擅长把高浓度的设定与需求拆成有节奏、可执行的卷级蓝图与章节卡。\n"
            "你的输出必须是【严格的、可被 json.loads 直接解析的 JSON】，不要包含 Markdown 代码块、注释、解释、省略号。\n"
            "你的硬性原则：\n"
            "1. 主角名、配角名必须严格使用用户提供的名字，不得自创、不得改写、不得别名化；\n"
            "2. 任何人物、地点、组织名第一次出现都必须加入 name_whitelist；\n"
            "3. 卷与卷之间必须有清晰的目标递进，不允许出现两卷主题雷同；\n"
            "4. 全局伏笔必须有埋设卷与回收卷，回收卷必须晚于埋设卷；\n"
            "5. 章节钩子（ending_hook）必须各不相同，避免任何'X已开启 / 时钟敲响第N声'之类的模板复读；\n"
            "6. 字段缺失要写空数组或空字符串，绝不可省略字段或写注释。"
        )
        addon = ""
        if self.genre_pack is not None:
            try:
                addon = self.genre_pack.system_prompt_addon(role="planner") or ""
            except Exception:
                addon = ""
        if addon:
            return base + "\n\n=== 题材规则（来自 GenrePack） ===\n" + addon
        return base

    def _build_blueprint_prompt(
        self,
        spec: Dict[str, Any],
        total_chapters: int,
        volume_count: int,
        protagonist_name: str,
        supporting_names: List[str],
    ) -> str:
        tags_text = json.dumps(spec.get("tags", {}), ensure_ascii=False)
        themes_text = json.dumps(spec.get("themes", []), ensure_ascii=False)
        world_text = json.dumps(spec.get("world_setting", {}), ensure_ascii=False)

        # 通用注入：完整人物档案（不仅是姓名串）
        character_briefs_block = self._build_character_briefs_block(
            main_character=spec.get("protagonist"),
            supporting_characters=spec.get("supporting_characters"),
            title="人物档案（蓝图阶段必须遵守）",
        )
        # 通用注入：故事架构骨架（act1/2/3 + 中点 + 高潮 + 主题）
        story_arc_block = self._build_story_arc_block(spec.get("storyline_arc"))

        chapter_ranges_hint = self._build_default_volume_ranges(total_chapters, volume_count)
        phase_suggestion = self._suggest_volume_phases(volume_count)
        min_high_span = max(2, volume_count // 3)

        # 区块组装时优雅降级——任意区块为空时不出现孤零零的标题
        optional_blocks = "\n\n".join(
            block for block in (character_briefs_block, story_arc_block) if block
        )
        optional_blocks_section = ("\n\n" + optional_blocks) if optional_blocks else ""

        return f"""请基于以下设定，规划一本【共 {total_chapters} 章 / 共 {volume_count} 卷】的长篇小说"整本蓝图"。

=== 基本信息 ===
小说标题：{spec['title']}
主角姓名（必须使用，不得改名）：{protagonist_name}
配角姓名（必须使用，不得改名）：{json.dumps(supporting_names, ensure_ascii=False)}

=== 用户原始需求（重要） ===
{spec['user_requirements']}

=== 标签 ===
{tags_text}

=== 主题 ===
{themes_text}

=== 世界观骨架（如已存在，必须沿用） ===
{world_text}{optional_blocks_section}

=== 卷划分参考（不必完全一致，但卷数固定为 {volume_count}） ===
{json.dumps(chapter_ranges_hint, ensure_ascii=False)}

=== phase 字段术语规范（务必准确选用） ===
phase 不是模糊形容词，是叙事位置。它的语义如下：
- opening    : 开局，建立角色、世界、主冲突；通常只用于第 1 卷
- rising     : 上升，冲突逐步加剧，铺设主要伏笔
- midpoint   : 中点反转/重大真相揭露；通常只用于全书中段一卷
- falling    : ⚠️ 这是"高潮之后的下行"，仅在 climax 之后才允许使用
- climax     : 全书最高潮，主线冲突的总决战
- denouement : 结局收尾，回收剩余伏笔，给出最终状态

【强约束】请尽量按下表选 phase（也允许微调，但禁止把"climax"写成"falling"）：
{json.dumps(phase_suggestion, ensure_ascii=False)}

=== 全局伏笔账本（global_foreshadow_ledger）规范 ===
1. 至少 5 条，至多 12 条；payoff_volume 必须严格大于 plant_volume；
2. 所有 importance="high" 的伏笔，跨度必须满足：payoff_volume - plant_volume >= {min_high_span}；
3. 至少 1 条 high 伏笔横跨从第 1 卷到末卷或临末卷（用于撑起主线）；
4. 任何在 volumes[].foreshadow_plant_hints / foreshadow_payoff_hints 中提及的伏笔关键词，
   必须有对应的一条 ledger 条目（可以同名或语义可识别），不得只写在卷里却不入账；
5. ledger 的 content 必须是具体物件/事件/线索，不要写"主角的成长"这种空话。

=== 输出要求（严格 JSON） ===
请严格按以下 JSON Schema 输出：

{{
  "meta": {{
    "title": "{spec['title']}",
    "total_chapters": {total_chapters},
    "volume_count": {volume_count},
    "protagonist_name": "{protagonist_name}",
    "name_whitelist": ["{protagonist_name}", ...所有会出现的人/组织/关键地点名],
    "core_theme": "一句话主题",
    "tone": "整体基调描述"
  }},
  "global_arc": {{
    "act1_range": [1, ?],
    "act2_range": [?, ?],
    "act3_range": [?, {total_chapters}],
    "midpoint_chapter": ?,
    "main_thread": "明线一句话",
    "sub_thread": "暗线一句话"
  }},
  "volumes": [
    {{
      "index": 1,
      "title": "卷一标题",
      "chapter_range": [起始章, 结束章],
      "phase": "opening | rising | midpoint | falling | climax | denouement 之一（按上面术语规范）",
      "goal": "本卷必须完成的目标（具体、可验证）",
      "core_conflict": "本卷主冲突",
      "key_milestones": ["卷内 3-5 个关键里程碑（含大致章号）"],
      "foreshadow_plant_hints": ["本卷适合埋设的伏笔关键词（必须能在 ledger 中找到对应项）"],
      "foreshadow_payoff_hints": ["本卷需要回收的早期伏笔关键词（同上）"],
      "ending_state": "卷末主角与局势的状态"
    }}
    // ... 共 {volume_count} 个卷
  ],
  "global_foreshadow_ledger": [
    {{"id": "F01", "content": "伏笔内容", "plant_volume": 1, "payoff_volume": 4, "importance": "high"}}
    // 至少 5 条，至多 12 条；high 跨度 >= {min_high_span}；payoff_volume > plant_volume
  ]
}}

请只输出该 JSON，不要任何其它文字。"""

    def _build_volume_cards_prompt(
        self,
        blueprint: Dict[str, Any],
        target_volume: Dict[str, Any],
        start_ch: int,
        end_ch: int,
        protagonist_name: str,
        name_whitelist: List[str],
        banned_endings: List[str],
        debt_payload: Optional[Dict[str, Any]] = None,
        retry_uncovered: Optional[List[str]] = None,
    ) -> str:
        chapter_count = end_ch - start_ch + 1
        ledger = blueprint.get("global_foreshadow_ledger", [])
        role_suggestion = self._suggest_chapter_roles(start_ch, end_ch)
        debt_block = self._build_debt_prompt_block(debt_payload, retry_uncovered)

        # 来自 _render_source_briefs 的派生缓存——若不存在（旧蓝图）则降级为空串
        source_briefs = blueprint.get("_source_briefs") or {}
        character_briefs_block = source_briefs.get("character_briefs_block_full") or ""
        story_arc_block = source_briefs.get("story_arc_block") or ""
        # 同样优雅降级：任意区块为空时不出现孤标题
        optional_blocks = "\n\n".join(
            block for block in (character_briefs_block, story_arc_block) if block
        )
        optional_blocks_section = ("\n\n" + optional_blocks) if optional_blocks else ""

        return f"""请基于以下卷级目标，为本卷展开【共 {chapter_count} 章】的章节卡（ChapterCard）。
{debt_block}

=== 整本元信息 ===
{json.dumps(blueprint.get('meta', {}), ensure_ascii=False)}

=== 整本节奏弧 ===
{json.dumps(blueprint.get('global_arc', {}), ensure_ascii=False)}

=== 当前卷信息 ===
{json.dumps(target_volume, ensure_ascii=False)}{optional_blocks_section}

=== 全局伏笔账本（请用 id 引用） ===
{json.dumps(ledger, ensure_ascii=False)}

=== 命名白名单（任何人物/组织/地点必须从中选取或先加入） ===
{json.dumps(name_whitelist, ensure_ascii=False)}

=== 已经用过的章节钩子（严禁雷同！必须明显不同） ===
{json.dumps(banned_endings, ensure_ascii=False)}

=== role 字段术语规范（务必准确选用，错用会被自动纠正并打警告） ===
role 是"本章在本卷里承担的叙事位置"，不是模糊形容词。语义如下：
- opening    : 卷的开场章。建立场景/抛出本卷主冲突。仅允许出现在卷的前 25% 章节。
- rising     : 上升。冲突加剧、调查推进、人物关系升温。卷中段为主，可多次使用。
- buffer     : 缓冲/转场/铺垫。节奏放缓、整理线索、人物喘息。任何位置可少量使用。
- twist      : 反转/重大新发现，打破读者预期。每卷建议 1-2 章。
- climax     : 本卷最高对抗点。⚠️ 仅允许出现在卷的后 50% 章节，且全卷不超过 1-2 次。
- denouement : 本卷收尾，给阶段性结局或悬念结尾。⚠️ 仅允许出现在卷的最后 1-2 章。

【强约束】
- climax 之后的章节，role 不允许是 opening / rising（应为 buffer / twist / climax / denouement）；
- denouement 一旦出现，后面的章节也只能是 denouement；
- 整卷至少出现 1 个 climax 或 twist，否则节奏必然平庸。

=== role 推荐序列（请尽量贴近，可微调） ===
{json.dumps(role_suggestion, ensure_ascii=False)}

=== 写作硬约束 ===
1. 章节号必须从 {start_ch} 到 {end_ch}，连续、不重复、不缺失；
2. 主角"{protagonist_name}"必须出现在本卷绝大多数章节的 must_appear.characters 中；
3. role 字段值只能是：opening / rising / buffer / twist / climax / denouement，且必须遵循上面的【强约束】；
4. ending_hook 不允许沿用任何 banned_endings 中的句式或意象；
5. 每章 beats 必须 3-5 条，是具体动作或事件，不能写"主角思考""主角行动"这种空话；
6. 全卷至少埋设 1 条新伏笔且至少回收 1 条已有伏笔（如果卷级目标允许）；
7. tension_level 在 1-10，整卷需有节奏起伏，不能全 8 或全 5。

=== 输出 JSON Schema ===
{{
  "volume_index": {target_volume.get('index')},
  "chapter_cards": [
    {{
      "chapter_number": {start_ch},
      "volume": {target_volume.get('index')},
      "role": "opening",
      "title": "章节标题",
      "summary": "≤40 字一句话",
      "beats": ["节拍1", "节拍2", "节拍3"],
      "must_appear": {{
        "characters": ["{protagonist_name}", ...],
        "locations": ["..."],
        "objects": ["..."]
      }},
      "foreshadow_plant": ["F0X 或自由描述"],
      "foreshadow_payoff": [],
      "ending_hook": "一句话钩子，避免与 banned_endings 雷同",
      "tone": "冷峻 / 紧张 / 压抑 / 沉默 / 等",
      "tension_level": 7
    }}
    // ... 共 {chapter_count} 张
  ]
}}

请只输出该 JSON，不要任何其它文字。"""

    # ------------------------------------------------------------------
    # 蓝图归一化与兜底
    # ------------------------------------------------------------------
    def _normalize_blueprint(
        self,
        raw: Dict[str, Any],
        spec: Dict[str, Any],
        total_chapters: int,
        volume_count: int,
        protagonist_name: str,
        name_whitelist_seed: List[str],
    ) -> Dict[str, Any]:
        meta = raw.get("meta", {}) or {}
        meta.setdefault("title", spec["title"])
        meta["total_chapters"] = total_chapters
        meta["volume_count"] = volume_count
        meta["protagonist_name"] = protagonist_name

        whitelist = list(meta.get("name_whitelist") or [])
        for name in name_whitelist_seed:
            if name and name not in whitelist:
                whitelist.append(name)
        meta["name_whitelist"] = whitelist
        meta.setdefault("core_theme", "")
        meta.setdefault("tone", "")

        global_arc = raw.get("global_arc", {}) or {}
        global_arc.setdefault("act1_range", [1, max(1, total_chapters // 4)])
        global_arc.setdefault("act2_range", [max(1, total_chapters // 4) + 1, max(2, total_chapters * 3 // 4)])
        global_arc.setdefault("act3_range", [max(2, total_chapters * 3 // 4) + 1, total_chapters])
        global_arc.setdefault("midpoint_chapter", total_chapters // 2)
        global_arc.setdefault("main_thread", "")
        global_arc.setdefault("sub_thread", "")

        volumes = raw.get("volumes", []) or []
        volumes = self._fix_volume_ranges(volumes, total_chapters, volume_count)
        suggested_phases = self._suggest_volume_phases(volume_count)
        for idx, vol in enumerate(volumes, start=1):
            vol.setdefault("index", idx)
            vol.setdefault("title", f"卷{idx}")
            phase = vol.get("phase", "")
            if phase not in self.VALID_VOLUME_PHASES:
                vol["phase"] = self._infer_phase_by_index(idx, volume_count)
            else:
                suggested = suggested_phases[idx - 1]["phase"]
                if self._is_phase_severely_off(phase, suggested, idx, volume_count):
                    self.log(
                        f"⚠️ 卷{idx} phase='{phase}' 与位置严重不符（建议 '{suggested}'），已纠正"
                    )
                    vol["phase"] = suggested
            vol.setdefault("goal", "")
            vol.setdefault("core_conflict", "")
            vol.setdefault("key_milestones", [])
            vol.setdefault("foreshadow_plant_hints", [])
            vol.setdefault("foreshadow_payoff_hints", [])
            vol.setdefault("ending_state", "")

        ledger = raw.get("global_foreshadow_ledger", []) or []
        cleaned_ledger = []
        for i, item in enumerate(ledger, start=1):
            if not isinstance(item, dict):
                continue
            plant_v = self._safe_int(item.get("plant_volume"), default=1)
            payoff_v = self._safe_int(item.get("payoff_volume"), default=plant_v + 1)
            if payoff_v <= plant_v:
                payoff_v = min(volume_count, plant_v + 1)
            cleaned_ledger.append({
                "id": item.get("id") or f"F{i:02d}",
                "content": item.get("content", ""),
                "plant_volume": plant_v,
                "payoff_volume": payoff_v,
                "importance": item.get("importance", "mid"),
            })

        cleaned_ledger = self._merge_hints_into_ledger(volumes, cleaned_ledger, volume_count)
        self._warn_foreshadow_span(cleaned_ledger, volume_count)

        return {
            "meta": meta,
            "global_arc": global_arc,
            "volumes": volumes,
            "global_foreshadow_ledger": cleaned_ledger,
        }

    def _fix_volume_ranges(
        self, volumes: List[Dict[str, Any]], total_chapters: int, volume_count: int
    ) -> List[Dict[str, Any]]:
        if not volumes:
            return self._build_default_volume_ranges(total_chapters, volume_count)

        if len(volumes) != volume_count:
            self.log(f"⚠️ LLM 给出的卷数={len(volumes)} 与目标={volume_count} 不一致，按目标卷数兜底重排")
            base = self._build_default_volume_ranges(total_chapters, volume_count)
            for i, default_vol in enumerate(base):
                if i < len(volumes):
                    src = volumes[i]
                    src["index"] = default_vol["index"]
                    src["chapter_range"] = default_vol["chapter_range"]
                    base[i] = src
            return base

        ranges = self._build_default_volume_ranges(total_chapters, volume_count)
        for i, vol in enumerate(volumes):
            cr = vol.get("chapter_range")
            if not (isinstance(cr, list) and len(cr) == 2 and all(isinstance(x, int) for x in cr)):
                vol["chapter_range"] = ranges[i]["chapter_range"]
            vol["index"] = i + 1
        return volumes

    @staticmethod
    def _build_default_volume_ranges(total_chapters: int, volume_count: int) -> List[Dict[str, Any]]:
        per = total_chapters // volume_count
        remainder = total_chapters - per * volume_count
        ranges = []
        cursor = 1
        for i in range(volume_count):
            length = per + (1 if i < remainder else 0)
            start = cursor
            end = cursor + length - 1
            ranges.append({"index": i + 1, "chapter_range": [start, end]})
            cursor = end + 1
        return ranges

    @staticmethod
    def _suggest_volume_count(total_chapters: int) -> int:
        if total_chapters <= 30:
            return 3
        if total_chapters <= 80:
            return 5
        if total_chapters <= 200:
            return 8
        return max(10, total_chapters // 50)

    @staticmethod
    def _infer_phase_by_index(idx: int, volume_count: int) -> str:
        ratio = idx / max(1, volume_count)
        if ratio <= 0.2:
            return "opening"
        if ratio <= 0.5:
            return "rising"
        if ratio <= 0.6:
            return "midpoint"
        if ratio <= 0.85:
            return "climax"
        return "denouement"

    @classmethod
    def _suggest_volume_phases(cls, volume_count: int) -> List[Dict[str, Any]]:
        """给出"卷号 → 推荐 phase"的建议表，prompt 与归一化共用一个事实源。"""
        suggestion = []
        for idx in range(1, volume_count + 1):
            suggestion.append({
                "volume_index": idx,
                "phase": cls._infer_phase_by_index(idx, volume_count),
            })
        return suggestion

    PHASE_ORDER = ["opening", "rising", "midpoint", "climax", "falling", "denouement"]

    @classmethod
    def _is_phase_severely_off(cls, given: str, suggested: str, idx: int, volume_count: int) -> bool:
        """判断 LLM 给的 phase 与建议是否"严重不符"。

        放宽规则：相邻一档（如 rising vs midpoint）允许；但下列情况一律纠正：
        - 倒数第 1-2 卷给了 opening / rising
        - climax 之前的卷给了 falling / denouement
        - 中段给 denouement
        """
        if given == suggested:
            return False
        # 末两卷不应回退到开头/上升
        if idx >= volume_count - 1 and given in {"opening", "rising"}:
            return True
        # falling 是"climax 之后的下行"；只要建议表不在该位置推荐 falling，
        # LLM 写 falling 都按误用处理（多见的真实错误：把 climax 错标成 falling）
        if given == "falling" and suggested != "falling":
            return True
        # 非末卷出现 denouement
        if given == "denouement" and idx < volume_count:
            return True
        # opening 只允许第 1 卷
        if given == "opening" and idx != 1:
            return True
        # midpoint 不应在前 1/3 或后 1/3 出现
        if given == "midpoint" and (idx <= max(1, volume_count // 3) or idx > volume_count - max(1, volume_count // 3)):
            return True
        return False

    def _merge_hints_into_ledger(
        self,
        volumes: List[Dict[str, Any]],
        ledger: List[Dict[str, Any]],
        volume_count: int,
    ) -> List[Dict[str, Any]]:
        """扫描 volumes[].foreshadow_plant_hints / payoff_hints，确保每条都有 ledger 记录。

        匹配策略：先精确匹配 content，再做包含匹配；都不命中就自动补一条 mid 优先级、跨 2 卷的 ledger。
        """
        existing_contents = [(item.get("content") or "").strip() for item in ledger]

        def hint_in_ledger(hint: str) -> bool:
            h = hint.strip()
            if not h:
                return True
            for c in existing_contents:
                if not c:
                    continue
                if h == c or h in c or c in h:
                    return True
            return False

        next_id_num = max(
            [self._safe_int(re.sub(r"\D", "", item.get("id", "F00")), default=0) for item in ledger] or [0]
        ) + 1

        added = 0
        for vol in volumes:
            v_idx = int(vol.get("index", 1))
            for hint in (vol.get("foreshadow_plant_hints") or []):
                if not isinstance(hint, str) or not hint.strip():
                    continue
                if hint_in_ledger(hint):
                    continue
                payoff_v = min(volume_count, v_idx + 2)
                if payoff_v <= v_idx:
                    payoff_v = min(volume_count, v_idx + 1)
                if payoff_v <= v_idx:
                    continue
                new_item = {
                    "id": f"F{next_id_num:02d}",
                    "content": hint.strip(),
                    "plant_volume": v_idx,
                    "payoff_volume": payoff_v,
                    "importance": "mid",
                    "_auto_merged": True,
                }
                ledger.append(new_item)
                existing_contents.append(new_item["content"])
                next_id_num += 1
                added += 1

            for hint in (vol.get("foreshadow_payoff_hints") or []):
                if not isinstance(hint, str) or not hint.strip():
                    continue
                if hint_in_ledger(hint):
                    continue
                plant_v = max(1, v_idx - 2)
                if plant_v >= v_idx:
                    continue
                new_item = {
                    "id": f"F{next_id_num:02d}",
                    "content": hint.strip(),
                    "plant_volume": plant_v,
                    "payoff_volume": v_idx,
                    "importance": "mid",
                    "_auto_merged": True,
                }
                ledger.append(new_item)
                existing_contents.append(new_item["content"])
                next_id_num += 1
                added += 1

        if added:
            self.log(f"🔧 ledger 自动补齐 {added} 条（来自 volume hints 的孤儿伏笔）")
        return ledger

    def _warn_foreshadow_span(self, ledger: List[Dict[str, Any]], volume_count: int) -> None:
        """对 high 优先级伏笔跨度过短的，仅 warn 不强改。"""
        min_high_span = max(2, volume_count // 3)
        for item in ledger:
            if item.get("importance") == "high":
                span = self._safe_int(item.get("payoff_volume"), 0) - self._safe_int(item.get("plant_volume"), 0)
                if span < min_high_span:
                    self.log(
                        f"⚠️ 伏笔 {item.get('id')}({item.get('content')[:20]}...) 标为 high "
                        f"但跨度仅 {span} 卷，建议 ≥ {min_high_span}"
                    )

    def _fallback_blueprint(
        self,
        spec: Dict[str, Any],
        total_chapters: int,
        volume_count: int,
        protagonist_name: str,
        supporting_names: List[str],
    ) -> Dict[str, Any]:
        ranges = self._build_default_volume_ranges(total_chapters, volume_count)
        volumes = []
        for r in ranges:
            phase = self._infer_phase_by_index(r["index"], volume_count)
            volumes.append({
                "index": r["index"],
                "title": f"第{r['index']}卷（待规划）",
                "chapter_range": r["chapter_range"],
                "phase": phase,
                "goal": "",
                "core_conflict": "",
                "key_milestones": [],
                "foreshadow_plant_hints": [],
                "foreshadow_payoff_hints": [],
                "ending_state": "",
            })

        return {
            "meta": {
                "title": spec["title"],
                "total_chapters": total_chapters,
                "volume_count": volume_count,
                "protagonist_name": protagonist_name,
                "name_whitelist": [protagonist_name] + supporting_names,
                "core_theme": "",
                "tone": "",
            },
            "global_arc": {
                "act1_range": [1, max(1, total_chapters // 4)],
                "act2_range": [max(1, total_chapters // 4) + 1, max(2, total_chapters * 3 // 4)],
                "act3_range": [max(2, total_chapters * 3 // 4) + 1, total_chapters],
                "midpoint_chapter": total_chapters // 2,
                "main_thread": "",
                "sub_thread": "",
            },
            "volumes": volumes,
            "global_foreshadow_ledger": [],
            "_fallback": True,
        }

    # ------------------------------------------------------------------
    # 章节卡归一化与兜底
    # ------------------------------------------------------------------
    def _normalize_volume_cards(
        self,
        raw: Dict[str, Any],
        target_volume: Dict[str, Any],
        protagonist_name: str,
        name_whitelist: List[str],
        start_ch: int,
        end_ch: int,
    ) -> Dict[str, Any]:
        cards = raw.get("chapter_cards", []) or []
        normalized = []
        seen_endings = []
        suggested_roles = {
            item["chapter_number"]: item["role"]
            for item in self._suggest_chapter_roles(start_ch, end_ch)
        }
        prior_roles: List[str] = []

        for offset, ch_num in enumerate(range(start_ch, end_ch + 1)):
            src = cards[offset] if offset < len(cards) else {}
            role = src.get("role", "")
            if role not in self.VALID_CHAPTER_ROLES:
                role = self._infer_chapter_role(ch_num, start_ch, end_ch)
            elif self._is_chapter_role_off(role, ch_num, start_ch, end_ch, prior_roles):
                fallback = suggested_roles.get(ch_num) or self._infer_chapter_role(
                    ch_num, start_ch, end_ch
                )
                # 若推荐值本身也违反前序约束（比如末段已 denouement），再退一档
                if "denouement" in prior_roles and fallback != "denouement":
                    fallback = "denouement"
                elif "climax" in prior_roles and fallback in {"opening", "rising"}:
                    fallback = "buffer"
                self.log(
                    f"⚠️ 第{ch_num}章 role='{role}' 与位置/前序不符（建议 '{fallback}'），已纠正"
                )
                role = fallback
            prior_roles.append(role)

            must_appear = src.get("must_appear", {}) or {}
            characters = must_appear.get("characters", []) or []
            if protagonist_name and protagonist_name not in characters:
                characters = [protagonist_name] + characters
            characters = [c for c in characters if c]

            illegal_names = [c for c in characters if name_whitelist and c not in name_whitelist]
            if illegal_names:
                self.log(f"⚠️ 第{ch_num}章出现白名单外人物：{illegal_names}，已剔除")
                characters = [c for c in characters if c in name_whitelist]
                if protagonist_name and protagonist_name not in characters:
                    characters = [protagonist_name] + characters

            ending = (src.get("ending_hook") or "").strip()
            if ending and ending in seen_endings:
                self.log(f"⚠️ 第{ch_num}章 ending_hook 与同卷前章重复，已标注")
                ending = ending + "（⚠️本卷内重复）"
            if ending:
                seen_endings.append(ending)

            tension = self._safe_int(src.get("tension_level"), default=5)
            tension = max(1, min(10, tension))

            normalized.append({
                "chapter_number": ch_num,
                "volume": int(target_volume.get("index", 0)),
                "role": role,
                "title": src.get("title") or f"第{ch_num}章",
                "summary": (src.get("summary") or "")[:80],
                "beats": [b for b in (src.get("beats") or []) if isinstance(b, str)][:6],
                "must_appear": {
                    "characters": characters,
                    "locations": [x for x in (must_appear.get("locations") or []) if isinstance(x, str)],
                    "objects": [x for x in (must_appear.get("objects") or []) if isinstance(x, str)],
                },
                "foreshadow_plant": [x for x in (src.get("foreshadow_plant") or []) if isinstance(x, str)],
                "foreshadow_payoff": [x for x in (src.get("foreshadow_payoff") or []) if isinstance(x, str)],
                "ending_hook": ending,
                "tone": src.get("tone") or "",
                "tension_level": tension,
            })

        return {
            "volume_index": target_volume.get("index"),
            "volume_title": target_volume.get("title"),
            "chapter_range": [start_ch, end_ch],
            "chapter_cards": normalized,
        }

    # ------------------------------------------------------------------
    # DKM 反向闭环：从 snapshot 提取本卷必收伏笔，并校验 LLM 是否安排到位
    # ------------------------------------------------------------------
    def _extract_volume_debt(
        self,
        snapshot: Optional[Dict[str, Any]],
        blueprint: Dict[str, Any],
        target_volume_index: int,
    ) -> Dict[str, Any]:
        """从 DKM snapshot 与 blueprint.ledger 提取本卷需要处理的伏笔债务。

        返回结构：
        {
          "must_payoff":      [{"id","content","importance","reason","plant_volume","payoff_volume","age_chapters"}],
          "overdue":          [...]   # must_payoff 的子集：已逾期
          "scheduled_payoff": [...]   # must_payoff 的子集：按蓝图本卷应收
          "due_to_plant":     [...]   # 建议本卷埋（按蓝图 plant_volume == target_volume）
          "still_open_context":[...]  # 仅作背景，不强制处理
        }
        """
        result = {
            "must_payoff": [],
            "overdue": [],
            "scheduled_payoff": [],
            "due_to_plant": [],
            "still_open_context": [],
        }
        if not snapshot:
            return result

        # 用 ledger 作为"内容/优先级"的回填源（snapshot 里也有，但有时 content 缺失）
        ledger_index: Dict[str, Dict[str, Any]] = {}
        for item in blueprint.get("global_foreshadow_ledger", []) or []:
            fid = item.get("id")
            if fid:
                ledger_index[fid] = item

        def _enrich(f: Dict[str, Any], reason: str) -> Dict[str, Any]:
            fid = f.get("id") or "?"
            base = ledger_index.get(fid, {})
            return {
                "id": fid,
                "content": (f.get("content") or base.get("content") or "").strip()
                           or "(未提供描述)",
                "importance": f.get("importance") or base.get("importance") or "mid",
                "plant_volume": f.get("plant_volume") or base.get("plant_volume"),
                "payoff_volume": f.get("payoff_volume") or base.get("payoff_volume"),
                "age_chapters": f.get("age_chapters"),
                "actually_planted_in_ch": f.get("actually_planted_in_ch"),
                "reason": reason,
            }

        seen_ids = set()

        # 1) 逾期伏笔 → 必收
        for f in snapshot.get("overdue_foreshadowings") or []:
            fid = f.get("id")
            if not fid or fid in seen_ids:
                continue
            item = _enrich(f, "overdue")
            result["overdue"].append(item)
            result["must_payoff"].append(item)
            seen_ids.add(fid)

        # 2) open/planted 中按蓝图本卷应回收的 → 必收
        for f in snapshot.get("open_foreshadowings") or []:
            fid = f.get("id")
            if not fid or fid in seen_ids:
                continue
            payoff_v = f.get("payoff_volume") or ledger_index.get(fid, {}).get("payoff_volume")
            plant_v = f.get("plant_volume") or ledger_index.get(fid, {}).get("plant_volume")
            try:
                payoff_v_int = int(payoff_v) if payoff_v is not None else None
                plant_v_int = int(plant_v) if plant_v is not None else None
            except (TypeError, ValueError):
                payoff_v_int, plant_v_int = None, None

            if payoff_v_int is not None and payoff_v_int <= target_volume_index:
                # 包含两类必收：
                #   a) payoff_volume == 本卷（蓝图原计划本卷收）
                #   b) payoff_volume < 本卷（蓝图原本应在更早卷收，但实际未回收 → 越早卷的债越要立刻还）
                reason = (
                    "scheduled_payoff_this_volume"
                    if payoff_v_int == target_volume_index
                    else "missed_payoff_from_earlier_volume"
                )
                item = _enrich(f, reason)
                result["scheduled_payoff"].append(item)
                result["must_payoff"].append(item)
                seen_ids.add(fid)
                continue

            if plant_v_int == target_volume_index and not f.get("actually_planted_in_ch"):
                # 本卷应埋且尚未埋下 → 提示 LLM 安排到 plant
                result["due_to_plant"].append(_enrich(f, "scheduled_plant_this_volume"))
                continue

            # 其它仍 open 的伏笔：仅作上下文，避免 LLM 与之矛盾或重复埋
            if len(result["still_open_context"]) < 6:
                result["still_open_context"].append(_enrich(f, "open_context"))

        return result

    @staticmethod
    def _build_debt_prompt_block(
        debt_payload: Optional[Dict[str, Any]],
        retry_uncovered: Optional[List[str]] = None,
    ) -> str:
        if not debt_payload:
            return ""
        must = debt_payload.get("must_payoff") or []
        plant = debt_payload.get("due_to_plant") or []
        ctx = debt_payload.get("still_open_context") or []

        if not (must or plant or ctx or retry_uncovered):
            return ""

        def _fmt(item: Dict[str, Any]) -> str:
            tag = ""
            if item.get("reason") == "overdue":
                age = item.get("age_chapters")
                tag = f"（已逾期，搁置 {age} 章）" if age is not None else "（已逾期）"
            elif item.get("reason") == "scheduled_payoff_this_volume":
                tag = f"（蓝图安排本卷回收，plant=vol{item.get('plant_volume')}）"
            elif item.get("reason") == "missed_payoff_from_earlier_volume":
                tag = (
                    f"（蓝图原计划在 vol{item.get('payoff_volume')} 收，但已错过未收，"
                    f"必须在本卷补收）"
                )
            elif item.get("reason") == "scheduled_plant_this_volume":
                tag = f"（蓝图安排本卷埋设，payoff=vol{item.get('payoff_volume')}）"
            return f"  - {item['id']} [{item.get('importance','?')}] {item['content']}{tag}"

        lines: List[str] = ["", "=== 来自动态状态（DKM）的本卷伏笔债务（强约束） ==="]

        if must:
            lines.append(
                "\n【本卷必须回收（请把这些 id 分别写进具体章节的 foreshadow_payoff 字段）】："
            )
            for item in must:
                lines.append(_fmt(item))
            lines.append(
                "  注意：上列伏笔已经在更早卷被埋下，本卷不要再写进任何章节的 foreshadow_plant；"
                "回收时请确保对应章节的 beats / ending_hook 真的兑现该伏笔，不要只在 payoff 字段挂个 id。"
            )

        if plant:
            lines.append(
                "\n【本卷建议新埋（蓝图把它们的 plant_volume 标在本卷，但目前还没埋下）】："
            )
            for item in plant:
                lines.append(_fmt(item))
            lines.append(
                "  请把这些 id 分散写进合适章节的 foreshadow_plant；"
                "若某条与本卷主线冲突可保留不埋，但需在卷末状态里说明理由。"
            )

        if ctx:
            lines.append(
                "\n【背景：其它仍未回收的伏笔（本卷不强制处理，但写作时不要与其矛盾、不要重复埋设）】："
            )
            for item in ctx:
                lines.append(_fmt(item))

        if retry_uncovered:
            lines.append(
                "\n⚠️【重试提示】你上一次的章节卡草稿没有把以下必收伏笔分配到任何章的 foreshadow_payoff："
            )
            for fid in retry_uncovered:
                lines.append(f"  - {fid}")
            lines.append(
                "  本次请务必把上列每个 id 都至少出现在某章的 foreshadow_payoff 数组中，"
                "并让该章的 beats 真正兑现它。"
            )

        return "\n".join(lines)

    @staticmethod
    def _check_payoff_coverage(
        chapter_cards: List[Dict[str, Any]],
        must_payoff_ids: List[str],
    ) -> Dict[str, Any]:
        """检查必收伏笔 id 是否都出现在某章 foreshadow_payoff 中。

        匹配规则：精确包含（id 出现在任一章的 foreshadow_payoff 列表元素中作为子串即算覆盖，
        以容忍 LLM 偶尔写成 'F03 - 某事件' 这种格式）。
        """
        if not must_payoff_ids:
            return {
                "must_count": 0,
                "covered_count": 0,
                "covered": [],
                "uncovered": [],
                "by_chapter": {},
            }

        covered_set = set()
        by_chapter: Dict[int, List[str]] = {}
        for card in chapter_cards:
            ch = int(card.get("chapter_number", 0))
            payoff_list = card.get("foreshadow_payoff") or []
            hits: List[str] = []
            for entry in payoff_list:
                if not isinstance(entry, str):
                    continue
                for fid in must_payoff_ids:
                    if fid and fid in entry:
                        covered_set.add(fid)
                        hits.append(fid)
            if hits:
                by_chapter[ch] = sorted(set(hits))

        uncovered = [fid for fid in must_payoff_ids if fid not in covered_set]
        return {
            "must_count": len(must_payoff_ids),
            "covered_count": len(covered_set),
            "covered": sorted(covered_set),
            "uncovered": uncovered,
            "by_chapter": by_chapter,
        }

    def _fallback_volume_cards(self, target_volume: Dict[str, Any], protagonist_name: str) -> Dict[str, Any]:
        chapter_range = target_volume.get("chapter_range", [0, 0])
        start_ch, end_ch = int(chapter_range[0]), int(chapter_range[1])
        cards = []
        for ch_num in range(start_ch, end_ch + 1):
            cards.append({
                "chapter_number": ch_num,
                "volume": int(target_volume.get("index", 0)),
                "role": self._infer_chapter_role(ch_num, start_ch, end_ch),
                "title": f"第{ch_num}章（待规划）",
                "summary": "",
                "beats": [],
                "must_appear": {"characters": [protagonist_name] if protagonist_name else [],
                                "locations": [], "objects": []},
                "foreshadow_plant": [],
                "foreshadow_payoff": [],
                "ending_hook": "",
                "tone": "",
                "tension_level": 5,
            })
        return {
            "volume_index": target_volume.get("index"),
            "volume_title": target_volume.get("title"),
            "chapter_range": [start_ch, end_ch],
            "chapter_cards": cards,
            "_fallback": True,
        }

    @staticmethod
    def _infer_chapter_role(ch_num: int, start_ch: int, end_ch: int) -> str:
        length = max(1, end_ch - start_ch + 1)
        pos = (ch_num - start_ch) / length
        if pos == 0:
            return "opening"
        if pos >= 0.85:
            return "climax"
        if 0.4 <= pos < 0.55:
            return "twist"
        if pos >= 0.55:
            return "rising"
        return "buffer"

    @classmethod
    def _suggest_chapter_roles(cls, start_ch: int, end_ch: int) -> List[Dict[str, Any]]:
        """生成"章号 → 推荐 role"序列，prompt 与归一化共用一个事实源。

        典型 10 章卷会给出：opening / rising / rising / buffer / rising / twist /
        rising / rising / climax / denouement
        """
        chapter_count = end_ch - start_ch + 1
        if chapter_count <= 0:
            return []

        roles: List[str] = []
        for offset in range(chapter_count):
            ratio = (offset + 1) / chapter_count
            if ratio <= 0.15:
                roles.append("opening")
            elif ratio <= 0.40:
                roles.append("rising")
            elif ratio <= 0.50:
                roles.append("buffer")
            elif ratio <= 0.85:
                roles.append("rising")
            elif ratio <= 0.95:
                roles.append("climax")
            else:
                roles.append("denouement")

        # 在中段塞 1 个 twist，避免推荐序列里只有 rising
        mid_idx = chapter_count // 2
        for shift in (0, -1, 1, -2, 2):
            idx = mid_idx + shift
            if 0 <= idx < chapter_count and roles[idx] == "rising":
                roles[idx] = "twist"
                break

        # 兜底：极短卷
        if chapter_count == 1:
            roles = ["climax"]
        elif chapter_count == 2:
            roles = ["rising", "climax"]

        return [
            {"chapter_number": start_ch + i, "role": roles[i]}
            for i in range(chapter_count)
        ]

    @classmethod
    def _is_chapter_role_off(
        cls,
        role: str,
        ch_num: int,
        start_ch: int,
        end_ch: int,
        prior_roles: List[str],
    ) -> bool:
        """判断本章 role 是否与位置/前序严重不符（仅纠正硬错位，不挑剔风格差异）。

        prior_roles: 本卷此章之前已确定（含可能已被纠正过）的 role 序列。
        """
        length = max(1, end_ch - start_ch + 1)
        pos = (ch_num - start_ch + 1) / length

        if role == "opening" and pos > 0.30:
            return True
        if role == "denouement" and pos < 0.80:
            return True
        if role == "climax" and pos < 0.50:
            return True
        if "climax" in prior_roles and role in {"opening", "rising"}:
            return True
        if "denouement" in prior_roles and role != "denouement":
            return True
        return False

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_get_name(character: Any) -> str:
        if not isinstance(character, dict):
            return ""
        basic = character.get("basic_info") or {}
        return (basic.get("name") or character.get("name") or "").strip()

    # ------------------------------------------------------------------
    # 通用人物档案精炼器（数据驱动，不依赖任何具体角色名/身份）
    # ------------------------------------------------------------------
    @staticmethod
    def _truncate(text: Any, limit: int) -> str:
        """安全截断任意值为字符串，并控制长度，避免 prompt 膨胀。"""
        if text is None:
            return ""
        s = str(text).strip().replace("\n", " ").replace("\r", " ")
        if not s:
            return ""
        return s if len(s) <= limit else (s[:limit].rstrip() + "…")

    @classmethod
    def _extract_character_brief(cls, character: Dict[str, Any], is_main: bool = False) -> Optional[Dict[str, str]]:
        """从一个 character dict 中按通用字段提取最关键的"硬约束"档案。

        每个字段都做存在性检查；任何字段缺失都不会崩溃，只会输出"未指定"或跳过。
        这套提取规则对任何符合 characters.json 通用结构的小说都成立——
        只读字段名，不读字段值，更不假设任何具体角色身份。
        """
        if not isinstance(character, dict):
            return None
        name = cls._safe_get_name(character)
        if not name:
            return None

        basic = character.get("basic_info") or {}
        personality = character.get("personality") or {}
        background = character.get("background") or {}

        # role 在 characters.json 中的位置：
        # - main_character 没有显式 role 字段，是主角（is_main=True）
        # - supporting_characters[i].role 直接是字符串（"反派" / "助手" / "受害者"...）
        if is_main:
            role_text = "主角"
        else:
            role_text = (character.get("role") or "").strip() or "配角（角色定位未指定）"

        occupation = (basic.get("occupation") or "").strip()
        # 性格描述：优先取摘要，其次取 description 第一句
        personality_desc = ""
        if isinstance(personality, dict):
            personality_desc = (personality.get("description") or "").strip()
        elif isinstance(personality, str):
            personality_desc = personality.strip()

        # 背景：优先取 past_experience，其次 motivation，其次顶层 background 字符串
        bg_text = ""
        if isinstance(background, dict):
            bg_text = (background.get("past_experience")
                       or background.get("motivation")
                       or background.get("core_desire") or "").strip()
        elif isinstance(background, str):
            bg_text = background.strip()

        # 与主角关系：主角自己跳过，配角必出
        relation_text = ""
        if not is_main:
            relation_text = (character.get("relationship_with_main") or "").strip()

        return {
            "name": name,
            "role": cls._truncate(role_text, 60),
            "occupation": cls._truncate(occupation, 80) if occupation else "",
            "key_traits": cls._truncate(personality_desc, 200) if personality_desc else "",
            "background": cls._truncate(bg_text, 200) if bg_text else "",
            "relation_with_main": cls._truncate(relation_text, 250) if relation_text else "",
        }

    @classmethod
    def _build_character_briefs_block(
        cls,
        main_character: Optional[Dict[str, Any]],
        supporting_characters: Optional[List[Dict[str, Any]]],
        only_names: Optional[List[str]] = None,
        title: str = "人物档案",
    ) -> str:
        """渲染一个可直接拼进 prompt 的人物档案块。

        参数：
          main_character / supporting_characters：原始 characters.json 中的两段；
            任一为 None 都会被安全跳过。
          only_names：若提供，则只保留 name 在该列表中的角色（用于"本章出场人物"按需精挑）。
          title：本档案块的标题，方便在不同 prompt 中复用。

        若没有任何角色可渲染，返回空字符串（调用方据此决定是否插入区块）。
        """
        briefs: List[Dict[str, str]] = []
        if isinstance(main_character, dict):
            mb = cls._extract_character_brief(main_character, is_main=True)
            if mb and (only_names is None or mb["name"] in only_names):
                briefs.append(mb)
        for sup in (supporting_characters or []):
            sb = cls._extract_character_brief(sup, is_main=False)
            if sb and (only_names is None or sb["name"] in only_names):
                briefs.append(sb)

        if not briefs:
            return ""

        lines = [f"=== {title} ==="]
        lines.append("以下每位人物的【姓名 / 角色定位 / 职业 / 与主角关系】是不可篡改的核心设定。"
                     "你在写作中不得擅自改写、调换阵营、改变身份、改变性别，或与白名单中的其他人物混淆；"
                     "违反将直接导致本章作废。")
        for b in briefs:
            parts = [f"【{b['name']}】"]
            parts.append(f"角色定位：{b['role']}")
            if b["occupation"]:
                parts.append(f"职业：{b['occupation']}")
            if b["relation_with_main"]:
                parts.append(f"与主角关系：{b['relation_with_main']}")
            if b["key_traits"]:
                parts.append(f"核心性格：{b['key_traits']}")
            if b["background"]:
                parts.append(f"关键背景：{b['background']}")
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 通用故事架构精炼器（从 storyline.overall_storyline 通用提取）
    # ------------------------------------------------------------------
    @classmethod
    def _build_story_arc_block(cls, storyline_arc: Optional[Dict[str, Any]]) -> str:
        """从 storyline.overall_storyline 中通用提取宏观剧情骨架，渲染为 prompt 块。

        只读 act1/act2/act3、main_goal、core_conflict、themes 这些通用字段；
        任何字段缺失都跳过该项，不崩溃。完全不依赖具体小说题材。
        """
        if not isinstance(storyline_arc, dict) or not storyline_arc:
            return ""

        lines: List[str] = []
        main_goal = (storyline_arc.get("main_goal") or "").strip()
        if main_goal:
            lines.append(f"主线目标：{cls._truncate(main_goal, 300)}")

        core_conflict = storyline_arc.get("core_conflict") or {}
        if isinstance(core_conflict, dict):
            ext = (core_conflict.get("external") or "").strip()
            inter = (core_conflict.get("interpersonal") or "").strip()
            internal = (core_conflict.get("internal") or "").strip()
            if ext:
                lines.append(f"外部冲突：{cls._truncate(ext, 250)}")
            if inter:
                lines.append(f"人际冲突：{cls._truncate(inter, 250)}")
            if internal:
                lines.append(f"内心冲突：{cls._truncate(internal, 250)}")
        elif isinstance(core_conflict, str) and core_conflict.strip():
            lines.append(f"核心冲突：{cls._truncate(core_conflict, 250)}")

        # 三幕骨架——只取最关键的几个里程碑字段
        for act_key, act_label in (("act1", "第一幕"), ("act2", "第二幕"), ("act3", "第三幕")):
            act = storyline_arc.get(act_key)
            if not isinstance(act, dict):
                continue
            act_lines: List[str] = []
            for field, label in (
                ("setup", "建立"),
                ("inciting_incident", "激励事件"),
                ("ending", "幕末状态"),
                ("confrontation", "对抗主轴"),
                ("midpoint_crisis", "中点危机"),
                ("low_point", "低谷"),
                ("turning_point", "转折点"),
                ("climax_preparation", "高潮前置"),
                ("climax", "高潮"),
                ("resolution", "解决方案"),
                ("character_transformation", "人物蜕变"),
            ):
                v = (act.get(field) or "").strip()
                if v:
                    act_lines.append(f"  · {label}：{cls._truncate(v, 220)}")
            if act_lines:
                lines.append(f"\n{act_label}：")
                lines.extend(act_lines)

        themes = storyline_arc.get("themes")
        if isinstance(themes, list) and themes:
            theme_text = "；".join(cls._truncate(t, 60) for t in themes if t)
            if theme_text:
                lines.append(f"\n核心主题：{theme_text}")

        if not lines:
            return ""
        return "=== 故事架构（来自原始故事圣经，是本书的剧情骨架，蓝图必须与之吻合）===\n" + "\n".join(lines)

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                m = re.search(r"-?\d+", str(value))
                return int(m.group()) if m else default
            except Exception:
                return default

    # ------------------------------------------------------------------
    # IO 辅助：保存到 data/novels/<id>/outline/
    # ------------------------------------------------------------------
    @staticmethod
    def save_blueprint(novel_id: str, blueprint: Dict[str, Any]) -> str:
        outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
        os.makedirs(outline_dir, exist_ok=True)
        path = os.path.join(outline_dir, "blueprint.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blueprint, f, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def save_volume_cards(novel_id: str, volume_index: int, payload: Dict[str, Any]) -> str:
        outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
        os.makedirs(outline_dir, exist_ok=True)
        path = os.path.join(outline_dir, f"volume_{volume_index}_chapters.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
