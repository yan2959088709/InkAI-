"""
ChapterCardWriter —— 基于 ChapterCard 的单章写作 Agent（独立组件，零侵入现有系统）

设计原则
--------
1. 输出格式锁死：chapter_content 永远是【纯字符串】，不嵌套 dict —— 修掉之前
   batch_continuation 中 'dict' object has no attribute 'replace' 那类隐患
2. 写作约束前置：主角名 / 名字白名单 / banned_endings 直接进 system prompt
3. 后置轻量校验：主角名出现次数、字数、banned 子串、白名单外姓名候选
4. 失败重写只一次：避免无限循环；重写时把上次失败原因回灌进 prompt
5. 不依赖现有 workflow / 任何 chapter_writer，可独立 demo

输入 (process)
--------------
{
  "chapter_card": {...},           # 必填，单张 ChapterCard
  "blueprint": {...},              # 必填，整本蓝图（用来取 meta + volume context）
  "recent_chapters": [             # 可选，最近 N 篇原文（不要太长）
      {"chapter_number": int, "title": str, "content": str}, ...
  ],
  "banned_endings": [str],         # 可选，前面用过的 ending_hook
  "style_anchor": str,             # 可选，风格锚点（如首章开头节选）
  "target_word_count": int         # 可选，默认 2500
}

输出
----
{
  "chapter_number": int,
  "title": str,
  "chapter_content": str,          # 纯字符串！
  "word_count": int,
  "validation": {
      "protagonist_count": int,
      "protagonist_present": bool,
      "word_count_ok": bool,
      "banned_hits": [str],
      "must_appear": {                  # 反查 chapter_card.must_appear 是否真的出现
          "characters": {"expected", "ok", "light", "missing"},
          "locations":  {同上},
          "objects":    {同上},
          "coverage": float, ...
      },
      "must_characters_missing": [str], # 卡片声明但完全没出场的角色（硬失败 → 触发重写）
      "must_objects_missing":    [str], # 卡片声明但完全没出场的关键道具（硬失败 → 触发重写）
      "passed": bool
  },
  "_generation": {
      "retried": bool,
      "revised_from_feedback": bool,    # 是否使用了外部 force_revise_feedback
      "raw_response_length": int
  }
}
"""

from typing import Dict, List, Any, Optional
import json
import re

from base_agent import BaseAgent
import config


