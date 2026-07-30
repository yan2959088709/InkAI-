"""
core/canon_checker.py —— 档案一致性校验器（Canon Checker）

定位：作为整套小说生成系统的"档案防卫层"，在 init/outline 阶段
拦截 characters.json 与 storyline.json 之间的契约破坏，避免脏数据
往下游 prompt / blueprint / chapter 链路扩散。

设计原则：
1. 纯规则驱动，不调 LLM，零成本可重复执行；
2. 通用、数据驱动，不硬编码任何角色名 / 作品名；
3. 高置信度优先，宁可漏报不要误报；
4. 输出结构化 issue 列表 + 人类可读摘要，便于后续 LLM 仲裁或人工裁决。

被以下入口使用：
- run_init_novel.py（写盘后自动跑一次）
- run_validate_canon.py（CLI，单独审查任意已有 novel）
- 后续可被 OutlinePlanner.generate_blueprint 在 spec 校验阶段调用
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Iterable


# 通用的"角色标签词"清单——用于在 storyline 文本中识别"X<人名>"或"<人名>（X）"等模式
# 不针对任何具体题材，仅覆盖最常见的角色关系语义。
ROLE_LABEL_TOKENS: Tuple[str, ...] = (
    "搭档", "师父", "师傅", "师兄", "师姐", "师弟", "师妹", "徒弟", "弟子",
    "队长", "副队长", "队友", "组长", "副组长", "组员",
    "局长", "副局长", "处长", "厅长",
    "上司", "上级", "下属", "属下",
    "法医", "警员", "刑警", "技术警", "技术员", "勘验员",
    "反派", "主使", "幕后", "凶手", "嫌疑人", "嫌犯",
    "受害者", "受害人", "被害者", "被害人", "失踪者",
    "线人", "举报人", "证人", "目击者",
    "记者", "媒体人",
    "助手", "顾问", "侧写师",
    "恋人", "爱人", "伴侣", "未婚夫", "未婚妻",
    "父亲", "母亲", "兄长", "弟弟", "姐姐", "妹妹",
    "教授", "导师",
)

# 角色标签互斥组——同一个人不能同时落入这些组里多于一个
# （组内可以并存，跨组则视为剧情冲突）
ROLE_EXCLUSIVE_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("搭档", "队友", "队长", "副队长", "组长", "副组长", "组员", "下属", "属下"),
    ("师父", "师傅", "导师", "上司", "上级", "教授"),
    ("反派", "主使", "幕后", "凶手", "嫌疑人", "嫌犯"),
    ("受害者", "受害人", "被害者", "被害人", "失踪者"),
    ("法医",),
    ("线人", "举报人", "证人", "目击者"),
)

# 中文人名捕获——保守版（2-4 个汉字）；后接括号或角色标签使用
_NAME_RE = re.compile(r"[\u4e00-\u9fa5]{2,4}")

# 性别代词
_PRONOUN_MALE = ("他", "他的", "他们")
_PRONOUN_FEMALE = ("她", "她的", "她们")

# 中国常见姓氏白名单（约 200 个，覆盖 ~99% 中文人名）
# 用于过滤"师父X" / "搭档X" 模式中 X 是不是真人名——避免把"师父刻意留下"
# 这种短句开头切成"刻意留下"误报为人名。
COMMON_SURNAMES: frozenset = frozenset([
    "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "吴", "周",
    "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗",
    "郑", "梁", "谢", "宋", "唐", "许", "韩", "冯", "邓", "曹",
    "彭", "曾", "肖", "田", "董", "袁", "潘", "于", "蒋", "蔡",
    "余", "杜", "叶", "程", "苏", "魏", "吕", "丁", "任", "沈",
    "姚", "卢", "姜", "崔", "钟", "谭", "陆", "汪", "范", "金",
    "石", "廖", "贾", "夏", "韦", "付", "方", "白", "邹", "孟",
    "熊", "秦", "邱", "江", "尹", "薛", "闫", "段", "雷", "侯",
    "龙", "史", "陶", "黎", "贺", "顾", "毛", "郝", "龚", "邵",
    "万", "钱", "严", "覃", "武", "戴", "莫", "孔", "向", "汤",
    "常", "温", "康", "施", "文", "牛", "樊", "葛", "邢", "安",
    "齐", "易", "乔", "伍", "庞", "颜", "倪", "庄", "聂", "章",
    "鲁", "岳", "翟", "殷", "詹", "申", "欧", "耿", "关", "兰",
    "焦", "俞", "左", "柳", "甘", "祝", "包", "宁", "尚", "符",
    "舒", "阮", "纪", "梅", "童", "凌", "毕", "单", "季", "裴",
    "霍", "涂", "成", "苗", "谷", "盛", "曲", "翁", "冷", "辛",
    "宫", "桂", "祁", "缪", "古", "解", "应", "井", "蓝", "米",
    "蒙", "池", "原", "屈", "封", "骆", "宗", "佘", "费", "鲍",
    "靳", "门", "雍", "公", "丛", "吉", "全", "司", "卓", "戚",
    "管", "卞", "邝", "海", "都", "巫", "甄", "项", "麻",
    # 复姓
    "欧阳", "司马", "上官", "诸葛", "皇甫", "尉迟", "公孙", "令狐",
    "宇文", "长孙", "慕容", "百里", "东方", "西门", "南宫", "北堂",
])

# 名字尾部不允许是这些"虚词/常见连接字"，否则视为切错位
_NAME_TAIL_BLACKLIST: frozenset = frozenset([
    "的", "之", "在", "于", "以", "为", "与", "和", "及", "或",
    "把", "被", "让", "使", "将", "向", "往", "从", "到", "对",
    "并", "也", "都", "就", "还", "又", "再", "便", "却", "已",
    "了", "过", "着", "得", "上", "下", "中", "里", "外", "前",
    "后", "时", "等", "者", "者", "等", "如", "若", "似", "如",
    "是", "非", "有", "无",
])

# 名字第二/三/四字也不能命中"明显是动词/名词词根"的常见字
# （从误报数据归纳：殉、职、刻、留、画、像、黑、网、灭、配、基、墓、衍）
_NAME_BODY_BLACKLIST: frozenset = frozenset([
    "殉", "职", "刻", "留", "画", "像", "黑", "网", "灭", "配",
    "基", "墓", "衍", "审", "调", "因", "正", "高", "组", "完",
    "整", "传", "故", "事", "前", "记", "录", "经", "手", "现",
    "场", "前", "前最", "可", "靠", "队", "友", "线", "人", "物",
    "中", "发", "去", "口", "审", "定", "决", "理", "解", "析",
    "析", "材", "料", "件", "案", "卷", "宗", "册",
])

# 通用非人名短语白名单——命中则直接丢弃（这些都是中文里常见的、容易被
# 错切成"姓+常见字"的抽象名词或职务名词）。不针对具体题材。
_NON_NAME_PHRASES: frozenset = frozenset([
    # 抽象层级 / 集合
    "高层", "上层", "底层", "中层", "层面",
    "众人", "诸位", "各位", "众生", "群众",
    # 通用职务（不带姓）
    "门主", "宗主", "庄主", "盟主", "教主", "城主", "山主",
    "弟子", "徒弟", "师叔", "师伯", "师祖", "长老",
    "头目", "首脑", "干部", "成员",
    # 抽象施事方
    "对方", "敌方", "我方", "他方", "双方", "各方", "多方",
    "组织", "势力", "阵营", "团队",
    # 题材通用反派/凶手代称
    "黑手", "幕后", "主使", "凶手", "歹徒", "反派",
    # 物件/概念
    "证据", "线索", "目标", "动机", "结果", "原因",
    "记忆", "梦境", "幻象", "灵魂", "肉身",
    # 时间/地点抽象
    "当下", "此时", "此刻", "此地", "此处", "彼时", "彼地",
    # 常见 4 字成语 / 套话短语（防止"安分守己"被切成"安+分守己"误判为人名）
    "安分守己", "安然无恙", "安之若素", "苏醒过来", "马不停蹄",
    "钟灵毓秀", "钟鸣鼎食", "李代桃僵", "张牙舞爪", "刘姥姥",
    "胡作非为", "胡言乱语", "周而复始", "周到细致",
])


@dataclass
class CanonIssue:
    rule_id: str
    severity: str  # ERROR / WARNING / INFO
    title: str
    detail: str
    subject: str = ""           # 涉及的人物/对象
    suggestions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)


@dataclass
class CanonReport:
    novel_id: str
    novel_dir: str
    summary: Dict[str, int]
    issues: List[CanonIssue]
    registered_main: Optional[str]
    registered_supporting: List[str]
    storyline_named_unregistered: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "novel_id": self.novel_id,
            "novel_dir": self.novel_dir,
            "summary": self.summary,
            "issues": [asdict(i) for i in self.issues],
            "registered_main": self.registered_main,
            "registered_supporting": self.registered_supporting,
            "storyline_named_unregistered": self.storyline_named_unregistered,
        }

    def has_errors(self) -> bool:
        return self.summary.get("ERROR", 0) > 0


# ----------------------------------------------------------------------
# 辅助：递归把任意嵌套 JSON 拍平成纯文本（用于全局名字搜索）
# ----------------------------------------------------------------------
def _flatten_to_text(node: Any) -> str:
    """把任意 JSON 子树递归拼成大字符串。"""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, (int, float, bool)):
        return str(node)
    if isinstance(node, list):
        return "\n".join(_flatten_to_text(x) for x in node)
    if isinstance(node, dict):
        return "\n".join(f"{k}: {_flatten_to_text(v)}" for k, v in node.items())
    return str(node)


def _iter_string_with_path(node: Any, path: str = "") -> Iterable[Tuple[str, str]]:
    """深度遍历 JSON，产出 (path, string_value) 对，便于后续定位证据来源。"""
    if isinstance(node, str):
        if node.strip():
            yield (path or "$", node)
    elif isinstance(node, list):
        for i, x in enumerate(node):
            yield from _iter_string_with_path(x, f"{path}[{i}]")
    elif isinstance(node, dict):
        for k, v in node.items():
            sub = f"{path}.{k}" if path else k
            yield from _iter_string_with_path(v, sub)


# ----------------------------------------------------------------------
# 主校验入口
# ----------------------------------------------------------------------
def check_novel_canon(
    novel_id: str,
    characters: Dict[str, Any],
    storyline: Dict[str, Any],
    *,
    novel_dir: str = "",
) -> CanonReport:
    """对一本小说的两份"圣经"做一致性校验，返回结构化报告。"""
    issues: List[CanonIssue] = []

    main_char = (characters or {}).get("main_character") or {}
    supporting = (characters or {}).get("supporting_characters") or []

    main_name = ((main_char.get("basic_info") or {}).get("name") or "").strip() \
                or (main_char.get("name") or "").strip()
    supporting_entries: List[Dict[str, Any]] = []
    for sc in supporting:
        nm = ((sc.get("basic_info") or {}).get("name") or "").strip() \
             or (sc.get("name") or "").strip()
        if nm:
            supporting_entries.append({
                "name": nm,
                "role": sc.get("role") or "",
                "gender": (sc.get("basic_info") or {}).get("gender") or "",
                "occupation": (sc.get("basic_info") or {}).get("occupation") or "",
                "raw": sc,
            })
    supporting_names = [s["name"] for s in supporting_entries]
    all_registered = set(supporting_names) | ({main_name} if main_name else set())

    storyline_text = _flatten_to_text(storyline)
    storyline_strings = list(_iter_string_with_path(storyline))

    # ============== R001: 主角必须出现在 storyline ==============
    if main_name:
        if main_name not in storyline_text:
            issues.append(CanonIssue(
                rule_id="R001",
                severity="ERROR",
                title="主角姓名未在故事大纲中出现",
                detail=f"主角『{main_name}』在 characters.json 中注册，"
                       f"但在 storyline.json 全文中一次都没有出现。",
                subject=main_name,
                suggestions=["检查 storyline 是否使用了主角的别名或错误姓名",
                             "或在 storyline.overall_storyline 中显式提及主角"],
            ))
    else:
        issues.append(CanonIssue(
            rule_id="R001",
            severity="ERROR",
            title="characters.json 中缺少主角姓名",
            detail="main_character.basic_info.name 为空。",
            subject="<main_character>",
        ))

    # ============== R002: 同名重复注册 ==============
    name_to_slots: Dict[str, List[str]] = {}
    if main_name:
        name_to_slots.setdefault(main_name, []).append("main_character")
    for s in supporting_entries:
        name_to_slots.setdefault(s["name"], []).append(f"supporting:{s['role'] or '?'}")
    for nm, slots in name_to_slots.items():
        if len(slots) > 1:
            issues.append(CanonIssue(
                rule_id="R002",
                severity="ERROR",
                title="同名角色被重复注册",
                detail=f"姓名『{nm}』在 characters.json 中出现于多个槽位：{slots}",
                subject=nm,
                suggestions=["合并重复条目，或为其中一个换名"],
            ))

    # ============== R003: 配角是否在 storyline 中亮过相 ==============
    for s in supporting_entries:
        if s["name"] not in storyline_text:
            issues.append(CanonIssue(
                rule_id="R003",
                severity="INFO",
                title="配角姓名未出现在故事大纲中",
                detail=f"配角『{s['name']}』（role={s['role'] or '未注明'}）"
                       f"在 storyline.json 中一次都没有出现。",
                subject=s["name"],
                suggestions=["确认该角色是否仍属于本作主线，否则可考虑从档案中移除",
                             "或在 storyline 中补充其登场说明"],
            ))

    # ============== R004: 性别代词一致性 ==============
    def _check_gender(name: str, declared_gender: str) -> Optional[CanonIssue]:
        if not name or not declared_gender or name not in storyline_text:
            return None
        male_hits = 0
        female_hits = 0
        evidences: List[str] = []
        for path, text in storyline_strings:
            if name not in text:
                continue
            # 取 name 周围窗口
            for m in re.finditer(re.escape(name), text):
                left = max(0, m.start() - 30)
                right = min(len(text), m.end() + 30)
                window = text[left:right]
                m_male = sum(window.count(p) for p in _PRONOUN_MALE)
                m_female = sum(window.count(p) for p in _PRONOUN_FEMALE)
                male_hits += m_male
                female_hits += m_female
                if m_male or m_female:
                    evidences.append(f"[{path}] …{window}…")
        if not (male_hits or female_hits):
            return None
        is_male_declared = "男" in declared_gender
        is_female_declared = "女" in declared_gender
        if is_male_declared and female_hits > male_hits and female_hits >= 2:
            return CanonIssue(
                rule_id="R004", severity="WARNING",
                title="性别代词与档案不一致",
                detail=f"『{name}』在 characters.json 注明性别为『{declared_gender}』，"
                       f"但在 storyline 中附近窗口出现『她』×{female_hits} > 『他』×{male_hits}",
                subject=name,
                suggestions=["核对该角色真实性别", "若性别正确请检查 storyline 中代词错误"],
                evidence=evidences[:3],
            )
        if is_female_declared and male_hits > female_hits and male_hits >= 2:
            return CanonIssue(
                rule_id="R004", severity="WARNING",
                title="性别代词与档案不一致",
                detail=f"『{name}』在 characters.json 注明性别为『{declared_gender}』，"
                       f"但在 storyline 中附近窗口出现『他』×{male_hits} > 『她』×{female_hits}",
                subject=name,
                suggestions=["核对该角色真实性别", "若性别正确请检查 storyline 中代词错误"],
                evidence=evidences[:3],
            )
        return None

    if main_name:
        gender_main = (main_char.get("basic_info") or {}).get("gender") or ""
        iss = _check_gender(main_name, gender_main)
        if iss:
            issues.append(iss)
    for s in supporting_entries:
        iss = _check_gender(s["name"], s["gender"])
        if iss:
            issues.append(iss)

    # ============== R005: storyline 中"角色标签+人名"未注册 ==============
    # 用通用模式扫描，提取被冠以角色标签的姓名，与已注册名做差集。
    storyline_named_unregistered: List[str] = []
    seen_unreg: Dict[str, List[str]] = {}

    label_alt = "|".join(re.escape(t) for t in ROLE_LABEL_TOKENS)

    # 主匹配模式：标签 + 紧随的最多 4 字汉字串；具体是不是真人名，交给 _refine_name 决定
    pat_label_then_chunk = re.compile(
        rf"(?P<label>{label_alt})(?P<chunk>[\u4e00-\u9fa5]{{1,5}})"
    )
    # 反向模式：人名（标签）；这里必须由括号兜底，所以 chunk 边界很安全
    pat_chunk_then_label_paren = re.compile(
        rf"(?P<chunk>[\u4e00-\u9fa5]{{2,4}})[（(](?P<label>{label_alt})"
    )

    def _refine_name(chunk: str, full_text: str, chunk_end_in_text: int) -> Optional[str]:
        """
        从一个汉字串中切出"看起来像人名"的部分，若不像人名则返回 None。
        策略：
          1. 第一个字必须是常见姓氏（含复姓，最长 2 字）
          2. 名字总长 2-4 字
          3. 名字最后一字不能是虚词，名字内部不能命中常见动词/名词词根字
          4. 名字之后在原文中必须紧接"切断字符"（标点/空白/常用动词字/虚词等）
             —— 否则视为名字粘在了下文动词里，舍弃
        """
        if not chunk:
            return None
        # 切出最长合法人名候选
        # 先尝试复姓（2 字），再尝试单姓
        for surname_len in (2, 1):
            if len(chunk) < surname_len:
                continue
            surname = chunk[:surname_len]
            if surname not in COMMON_SURNAMES:
                continue
            # 候选长度从最长到最短逐一尝试
            for total_len in range(min(4, len(chunk)), max(surname_len, 1), -1):
                cand = chunk[:total_len]
                if len(cand) < 2:
                    continue
                if cand in _NON_NAME_PHRASES:
                    continue
                tail = cand[-1]
                if tail in _NAME_TAIL_BLACKLIST:
                    continue
                # 名字内部任何一字不能命中明显动词/名词词根
                given_part = cand[surname_len:]
                if any(ch in _NAME_BODY_BLACKLIST for ch in given_part):
                    continue
                # 检查原文中名字之后的边界字符
                cand_end = chunk_end_in_text - len(chunk) + total_len
                next_ch = full_text[cand_end] if cand_end < len(full_text) else ""
                if next_ch == "":
                    return cand
                # 切断字符白名单：标点 + 常见连接字 + 任何非汉字（数字/字母/空白）
                CUT_CHARS = "，。、；：！？\"\"''《》()（）【】[]{}<>「」 \t\r\n"
                CONNECT_CHARS = (
                    "的之于以为与和及或在把被让使将向往从到对并也都就还又再便却已"
                    "了过着得是非有无的话则即然而但因所故而是不"
                )
                if next_ch in CUT_CHARS:
                    return cand
                if next_ch in CONNECT_CHARS:
                    return cand
                if not ('\u4e00' <= next_ch <= '\u9fa5'):
                    return cand
                # 否则名字粘上了下文动词，继续尝试更短的候选
                continue
        return None

    for path, text in storyline_strings:
        for m in pat_label_then_chunk.finditer(text):
            chunk = m.group("chunk")
            label = m.group("label")
            chunk_end = m.end("chunk")
            nm = _refine_name(chunk, text, chunk_end)
            if not nm:
                continue
            if nm in all_registered:
                continue
            seen_unreg.setdefault(nm, []).append(f"[{label}] {path}")
        for m in pat_chunk_then_label_paren.finditer(text):
            chunk = m.group("chunk")
            label = m.group("label")
            chunk_end = m.end("chunk")
            nm = _refine_name(chunk, text, chunk_end)
            if not nm:
                continue
            if nm in all_registered:
                continue
            seen_unreg.setdefault(nm, []).append(f"[{label}] {path}")

    for nm, evs in seen_unreg.items():
        evs = list(dict.fromkeys(evs))[:5]
        storyline_named_unregistered.append(nm)
        issues.append(CanonIssue(
            rule_id="R005",
            severity="ERROR",
            title="故事大纲中出现未注册的具名角色",
            detail=f"姓名『{nm}』在 storyline 中以角色标签形式出现 {len(evs)} 处，"
                   f"但 characters.json 中没有该角色档案。",
            subject=nm,
            suggestions=[f"在 characters.json 的 supporting_characters 中补全『{nm}』的档案",
                         "或修改 storyline 中的称谓，使其指向已注册角色"],
            evidence=evs,
        ))

    # ============== R006: 同一注册名在 storyline 中被赋予互斥角色标签 ==============
    # 对每个已注册名，扫所有"角色标签 + 该名"的出现，统计落入了多少个互斥组。
    for nm in all_registered:
        if not nm:
            continue
        labels_hit: List[str] = []
        for path, text in storyline_strings:
            for m in pat_label_then_chunk.finditer(text):
                refined = _refine_name(m.group("chunk"), text, m.end("chunk"))
                if refined == nm:
                    labels_hit.append(m.group("label"))
            for m in pat_chunk_then_label_paren.finditer(text):
                refined = _refine_name(m.group("chunk"), text, m.end("chunk"))
                if refined == nm:
                    labels_hit.append(m.group("label"))
        if not labels_hit:
            continue
        groups_hit: List[Tuple[str, ...]] = []
        for grp in ROLE_EXCLUSIVE_GROUPS:
            if any(lbl in grp for lbl in labels_hit):
                groups_hit.append(grp)
        if len(groups_hit) >= 2:
            uniq_labels = list(dict.fromkeys(labels_hit))
            issues.append(CanonIssue(
                rule_id="R006",
                severity="ERROR",
                title="同一角色在故事大纲中被赋予互斥的多重身份",
                detail=f"『{nm}』在 storyline 中同时被冠以以下互斥标签：{uniq_labels}。"
                       f"通常这意味着两份档案对该角色的设定相互打架。",
                subject=nm,
                suggestions=["在 storyline 中统一其角色身份，仅保留一种主身份",
                             "若确为身份反转剧情，请在 characters.json 中明确标注双重身份"],
            ))

    # ============== 汇总 ==============
    summary = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for i in issues:
        summary[i.severity] = summary.get(i.severity, 0) + 1

    return CanonReport(
        novel_id=novel_id,
        novel_dir=novel_dir,
        summary=summary,
        issues=issues,
        registered_main=main_name or None,
        registered_supporting=supporting_names,
        storyline_named_unregistered=sorted(set(storyline_named_unregistered)),
    )


# ----------------------------------------------------------------------
# 终端友好渲染
# ----------------------------------------------------------------------
def render_report_text(report: CanonReport) -> str:
    lines: List[str] = []
    lines.append("=" * 68)
    lines.append(f"档案一致性校验报告  novel_id={report.novel_id}")
    lines.append("-" * 68)
    lines.append(f"主角：{report.registered_main or '<缺失>'}")
    lines.append(f"配角：{', '.join(report.registered_supporting) or '<空>'}")
    s = report.summary
    lines.append(f"汇总：ERROR={s.get('ERROR', 0)}  WARNING={s.get('WARNING', 0)}  INFO={s.get('INFO', 0)}")
    if report.storyline_named_unregistered:
        lines.append(
            f"未注册具名角色：{', '.join(report.storyline_named_unregistered)}"
        )
    lines.append("=" * 68)
    if not report.issues:
        lines.append("[OK] 未发现一致性问题。")
        return "\n".join(lines)
    sev_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    sorted_issues = sorted(report.issues, key=lambda x: (sev_order.get(x.severity, 9), x.rule_id))
    for i, iss in enumerate(sorted_issues, 1):
        lines.append(f"\n#{i:02d} [{iss.severity}] [{iss.rule_id}] {iss.title}")
        if iss.subject:
            lines.append(f"   主体：{iss.subject}")
        lines.append(f"   {iss.detail}")
        if iss.suggestions:
            for sug in iss.suggestions:
                lines.append(f"   - 建议：{sug}")
        if iss.evidence:
            for ev in iss.evidence:
                short = ev if len(ev) <= 120 else ev[:117] + "..."
                lines.append(f"   - 证据：{short}")
    lines.append("\n" + "=" * 68)
    return "\n".join(lines)


def load_and_check(novel_dir: str, novel_id: Optional[str] = None) -> CanonReport:
    """从磁盘加载一本小说的 characters.json 与 storyline.json，做一次校验。"""
    if not os.path.isdir(novel_dir):
        raise FileNotFoundError(f"novel_dir 不存在：{novel_dir}")
    novel_id = novel_id or os.path.basename(os.path.normpath(novel_dir))
    chars_path = os.path.join(novel_dir, "characters.json")
    story_path = os.path.join(novel_dir, "storyline.json")
    characters: Dict[str, Any] = {}
    storyline: Dict[str, Any] = {}
    if os.path.isfile(chars_path):
        with open(chars_path, "r", encoding="utf-8") as f:
            characters = json.load(f) or {}
    if os.path.isfile(story_path):
        with open(story_path, "r", encoding="utf-8") as f:
            storyline = json.load(f) or {}
    return check_novel_canon(novel_id, characters, storyline, novel_dir=novel_dir)