class ChapterCardWriter(BaseAgent):
    """基于 ChapterCard 的单章写作器"""

    DEFAULT_TARGET_WORD_COUNT = 2500
    WRITER_TEMPERATURE = 0.85
    # 截断阈值。qwen 系列普遍有 128K~1M 上下文，6000 字会把关键 ending_hook 截掉。
    # 30000 字 ≈ 5 篇 2500 字章节的全文，仍远低于上下文上限。
    MAX_RECENT_CHAPTERS_CHARS = 30000
    # 单篇正文上限：避免某一篇过长就把后面更近的章节挤出 budget。
    PER_CHAPTER_HARD_CAP = 8000

    def __init__(self, genre_pack: Any = None):
        super().__init__("章节卡写手")
        self.temperature = self.WRITER_TEMPERATURE
        # genre_pack: 可选 GenrePack 实例。为 None 时行为完全等价于原版（题材中立）。
        self.genre_pack = genre_pack

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        validation = self.validate_input(input_data, ["chapter_card", "blueprint"])
        if not validation["is_valid"]:
            return {"error": validation["error"]}

        chapter_card = input_data["chapter_card"]
        blueprint = input_data["blueprint"]
        recent_chapters = input_data.get("recent_chapters") or []
        banned_endings = input_data.get("banned_endings") or []
        style_anchor = input_data.get("style_anchor") or ""
        target_word_count = int(input_data.get("target_word_count") or self.DEFAULT_TARGET_WORD_COUNT)
        # 可选：上一次写作的 validation 字典；若提供则首次写作即按 retry-prompt 走，
        # 用于"基于 Validator 报告对硬遗漏章做修补"的闭环场景。
        force_revise_feedback = input_data.get("force_revise_feedback")
        # 可选：DynamicKnowledgeManager.format_snapshot_for_prompt 渲染好的字符串
        # （或者直接传 snapshot dict，由本类渲染）。用于让 Writer 知道"截至上章的世界状态"。
        dynamic_state_block: str = input_data.get("dynamic_state_block") or ""
        if not dynamic_state_block and input_data.get("dynamic_state_snapshot"):
            try:
                from core.dynamic_knowledge_manager import DynamicKnowledgeManager
                dynamic_state_block = DynamicKnowledgeManager.format_snapshot_for_prompt(
                    input_data["dynamic_state_snapshot"]
                )
            except Exception:
                dynamic_state_block = ""

        # 可选：完整的人物档案 dict，结构与 characters.json 一致：
        #   {"main_character": {...}, "supporting_characters": [...]}
        # 用于让 Writer 知道每位本章出场角色的【角色定位 / 阵营 / 与主角关系】等硬约束，
        # 防止"角色身份漂移"（典型如反派被写成主角同事、女性角色被写成男性等）。
        # 调用方未传时，自动从 blueprint["_source_briefs"] 兜底（OutlinePlanner 在生成蓝图时缓存了）。
        character_profiles: Dict[str, Any] = input_data.get("character_profiles") or {}
        if not character_profiles:
            briefs_cache = blueprint.get("_source_briefs") or {}
            if briefs_cache:
                character_profiles = {
                    "main_character": briefs_cache.get("main_character") or {},
                    "supporting_characters": briefs_cache.get("supporting_characters") or [],
                }
        character_briefs_block = self._build_character_briefs_for_chapter(
            chapter_card=chapter_card,
            character_profiles=character_profiles,
        )

        meta = blueprint.get("meta", {}) or {}
        protagonist_name = meta.get("protagonist_name", "").strip()
        name_whitelist = meta.get("name_whitelist", []) or []
        if not protagonist_name:
            return {"error": "blueprint.meta.protagonist_name 为空，拒绝写作"}

        volume_context = self._find_volume_context(blueprint, chapter_card.get("volume"))
        ch_num = int(chapter_card.get("chapter_number", 0))

        if force_revise_feedback:
            self.log(
                f"开始修订第 {ch_num} 章（基于上次 validation 强制 retry） 主角={protagonist_name} 目标字数≈{target_word_count}"
            )
        else:
            self.log(f"开始撰写第 {ch_num} 章 主角={protagonist_name} 目标字数≈{target_word_count}")

        # 第一次写作（或修订）
        raw = self._call_writer(
            chapter_card=chapter_card,
            meta=meta,
            volume_context=volume_context,
            recent_chapters=recent_chapters,
            banned_endings=banned_endings,
            style_anchor=style_anchor,
            target_word_count=target_word_count,
            protagonist_name=protagonist_name,
            name_whitelist=name_whitelist,
            retry_feedback=force_revise_feedback,
            dynamic_state_block=dynamic_state_block,
            character_briefs_block=character_briefs_block,
        )
        title, body = self._split_title_and_body(raw, default_title=chapter_card.get("title") or f"第{ch_num}章")
        validation_result = self._validate_chapter(
            body=body,
            protagonist_name=protagonist_name,
            chapter_card=chapter_card,
            banned_endings=banned_endings,
            target_word_count=target_word_count,
        )

        # must_appear 软告警：locations 漏掉只 log 不重写（characters/objects 已升格为硬失败）
        ma = validation_result.get("must_appear", {})
        soft_misses = [m["name"] for m in (ma.get("locations") or {}).get("missing", [])]
        if soft_misses:
            self.log(
                f"[INFO] 第{ch_num}章 must_appear.locations 软遗漏（不重写，仅记录）：{soft_misses}"
            )

        retried = False
        if not validation_result["passed"]:
            self.log(f"⚠️ 第{ch_num}章首次校验未通过（硬失败）：{self._summarize_validation(validation_result)}，重写一次")
            retried = True
            raw2 = self._call_writer(
                chapter_card=chapter_card,
                meta=meta,
                volume_context=volume_context,
                recent_chapters=recent_chapters,
                banned_endings=banned_endings,
                style_anchor=style_anchor,
                target_word_count=target_word_count,
                protagonist_name=protagonist_name,
                name_whitelist=name_whitelist,
                retry_feedback=validation_result,
                dynamic_state_block=dynamic_state_block,
                character_briefs_block=character_briefs_block,
            )
            title2, body2 = self._split_title_and_body(raw2, default_title=chapter_card.get("title") or f"第{ch_num}章")
            validation_result2 = self._validate_chapter(
                body=body2,
                protagonist_name=protagonist_name,
                chapter_card=chapter_card,
                banned_endings=banned_endings,
                target_word_count=target_word_count,
            )
            if validation_result2["passed"] or self._score(validation_result2) > self._score(validation_result):
                title, body, validation_result, raw = title2, body2, validation_result2, raw2

        return {
            "chapter_number": ch_num,
            "title": title,
            "chapter_content": body,  # ← 纯字符串
            "word_count": len(body),
            "validation": validation_result,
            "_generation": {
                "retried": retried,
                "revised_from_feedback": bool(force_revise_feedback),
                "raw_response_length": len(raw or ""),
            },
        }

    # ------------------------------------------------------------------
    # LLM 调用与 prompt
    # ------------------------------------------------------------------
    def _call_writer(
        self,
        chapter_card: Dict[str, Any],
        meta: Dict[str, Any],
        volume_context: Dict[str, Any],
        recent_chapters: List[Dict[str, Any]],
        banned_endings: List[str],
        style_anchor: str,
        target_word_count: int,
        protagonist_name: str,
        name_whitelist: List[str],
        retry_feedback: Optional[Dict[str, Any]],
        dynamic_state_block: str = "",
        character_briefs_block: str = "",
    ) -> str:
        system = self._system_prompt(protagonist_name, name_whitelist)
        user = self._build_user_prompt(
            chapter_card=chapter_card,
            meta=meta,
            volume_context=volume_context,
            recent_chapters=recent_chapters,
            banned_endings=banned_endings,
            style_anchor=style_anchor,
            target_word_count=target_word_count,
            protagonist_name=protagonist_name,
            retry_feedback=retry_feedback,
            dynamic_state_block=dynamic_state_block,
            character_briefs_block=character_briefs_block,
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.call_llm(messages, temperature=self.WRITER_TEMPERATURE, max_tokens=config.MAX_TOKENS)

    def _system_prompt(
        self,
        protagonist_name: str,
        name_whitelist: List[str],
    ) -> str:
        whitelist_text = "、".join([n for n in name_whitelist if n]) or protagonist_name
        base = (
            f"你是一位资深中文小说写手，正在为长篇小说连载写单章正文。\n"
            f"--【铁律】--\n"
            f"1. 主角的名字是【{protagonist_name}】，绝对禁止改名、化名、自创主角；"
            f"任何人物/地点/组织名只能从下列白名单中选取：{whitelist_text}。\n"
            f"   如果剧情需要无关路人，使用泛化称呼（'那个男人'、'药店老板'），不要给出新姓名。\n"
            f"2. 你将得到一张 ChapterCard 作为本章剧情骨架（role / beats / must_appear / "
            f"foreshadow_plant / foreshadow_payoff / ending_hook），里面规定的事件你必须全部写出来；"
            f"但叙述方式、节奏与细节由你决定。\n"
            f"3. 严禁使用前几章已用过的钩子句式或意象（避免模板复读）；具体禁用清单见 user prompt 中的【本章禁用钩子】。\n"
            f"4. 字数控制在目标值±20%；具体目标字数见 user prompt 中的【目标字数】。\n"
            f"5. 输出格式必须严格如下：\n"
            f"   第一行：第N章 标题\n"
            f"   第二行：空行\n"
            f"   第三行起：正文\n"
            f"   不要 JSON、不要 markdown、不要解释、不要小标题、不要前言、不要后记。"
        )
        addon = ""
        if self.genre_pack is not None:
            try:
                addon = self.genre_pack.system_prompt_addon(role="writer") or ""
            except Exception:
                addon = ""
        if addon:
            return base + "\n\n=== 题材规则（来自 GenrePack） ===\n" + addon
        return base

    def _build_user_prompt(
        self,
        chapter_card: Dict[str, Any],
        meta: Dict[str, Any],
        volume_context: Dict[str, Any],
        recent_chapters: List[Dict[str, Any]],
        banned_endings: List[str],
        style_anchor: str,
        target_word_count: int,
        protagonist_name: str,
        retry_feedback: Optional[Dict[str, Any]],
        dynamic_state_block: str = "",
        character_briefs_block: str = "",
    ) -> str:
        recent_text = self._compose_recent_chapters_text(recent_chapters)
        prev_anchor_text = self._extract_prev_anchor(recent_chapters)
        style_text = (style_anchor or "").strip()[:1500]

        # [Issue #2] 动态内容放 user prompt，保持 system prompt 静态以命中 LLM 缓存
        banned_block = ""
        if banned_endings:
            banned_block = "\n=== 本章禁用钩子（句式/意象，严禁复用）===\n- " + "\n- ".join(banned_endings) + "\n"

        target_block = (
            f"\n=== 目标字数 ===\n{target_word_count} ±20%"
            f"（{int(target_word_count*0.8)}~{int(target_word_count*1.3)}），严禁灌水凑字数\n"
        )

        retry_block = ""
        if retry_feedback:
            issues = []
            if not retry_feedback.get("protagonist_present"):
                issues.append(f"上次正文中主角【{protagonist_name}】出现 {retry_feedback.get('protagonist_count', 0)} 次，太少甚至缺席，必须让主角全程在场并多次以姓名指代")
            if retry_feedback.get("banned_hits"):
                issues.append(f"上次结尾出现禁用钩子：{retry_feedback['banned_hits']}，本次必须换一种意象与句式")
            if not retry_feedback.get("word_count_ok"):
                issues.append(f"上次字数偏离目标，请控制在 {int(target_word_count*0.8)}~{int(target_word_count*1.2)} 字")
            miss_chars = retry_feedback.get("must_characters_missing") or []
            if miss_chars:
                issues.append(f"上次正文未让 must_appear.characters 中的角色 {miss_chars} 真正出场（甚至连姓名都没出现），本次必须给他们至少各 2 次台词或动作")

            # 软提示：locations / objects 漏掉的也带上，让模型自然把它们写进去
            ma = retry_feedback.get("must_appear") or {}
            miss_locs = [m["name"] for m in (ma.get("locations") or {}).get("missing", [])]
            if miss_locs:
                issues.append(f"上次正文遗漏了 must_appear.locations 中的场景 {miss_locs}，本次至少描写一次（哪怕一两句环境/方位）")
            miss_objs = [m["name"] for m in (ma.get("objects") or {}).get("missing", [])]
            if miss_objs:
                issues.append(
                    "上次正文完全遗漏了 must_appear.objects 中的关键道具 "
                    f"{miss_objs}，这是剧情承重物，缺一个整章逻辑就崩。本次硬性要求："
                    "（1）每个道具的【完整原词】必须在正文中至少出现一次"
                    "（如卡片名为'恐吓信'，正文里必须有'恐吓信'三个字连写一次，"
                    "不可改写成'威胁信'/'匿名信'/'纸条'/'卡片'等同义替换）；"
                    "（2）该道具必须在剧情中真正起作用（被发现/被使用/被解读），"
                    "不是仅作背景物提一下；（3）若 ChapterCard.beats 已经描述了道具登场方式，"
                    "请按 beats 写，不要把'印有遗照的恐吓信'拆解成'一张印有遗照的卡片'。"
                )

            if issues:
                retry_block = "\n=== ⚠️ 上一次写作的问题（本次必须修正） ===\n- " + "\n- ".join(issues) + "\n"

        dynamic_block = ""
        if dynamic_state_block:
            dynamic_block = "\n" + dynamic_state_block.strip() + "\n"

        # 优雅降级：character_briefs_block 为空时不出现孤标题（向后兼容旧调用方）
        char_block = ""
        if character_briefs_block and character_briefs_block.strip():
            char_block = "\n" + character_briefs_block.strip() + "\n"

        return f"""请按下列约束完成本章写作。
{banned_block}{target_block}
=== 本章 ChapterCard（剧情骨架，必须全部覆盖）===
{json.dumps(chapter_card, ensure_ascii=False, indent=2)}
{char_block}
=== 整本元信息 ===
{json.dumps(meta, ensure_ascii=False)}

=== 当前卷信息 ===
{json.dumps(volume_context, ensure_ascii=False)}
{dynamic_block}
=== 最近章节正文（既是文风样本，更是【事实承接锚点】）===
说明：以下是已经发生的剧情，对你而言它们是【既成事实】，不可推翻、不可绕过、不可"重置"。
本章 beats[0] 必须从【上一章末尾的状态】自然推进——上章在场的人物本章不会凭空消失，
上章拿到的关键道具/线索本章必须延续使用，上章揭示的认知不可在本章被无视。
你可以新增过渡或新事件，但不得让本章看起来像"另起一段，与上一章无关"。

{recent_text or "（无）"}
{prev_anchor_text}
=== 风格锚点（首章节选/语感参考）===
{style_text or "（无）"}
{retry_block}
=== 写作要求 ===
- 严格按 ChapterCard.beats 的顺序推进，可以在节拍间补过渡，但不得增删事件
- ChapterCard.must_appear.characters 全部要在本章登场（至少有可识别的描写或台词）
- ChapterCard.must_appear.objects 中的【关键道具】必须以原词原样在正文中出现至少一次，并真正参与剧情（不可用同义词代替，不可只在背景里提一下）
- ChapterCard.foreshadow_plant 中的伏笔必须在本章里"以剧情方式"埋下（不要直接告诉读者"这是伏笔"）
- ChapterCard.foreshadow_payoff 中的伏笔必须在本章被显现/兑现，让前读者能"恍然大悟"
- 章末要自然落到 ChapterCard.ending_hook 的意境，但句式与意象都要避开 banned_endings
- 全章紧扣 ChapterCard.tone 与 tension_level={chapter_card.get('tension_level', 5)}
- 第三人称叙事，以主角【{protagonist_name}】为主视角
- 多用对话、动作、感官细节，少用大段心理独白与"他想到……"

请直接输出本章正文，第一行严格为：第{chapter_card.get('chapter_number', 0)}章 {chapter_card.get('title', '')}
"""

    # ------------------------------------------------------------------
    # 通用：根据本章 must_appear.characters 精挑当前章涉及的人物档案
    # ------------------------------------------------------------------
    def _build_character_briefs_for_chapter(
        self,
        chapter_card: Dict[str, Any],
        character_profiles: Dict[str, Any],
    ) -> str:
        """根据 chapter_card.must_appear.characters，从完整人物档案中精挑本章登场者，
        渲染成一个可直接拼进 prompt 的硬约束块。

        通用、数据驱动：
        - 不假设任何具体角色名 / 身份；
        - 只读 characters.json 的标准字段名；
        - profiles 缺失或 must_appear 为空时优雅降级为空字符串（不出现孤标题）。

        渲染逻辑沿用 OutlinePlanner._build_character_briefs_block，
        以避免同一套规则在两处实现漂移；只是在这里按"本章出场名单"做精挑。
        """
        if not isinstance(character_profiles, dict) or not character_profiles:
            return ""
        must_appear = chapter_card.get("must_appear") or {}
        names_in_chapter = [n for n in (must_appear.get("characters") or []) if n]
        # 即使本章 must_appear.characters 为空，主角也应该被包含（写作硬约束本就要求主角全程在场）
        main_char = character_profiles.get("main_character") or {}
        main_name = ""
        if isinstance(main_char, dict):
            basic = main_char.get("basic_info") or {}
            main_name = (basic.get("name") or main_char.get("name") or "").strip()
        if main_name and main_name not in names_in_chapter:
            names_in_chapter.append(main_name)

        if not names_in_chapter:
            return ""

        try:
            from core.outline_planner import OutlinePlanner
            return OutlinePlanner._build_character_briefs_block(
                main_character=main_char,
                supporting_characters=character_profiles.get("supporting_characters") or [],
                only_names=names_in_chapter,
                title="本章出场人物的硬性档案（不可改写）",
            )
        except Exception:
            # 任何异常都降级为空，绝不让人物档案注入打断写作流程
            return ""

    def _extract_prev_anchor(self, recent_chapters: List[Dict[str, Any]]) -> str:
        """从最近章节中抽取【上一章末段】作为承接硬约束块。

        这是 F4 的核心：除了让 LLM 看到完整原文，还要在 prompt 里
        显式高亮"前章结尾的最后那段"，并明文要求本章首段必须从此推进。
        """
        if not recent_chapters:
            return ""
        ordered = sorted(
            [ch for ch in recent_chapters if (ch.get("content") or "").strip()],
            key=lambda c: int(c.get("chapter_number", 0)),
        )
        if not ordered:
            return ""
        prev = ordered[-1]
        body = (prev.get("content") or "").strip()
        # 取最后 ~400 字（一般覆盖最后 1-2 个段落，包含 ending_hook）
        tail = body[-400:] if len(body) > 400 else body
        prev_no = prev.get("chapter_number", "?")
        prev_title = prev.get("title", "")
        return (
            f"\n=== ⚓ 上一章承接锚点（第{prev_no}章《{prev_title}》末段，本章 beats[0] 必须从这里自然推进）===\n"
            f"{tail}\n"
            f"硬性要求：\n"
            f"- 本章开头不得【另起一段、与上一段毫无因果联系】。\n"
            f"- 上一章末段中出现的【人物/地点/道具/感官信息】，本章首段或前 1-2 段必须有所呼应。\n"
            f"- 不得在本章直接跳过上一章末段悬而未决的动作（例如上一章末出现的物件、对话、关键画面）。\n"
        )

    def _compose_recent_chapters_text(self, recent_chapters: List[Dict[str, Any]]) -> str:
        """组装最近章节正文。

        关键设计（修复连续性 bug）：
        - 从**最新章节往回**累加 budget。最新一章（直接前章）拥有最高优先级，
          其 ending_hook / 关键道具 / 在场人物绝不会被截断丢失。
        - 单篇软上限 PER_CHAPTER_HARD_CAP，避免某一长章吃掉所有 budget。
        - 渲染顺序仍按时间正序（旧→新），保留阅读时的因果脉络。
        """
        if not recent_chapters:
            return ""

        # 按 chapter_number 升序，避免上游传入顺序不稳定
        ordered = sorted(
            [ch for ch in recent_chapters if (ch.get("content") or "").strip()],
            key=lambda c: int(c.get("chapter_number", 0)),
        )
        if not ordered:
            return ""

        budget = self.MAX_RECENT_CHAPTERS_CHARS
        per_cap = self.PER_CHAPTER_HARD_CAP
        # 反向优先：从最新章节倒着填，最新章节绝不会被截掉
        kept_reverse: List[str] = []
        for ch in reversed(ordered):
            content = (ch.get("content") or "").strip()
            header = f"【第{ch.get('chapter_number', '?')}章 {ch.get('title', '')}】\n"
            # 单篇硬上限：太长的旧章节先自我压缩
            if len(content) > per_cap:
                # 保留首段 + 末段（末段含 ending_hook，最有承接价值）
                head = content[: per_cap // 2]
                tail = content[-(per_cap // 2):]
                content = head + "\n...（中段省略）...\n" + tail
            chunk = header + content
            if len(chunk) > budget:
                # budget 不够：仍优先保留末尾（ending_hook）
                if budget > len(header) + 200:
                    truncated = chunk[-budget:]
                    kept_reverse.append("...（前段截断）...\n" + truncated)
                # 已无 budget，停止往更旧的章节走
                break
            kept_reverse.append(chunk)
            budget -= len(chunk) + 8  # 8 是分隔符开销
            if budget <= 0:
                break

        # 反向收集后再翻回时间正序
        kept = list(reversed(kept_reverse))
        return "\n\n----\n\n".join(kept)

    # ------------------------------------------------------------------
    # 解析 / 校验
    # ------------------------------------------------------------------
    def _split_title_and_body(self, raw: str, default_title: str) -> (str, str):
        """从 LLM 原始返回里剥出 (title, body)"""
        if not raw:
            return default_title, ""

        text = raw.strip()
        # 去掉 markdown 代码块包裹
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()

        # 寻找 "第X章 ..." 起始行
        m = re.search(r"(第[一二三四五六七八九十百千万0-9]+章[^\n]*)", text)
        if not m:
            return default_title, text.strip()

        title_line = m.group(1).strip()
        body_start = m.end()
        body = text[body_start:].lstrip("\n").strip()
        return title_line, body

    def _validate_chapter(
        self,
        body: str,
        protagonist_name: str,
        chapter_card: Dict[str, Any],
        banned_endings: List[str],
        target_word_count: int,
    ) -> Dict[str, Any]:
        """单章硬校验：主角出场 / 字数 / 钩子复读 / must_appear 兑现。

        说明：之前还做过"白名单外姓名候选"的启发式（_scan_illegal_name_candidates），
        在生产上证明误报率高、需要堆维护性极差的中文常用词词典，方向是错的。
        现已彻底删除，改为基于 chapter_card.must_appear 的确定性反查 ——
        OutlinePlanner 已经规划好了"本章必须出场的人/地/物"，写手只需对账即可。
        """
        from utils.must_appear_check import check_card_against_body

        body = body or ""
        word_count = len(body)

        protagonist_count = body.count(protagonist_name) if protagonist_name else 0
        protagonist_present = protagonist_count >= 2

        # 字数：允许 -20% ~ +100%（即目标的 0.8x 到 2.0x）
        lower = int(target_word_count * 0.8)
        upper = int(target_word_count * 2.0)
        word_count_ok = lower <= word_count <= upper

        # banned ending 检查：只看正文末尾 300 字
        tail = body[-300:]
        banned_hits = [b for b in banned_endings if b and b.strip() and b.strip() in tail]

        # must_appear 反查
        must_report = check_card_against_body(chapter_card, body)
        # 硬失败标准：卡片声明的 characters / objects 中任何一个完全没出现（连模糊匹配都没命中）。
        # 关键道具（objects）是剧情承重物，缺一个就能让整章逻辑崩塌（如 ch19 缺"恐吓信"），
        # 因此与角色一并视为硬失败；locations 表达边界更模糊，仅记录不触发重写。
        characters_missing = [m["name"] for m in must_report["characters"]["missing"]]
        objects_missing = [m["name"] for m in must_report["objects"]["missing"]]
        must_characters_ok = len(characters_missing) == 0
        must_objects_ok = len(objects_missing) == 0

        passed = (
            protagonist_present
            and word_count_ok
            and not banned_hits
            and must_characters_ok
            and must_objects_ok
        )

        return {
            "protagonist_count": protagonist_count,
            "protagonist_present": protagonist_present,
            "word_count": word_count,
            "word_count_target": target_word_count,
            "word_count_ok": word_count_ok,
            "banned_hits": banned_hits,
            "must_appear": must_report,
            "must_characters_missing": characters_missing,
            "must_objects_missing": objects_missing,
            "passed": passed,
        }

    @staticmethod
    def _summarize_validation(v: Dict[str, Any]) -> str:
        """汇总硬失败原因（用于 retry 决策日志）。"""
        parts = []
        if not v.get("protagonist_present"):
            parts.append(f"主角出现={v.get('protagonist_count', 0)}")
        if not v.get("word_count_ok"):
            parts.append(f"字数={v.get('word_count', 0)}/目标={v.get('word_count_target', 0)}")
        if v.get("banned_hits"):
            parts.append(f"banned命中={v['banned_hits']}")
        if v.get("must_characters_missing"):
            parts.append(f"角色未出场={v['must_characters_missing']}")
        if v.get("must_objects_missing"):
            parts.append(f"关键道具缺失={v['must_objects_missing']}")
        return "; ".join(parts) or "ok"

    @staticmethod
    def _score(v: Dict[str, Any]) -> int:
        """打分函数仅基于硬条件，与 passed 判定一致。"""
        score = 0
        if v.get("protagonist_present"):
            score += 4
        if v.get("word_count_ok"):
            score += 2
        if not v.get("banned_hits"):
            score += 2
        if not v.get("must_characters_missing"):
            score += 2
        if not v.get("must_objects_missing"):
            score += 2
        return score

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    @staticmethod
    def _find_volume_context(blueprint: Dict[str, Any], volume_index: Any) -> Dict[str, Any]:
        try:
            vidx = int(volume_index)
        except (TypeError, ValueError):
            return {}
        for vol in blueprint.get("volumes", []) or []:
            if int(vol.get("index", -1)) == vidx:
                return vol
        return {}
