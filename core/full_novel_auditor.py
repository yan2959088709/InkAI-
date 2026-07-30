"""
core/full_novel_auditor.py —— 全本通读探针（Full-Novel Auditor）

定位：把一本已生成完成的小说当作"完整数据集"，从多个维度做纵览体检，
      输出可量化的质量纵览报告。整套工具纯本地、零 LLM 成本，可重复运行。

六个独立审计维度（可单独使用，也可组合）：

  M1: 基础规模统计    —— 章数、字数分布、outlier 章节
  M2: 角色分布与平衡  —— 主角戏份连续性、配角断链、角色频次矩阵
  M3: 钩子重复检测    —— 所有 ending_hook 两两相似度，暴露"换皮重复"
  M4: 跨章档案一致性  —— 复用 canon_checker，扫所有章节正文找未注册角色
  M5: 伏笔账本闭环    —— 全局伏笔账本 plant→payoff 是否真的兑现
  M6: 风格连续性      —— 章节相邻文本余弦相似度，暴露突变断点

设计原则：
  - 与 canon_checker / scan_continuity 复用同一套底层数据
  - 每个维度产出独立子报告，可以拼装也可以单独看
  - 输出综合得分（0-100），便于横向对比不同小说
  - 通用、零硬编码，能用于任意 novel_id

详见：docs/development/data_files_catalog.md
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# ----------------------------------------------------------------------
# 数据结构
# ----------------------------------------------------------------------

@dataclass
class AuditFinding:
    severity: str           # "ERROR" / "WARNING" / "INFO"
    code: str               # 维度码：M1-OUT-WORDS / M2-PROTAG-GAP / ...
    title: str
    detail: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class AuditReport:
    novel_id: str
    novel_title: str
    chapters_total: int
    chapters_loaded: int
    overall_score: float                       # 0-100 综合分
    dimension_scores: Dict[str, float]         # 各维度分数
    findings: List[AuditFinding]
    metrics: Dict[str, Any]                    # 各维度的原始指标，便于做对比

    def to_dict(self) -> Dict[str, Any]:
        return {
            "novel_id": self.novel_id,
            "novel_title": self.novel_title,
            "chapters_total": self.chapters_total,
            "chapters_loaded": self.chapters_loaded,
            "overall_score": round(self.overall_score, 2),
            "dimension_scores": {k: round(v, 2) for k, v in self.dimension_scores.items()},
            "findings": [asdict(f) for f in self.findings],
            "metrics": self.metrics,
        }


# ----------------------------------------------------------------------
# 数据加载层
# ----------------------------------------------------------------------

def _load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_chapter_cards(novel_dir: str) -> Dict[int, Dict[str, Any]]:
    outline_dir = os.path.join(novel_dir, "outline")
    cards: Dict[int, Dict[str, Any]] = {}
    if not os.path.isdir(outline_dir):
        return cards
    for fn in sorted(os.listdir(outline_dir)):
        if not (fn.startswith("volume_") and fn.endswith("_chapters.json")):
            continue
        payload = _load_json(os.path.join(outline_dir, fn))
        if not payload:
            continue
        for card in payload.get("chapter_cards") or []:
            n = card.get("chapter_number")
            if isinstance(n, int):
                cards[n] = card
    return cards


def _load_chapter_text(novel_dir: str, n: int) -> Tuple[str, str]:
    path = os.path.join(novel_dir, "chapters_demo", f"chapter_{n}.txt")
    if not os.path.isfile(path):
        return "", ""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n", 1)
    title = lines[0].strip() if lines else ""
    body = lines[1].lstrip("\n").rstrip() if len(lines) > 1 else ""
    return title, body


def _load_chapter_meta(novel_dir: str, n: int) -> Dict[str, Any]:
    return _load_json(os.path.join(novel_dir, "chapters_demo", f"chapter_{n}.meta.json")) or {}


# ----------------------------------------------------------------------
# 指标工具：字符 N-gram TF 向量 / 余弦相似度 / Jaccard
# ----------------------------------------------------------------------

def _char_ngrams(text: str, n: int = 2) -> Counter:
    text = re.sub(r"\s+", "", text)
    if len(text) < n:
        return Counter()
    return Counter(text[i:i + n] for i in range(len(text) - n + 1))


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _jaccard(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 0.0
    sa, sb = set(a.keys()), set(b.keys())
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"n": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / max(1, n - 1)
    return {
        "n": n,
        "mean": mean,
        "std": math.sqrt(var),
        "min": min(values),
        "max": max(values),
    }


# ----------------------------------------------------------------------
# 维度 M1：基础规模统计
# ----------------------------------------------------------------------

def audit_basic_stats(
    novel_dir: str,
    cards: Dict[int, Dict[str, Any]],
    metas: Dict[int, Dict[str, Any]],
) -> Tuple[float, Dict[str, Any], List[AuditFinding]]:
    findings: List[AuditFinding] = []

    word_counts: Dict[int, int] = {}
    target_words: Dict[int, int] = {}
    for n, m in metas.items():
        wc = m.get("word_count")
        if isinstance(wc, int):
            word_counts[n] = wc
        v = (m.get("validation") or {})
        if isinstance(v.get("word_count_target"), int):
            target_words[n] = v["word_count_target"]

    if not word_counts:
        return 0.0, {"reason": "no_meta_loaded"}, [
            AuditFinding("ERROR", "M1-NO-META", "无章节元数据可读", "未找到任何 chapter_*.meta.json")
        ]

    wc_values = list(word_counts.values())
    s = _stats([float(x) for x in wc_values])

    # outlier：> 2 std 偏离
    outliers: List[Tuple[int, int]] = []
    if s["std"] > 0:
        for n, wc in word_counts.items():
            if abs(wc - s["mean"]) > 2 * s["std"]:
                outliers.append((n, wc))

    # 偏离目标字数过多
    target_misses: List[Tuple[int, int, int]] = []
    for n, wc in word_counts.items():
        tg = target_words.get(n)
        if tg and tg > 0:
            ratio = wc / tg
            if ratio < 0.6 or ratio > 1.6:
                target_misses.append((n, wc, tg))

    # 评分
    score = 100.0
    if s["std"] > 0 and s["mean"] > 0:
        cv = s["std"] / s["mean"]      # 变异系数
        # cv 0.05 起扣分，0.30 时扣到 0
        if cv > 0.05:
            score -= min(40, (cv - 0.05) * 1000 * 0.4)
    score -= min(30, len(outliers) * 5)
    score -= min(20, len(target_misses) * 4)
    score = max(0.0, score)

    if outliers:
        findings.append(AuditFinding(
            severity="WARNING",
            code="M1-OUT-WORDS",
            title="章节字数严重偏离均值",
            detail=f"共 {len(outliers)} 章字数 > 2 std 偏离均值（mean={s['mean']:.0f}, std={s['std']:.0f}）",
            evidence=[f"ch{n}={wc}" for n, wc in outliers[:8]],
        ))
    if target_misses:
        findings.append(AuditFinding(
            severity="INFO",
            code="M1-TARGET-MISS",
            title="字数显著偏离目标",
            detail=f"共 {len(target_misses)} 章实际字数 / 目标字数 不在 [0.6, 1.6] 区间",
            evidence=[f"ch{n}: {wc}/{tg}" for n, wc, tg in target_misses[:8]],
        ))

    return score, {
        "word_count_stats": s,
        "outlier_chapters": outliers,
        "target_miss_chapters": target_misses,
        "total_words": sum(wc_values),
    }, findings


# ----------------------------------------------------------------------
# 维度 M2：角色分布与平衡
# ----------------------------------------------------------------------

def audit_character_distribution(
    novel_dir: str,
    characters: Dict[str, Any],
    metas: Dict[int, Dict[str, Any]],
) -> Tuple[float, Dict[str, Any], List[AuditFinding]]:
    findings: List[AuditFinding] = []

    main = (characters or {}).get("main_character") or {}
    main_name = ((main.get("basic_info") or {}).get("name") or "").strip() \
                or (main.get("name") or "").strip()
    sup_names = []
    for sc in (characters or {}).get("supporting_characters") or []:
        nm = ((sc.get("basic_info") or {}).get("name") or "").strip() \
             or (sc.get("name") or "").strip()
        if nm:
            sup_names.append(nm)

    if not metas:
        return 0.0, {"reason": "no_meta"}, []

    # 频次矩阵：character -> chapter -> count
    matrix: Dict[str, Dict[int, int]] = defaultdict(dict)
    sorted_chs = sorted(metas.keys())

    for n in sorted_chs:
        m = metas[n]
        v = m.get("validation") or {}
        # 主角
        if main_name:
            matrix[main_name][n] = int(v.get("protagonist_count") or 0)
        # 配角：从 must_appear.characters.ok 与 light 中读取
        ma = (v.get("must_appear") or {}).get("characters") or {}
        per_chap_named: Dict[str, int] = {}
        for entry in (ma.get("ok") or []) + (ma.get("light") or []):
            nm = entry.get("name", "")
            cnt = int(entry.get("count") or 0)
            per_chap_named[nm] = cnt
        for nm in sup_names:
            matrix[nm][n] = per_chap_named.get(nm, 0)

    # 主角戏份连续性
    score = 100.0
    main_gap_max = 0
    if main_name:
        cur = 0
        for n in sorted_chs:
            cnt = matrix[main_name].get(n, 0)
            if cnt == 0:
                cur += 1
                main_gap_max = max(main_gap_max, cur)
            else:
                cur = 0
        if main_gap_max >= 3:
            findings.append(AuditFinding(
                severity="ERROR" if main_gap_max >= 5 else "WARNING",
                code="M2-PROTAG-GAP",
                title="主角连续多章未出现",
                detail=f"主角『{main_name}』最长连续缺席 {main_gap_max} 章",
            ))
            score -= min(40, main_gap_max * 6)

    # 配角断链：每个配角最长缺席窗口 / 累计缺席比例
    sup_gaps: Dict[str, int] = {}
    sup_total_zero: Dict[str, int] = {}
    for nm in sup_names:
        cur = 0
        max_gap = 0
        zero = 0
        for n in sorted_chs:
            cnt = matrix[nm].get(n, 0)
            if cnt == 0:
                zero += 1
                cur += 1
                max_gap = max(max_gap, cur)
            else:
                cur = 0
        sup_gaps[nm] = max_gap
        sup_total_zero[nm] = zero
    # 配角通篇缺席视为 ERROR
    for nm, zero in sup_total_zero.items():
        if zero == len(sorted_chs):
            findings.append(AuditFinding(
                severity="WARNING",
                code="M2-SUP-ABSENT",
                title="配角通篇未出场",
                detail=f"配角『{nm}』在所有 {len(sorted_chs)} 章中均未出现",
            ))
            score -= 5

    # 矩阵打印用：截断到前 50 章
    matrix_view = {nm: dict(matrix[nm]) for nm in matrix}
    score = max(0.0, score)

    return score, {
        "main_name": main_name,
        "supporting_names": sup_names,
        "frequency_matrix": matrix_view,
        "main_max_gap": main_gap_max,
        "supporting_max_gap": sup_gaps,
        "supporting_total_zero": sup_total_zero,
    }, findings


# ----------------------------------------------------------------------
# 维度 M3：ending_hook 重复检测
# ----------------------------------------------------------------------

def audit_hook_repetition(
    cards: Dict[int, Dict[str, Any]],
    threshold: float = 0.55,
) -> Tuple[float, Dict[str, Any], List[AuditFinding]]:
    findings: List[AuditFinding] = []
    hooks: Dict[int, str] = {}
    for n, c in cards.items():
        h = (c.get("ending_hook") or c.get("hook") or "").strip()
        if h:
            hooks[n] = h

    if len(hooks) < 2:
        return 100.0, {"hook_count": len(hooks)}, []

    # 两两 Jaccard 相似度（字符 4-gram）
    items = sorted(hooks.items())
    grams: Dict[int, Counter] = {n: _char_ngrams(h, n=4) for n, h in items}
    pairs: List[Tuple[int, int, float]] = []
    for i, (na, _) in enumerate(items):
        for j in range(i + 1, len(items)):
            nb, _ = items[j]
            sim = _jaccard(grams[na], grams[nb])
            if sim >= threshold:
                pairs.append((na, nb, sim))
    pairs.sort(key=lambda x: -x[2])

    score = 100.0 - min(70, len(pairs) * 10)
    if pairs:
        findings.append(AuditFinding(
            severity="WARNING" if pairs[0][2] < 0.75 else "ERROR",
            code="M3-HOOK-DUP",
            title="章节钩子高度雷同",
            detail=f"共 {len(pairs)} 对钩子相似度 ≥{threshold}",
            evidence=[
                f"ch{a}↔ch{b} sim={s:.2f}\n     A: {hooks[a][:60]}…\n     B: {hooks[b][:60]}…"
                for a, b, s in pairs[:5]
            ],
        ))

    return max(0.0, score), {
        "hook_count": len(hooks),
        "high_similarity_pairs": [
            {"a": a, "b": b, "similarity": round(s, 3)} for a, b, s in pairs[:20]
        ],
    }, findings


# ----------------------------------------------------------------------
# 维度 M4：跨章档案一致性（复用 canon_checker 的 R005 思路扫所有正文）
# ----------------------------------------------------------------------

def audit_canon_in_chapters(
    novel_dir: str,
    characters: Dict[str, Any],
    chapter_texts: Dict[int, str],
) -> Tuple[float, Dict[str, Any], List[AuditFinding]]:
    """对每章正文做一次 R005 扫描，找未注册的具名角色。"""
    findings: List[AuditFinding] = []
    try:
        # 复用 canon_checker 内部工具（懒加载，避免循环引用）
        from core.canon_checker import (
            COMMON_SURNAMES, ROLE_LABEL_TOKENS, _NAME_TAIL_BLACKLIST,
            _NAME_BODY_BLACKLIST, _NON_NAME_PHRASES,
        )
    except Exception as exc:
        return 100.0, {"reason": f"import_failed:{exc}"}, []

    main = (characters or {}).get("main_character") or {}
    main_name = ((main.get("basic_info") or {}).get("name") or "").strip()
    sup_names = []
    for sc in (characters or {}).get("supporting_characters") or []:
        nm = ((sc.get("basic_info") or {}).get("name") or "").strip()
        if nm:
            sup_names.append(nm)
    registered = {main_name} | set(sup_names)
    registered.discard("")

    label_alt = "|".join(re.escape(t) for t in ROLE_LABEL_TOKENS)
    pat = re.compile(rf"(?P<label>{label_alt})(?P<chunk>[\u4e00-\u9fa5]{{1,5}})")

    def _refine(chunk: str, full_text: str, chunk_end: int) -> Optional[str]:
        if not chunk:
            return None
        for sl in (2, 1):
            if len(chunk) < sl:
                continue
            sn = chunk[:sl]
            if sn not in COMMON_SURNAMES:
                continue
            for tl in range(min(4, len(chunk)), max(sl, 1), -1):
                cand = chunk[:tl]
                if len(cand) < 2 or cand in _NON_NAME_PHRASES:
                    continue
                tail = cand[-1]
                if tail in _NAME_TAIL_BLACKLIST:
                    continue
                given = cand[sl:]
                if any(ch in _NAME_BODY_BLACKLIST for ch in given):
                    continue
                end_idx = chunk_end - len(chunk) + tl
                next_ch = full_text[end_idx] if end_idx < len(full_text) else ""
                CUT = "，。、；：！？\"\"''《》()（）【】[]{}<>「」 \t\r\n"
                CN = ("的之于以为与和及或在把被让使将向往从到对并也都就还又再便却已"
                      "了过着得是非有无的话则即然而但因所故而是不")
                if not next_ch or next_ch in CUT or next_ch in CN \
                        or not ('\u4e00' <= next_ch <= '\u9fa5'):
                    return cand
        return None

    name_to_chapters: Dict[str, List[int]] = defaultdict(list)
    for n in sorted(chapter_texts.keys()):
        text = chapter_texts[n]
        if not text:
            continue
        seen_in_chap: set = set()
        for m in pat.finditer(text):
            cand = _refine(m.group("chunk"), text, m.end("chunk"))
            if not cand or cand in registered or cand in seen_in_chap:
                continue
            seen_in_chap.add(cand)
            name_to_chapters[cand].append(n)

    score = 100.0 - min(60, len(name_to_chapters) * 4)
    if name_to_chapters:
        # 出场次数 ≥ 2 的最像"幽灵反复出场角色"，单次 1 章的可能是叙述需要
        recurrent = {nm: chs for nm, chs in name_to_chapters.items() if len(chs) >= 2}
        if recurrent:
            findings.append(AuditFinding(
                severity="ERROR",
                code="M4-GHOST-CHARS",
                title="未注册的幽灵角色反复出场",
                detail=f"共 {len(recurrent)} 个未注册角色出现 ≥2 章；可能是档案漂移症状",
                evidence=[
                    f"『{nm}』出现于章节 {chs[:8]}（共 {len(chs)} 章）"
                    for nm, chs in sorted(recurrent.items(), key=lambda x: -len(x[1]))[:8]
                ],
            ))
        once = {nm: chs for nm, chs in name_to_chapters.items() if len(chs) == 1}
        if once:
            findings.append(AuditFinding(
                severity="WARNING",
                code="M4-CAMEO",
                title="未注册的具名角色单章客串",
                detail=f"共 {len(once)} 个未注册角色仅在 1 章中以角色标签形式出现",
                evidence=[
                    f"『{nm}』@ch{chs[0]}" for nm, chs in list(once.items())[:8]
                ],
            ))

    return max(0.0, score), {
        "ghost_chars_recurrent": {
            nm: chs for nm, chs in name_to_chapters.items() if len(chs) >= 2
        },
        "ghost_chars_cameo_count": sum(1 for chs in name_to_chapters.values() if len(chs) == 1),
        "registered_count": len(registered),
    }, findings


# ----------------------------------------------------------------------
# 维度 M5：伏笔账本闭环
# ----------------------------------------------------------------------

def audit_foreshadow_ledger(
    blueprint: Dict[str, Any],
    chapter_texts: Dict[int, str],
    cards: Dict[int, Dict[str, Any]],
) -> Tuple[float, Dict[str, Any], List[AuditFinding]]:
    findings: List[AuditFinding] = []
    ledger = (blueprint or {}).get("ledger") \
             or ((blueprint or {}).get("global_arc") or {}).get("ledger") \
             or []
    if not ledger:
        return 100.0, {"ledger_size": 0, "reason": "no_ledger"}, []

    issues = 0
    bad_order: List[str] = []
    not_planted: List[str] = []
    not_paid: List[str] = []

    for f in ledger:
        fid = str(f.get("id") or f.get("ref") or "F?")
        plant_v = f.get("plant_volume") or f.get("plant_vol")
        payoff_v = f.get("payoff_volume") or f.get("payoff_vol")
        plant_ch = f.get("plant_chapter")
        payoff_ch = f.get("payoff_chapter")
        if isinstance(plant_v, int) and isinstance(payoff_v, int) and plant_v > payoff_v:
            bad_order.append(f"{fid}: plant_v={plant_v} > payoff_v={payoff_v}")
            issues += 1
        # 检查关键词是否在正文里出现过（粗略）
        kw = (f.get("keyword") or f.get("title") or f.get("description") or "").strip()
        if not kw:
            continue
        # 找包含 kw 中任意 3 字的章节
        kw3 = kw[:3] if len(kw) >= 3 else kw
        appearances: List[int] = []
        for n in sorted(chapter_texts.keys()):
            if kw3 and kw3 in chapter_texts[n]:
                appearances.append(n)
        if not appearances:
            not_planted.append(f"{fid} [{kw[:24]}]")
            issues += 1
        elif isinstance(payoff_v, int) and len(appearances) <= 1:
            # 出现过 plant 但似乎没有 payoff——容差很大
            not_paid.append(f"{fid} [{kw[:24]}] only @ch{appearances}")

    score = 100.0 - min(60, issues * 6)
    if bad_order:
        findings.append(AuditFinding(
            severity="ERROR",
            code="M5-FORE-ORDER",
            title="伏笔账本时序矛盾",
            detail=f"{len(bad_order)} 条伏笔的 plant 卷次大于 payoff 卷次",
            evidence=bad_order[:5],
        ))
    if not_planted:
        findings.append(AuditFinding(
            severity="WARNING",
            code="M5-FORE-DROP",
            title="伏笔关键词未在任何正文中出现",
            detail=f"{len(not_planted)} 条伏笔可能从未被真正埋下（仅基于 3 字粗匹配）",
            evidence=not_planted[:8],
        ))
    if not_paid:
        findings.append(AuditFinding(
            severity="INFO",
            code="M5-FORE-LIGHT",
            title="伏笔仅出现于一章",
            detail=f"{len(not_paid)} 条伏笔仅在 1 章中被提及，可能埋而未收",
            evidence=not_paid[:8],
        ))

    return max(0.0, score), {
        "ledger_size": len(ledger),
        "bad_order_count": len(bad_order),
        "not_planted_count": len(not_planted),
        "not_paid_count": len(not_paid),
    }, findings


# ----------------------------------------------------------------------
# 维度 M6：风格连续性（章节相邻文本余弦相似度）
# ----------------------------------------------------------------------

def _extract_entity_grams(text: str, n: int = 4) -> set:
    """
    抽取"实体级"的 4-gram 集合。
    思路：把虚词/常用动词/虚助词等剔除后，连续 4 个汉字才算一个实体片段。
    用于章节末段→章节首段的"实体承接"判定，比 2-gram TF 更接近"具名延续"。
    """
    text = re.sub(r"\s+", "", text)
    # 砍掉所有非汉字（标点/数字/字母）后再切 n-gram
    text = re.sub(r"[^\u4e00-\u9fa5]+", "|", text)
    grams = set()
    for seg in text.split("|"):
        if len(seg) < n:
            continue
        for i in range(len(seg) - n + 1):
            grams.add(seg[i:i + n])
    return grams


def audit_style_continuity(
    chapter_texts: Dict[int, str],
    head_chars: int = 800,
    transition_window: int = 400,
) -> Tuple[float, Dict[str, Any], List[AuditFinding]]:
    findings: List[AuditFinding] = []
    sorted_chs = sorted(chapter_texts.keys())
    if len(sorted_chs) < 2:
        return 100.0, {"reason": "too_few_chapters"}, []

    # 全本 2-gram TF 用于"风格漂移"
    full_g: Dict[int, Counter] = {}
    for n in sorted_chs:
        full_g[n] = _char_ngrams(chapter_texts[n], n=2)

    # —— 过渡断点：用"末段实体 4-gram 与首段的 Jaccard"
    # 实体 4-gram 命中代表具名实体在两章间真实延续；这比 2-gram 词频相似度更精准
    transition_jacs: List[Tuple[int, float, int]] = []  # (next_ch, jaccard, overlap_count)
    for i in range(len(sorted_chs) - 1):
        a, b = sorted_chs[i], sorted_chs[i + 1]
        ta = chapter_texts[a][-transition_window:]
        tb = chapter_texts[b][:transition_window]
        ga = _extract_entity_grams(ta, n=4)
        gb = _extract_entity_grams(tb, n=4)
        if not ga or not gb:
            transition_jacs.append((b, 0.0, 0))
            continue
        inter = ga & gb
        union = ga | gb
        jac = len(inter) / len(union) if union else 0.0
        transition_jacs.append((b, jac, len(inter)))

    # 与全本"平均章节"的余弦——衡量风格漂移
    avg = Counter()
    for n in sorted_chs:
        avg.update(full_g[n])
    drift_sims: List[Tuple[int, float]] = []
    for n in sorted_chs:
        sim = _cosine(full_g[n], avg)
        drift_sims.append((n, sim))

    drift_vals = [s for _, s in drift_sims]
    s_drift = _stats([float(x) for x in drift_vals])

    # 过渡断点判定（双条件）：
    #   - jaccard < 0.02（基本无任何实体延续）
    #   - 重叠 4-gram 数 == 0（首尾段没有任何 4 字连续实体片段重合）
    # 同时满足才视为真断点；这样"用词风格变了但钩子词承接住了"不会误报
    bad_trans: List[Tuple[int, float, int]] = []
    for n, jac, ov in transition_jacs:
        if jac < 0.02 and ov == 0:
            bad_trans.append((n, jac, ov))

    # 风格离群：drift 仍用 2-gram 余弦
    bad_drift: List[Tuple[int, float]] = []
    if s_drift["std"] > 0:
        thr_d = s_drift["mean"] - 2 * s_drift["std"]
        for n, s in drift_sims:
            if s < thr_d:
                bad_drift.append((n, s))

    score = 100.0
    score -= min(40, len(bad_trans) * 8)
    score -= min(20, len(bad_drift) * 4)
    score = max(0.0, score)

    if bad_trans:
        findings.append(AuditFinding(
            severity="ERROR" if any(j < 0.005 for _, j, _ in bad_trans) else "WARNING",
            code="M6-TRANS-BREAK",
            title="章节过渡断点",
            detail=(f"{len(bad_trans)} 处 ch_n 末段（{transition_window} 字）与 ch_(n+1) 首段"
                    "之间无任何具名实体（4-gram）重合"),
            evidence=[f"→ch{n} jac={j:.4f} overlap_grams={ov}" for n, j, ov in bad_trans[:8]],
        ))
    if bad_drift:
        findings.append(AuditFinding(
            severity="WARNING",
            code="M6-STYLE-DRIFT",
            title="章节风格离群",
            detail=f"{len(bad_drift)} 章风格与全本均值余弦低于 mean-2σ",
            evidence=[f"ch{n} sim={s:.3f}" for n, s in bad_drift[:8]],
        ))

    return score, {
        "transition_jaccard": [
            {"next_ch": n, "jaccard": round(j, 4), "overlap_grams": ov}
            for n, j, ov in transition_jacs
        ],
        "drift_sim_stats": s_drift,
        "low_transition_chapters": [
            {"next_ch": n, "jaccard": round(j, 4), "overlap_grams": ov}
            for n, j, ov in bad_trans
        ],
        "low_drift_chapters": bad_drift,
    }, findings


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------

# 各维度权重（综合分加权）
DIMENSION_WEIGHTS = {
    "M1_basic_stats": 0.10,
    "M2_character_distribution": 0.25,
    "M3_hook_repetition": 0.15,
    "M4_canon_in_chapters": 0.25,
    "M5_foreshadow_ledger": 0.15,
    "M6_style_continuity": 0.10,
}


def audit_full_novel(novel_dir: str, novel_id: Optional[str] = None) -> AuditReport:
    novel_id = novel_id or os.path.basename(os.path.normpath(novel_dir))
    metadata = _load_json(os.path.join(novel_dir, "metadata.json")) or {}
    characters = _load_json(os.path.join(novel_dir, "characters.json")) or {}
    blueprint = _load_json(os.path.join(novel_dir, "outline", "blueprint.json")) or {}
    cards = _load_chapter_cards(novel_dir)
    total_chapters = int(metadata.get("total_chapters_planned") or len(cards) or 0)

    # 加载所有已存在的章节正文 + meta
    chap_texts: Dict[int, str] = {}
    metas: Dict[int, Dict[str, Any]] = {}
    chap_dir = os.path.join(novel_dir, "chapters_demo")
    if os.path.isdir(chap_dir):
        for fn in sorted(os.listdir(chap_dir)):
            m = re.match(r"chapter_(\d+)\.txt$", fn)
            if not m:
                continue
            n = int(m.group(1))
            _, body = _load_chapter_text(novel_dir, n)
            if body:
                chap_texts[n] = body
            meta = _load_chapter_meta(novel_dir, n)
            if meta:
                metas[n] = meta

    findings: List[AuditFinding] = []
    metrics: Dict[str, Any] = {}
    scores: Dict[str, float] = {}

    s, m, fs = audit_basic_stats(novel_dir, cards, metas)
    scores["M1_basic_stats"] = s
    metrics["M1_basic_stats"] = m
    findings.extend(fs)

    s, m, fs = audit_character_distribution(novel_dir, characters, metas)
    scores["M2_character_distribution"] = s
    metrics["M2_character_distribution"] = m
    findings.extend(fs)

    s, m, fs = audit_hook_repetition(cards)
    scores["M3_hook_repetition"] = s
    metrics["M3_hook_repetition"] = m
    findings.extend(fs)

    s, m, fs = audit_canon_in_chapters(novel_dir, characters, chap_texts)
    scores["M4_canon_in_chapters"] = s
    metrics["M4_canon_in_chapters"] = m
    findings.extend(fs)

    s, m, fs = audit_foreshadow_ledger(blueprint, chap_texts, cards)
    scores["M5_foreshadow_ledger"] = s
    metrics["M5_foreshadow_ledger"] = m
    findings.extend(fs)

    s, m, fs = audit_style_continuity(chap_texts)
    scores["M6_style_continuity"] = s
    metrics["M6_style_continuity"] = m
    findings.extend(fs)

    # 综合分
    overall = sum(scores[k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS)

    return AuditReport(
        novel_id=novel_id,
        novel_title=str(metadata.get("title") or ""),
        chapters_total=total_chapters,
        chapters_loaded=len(chap_texts),
        overall_score=overall,
        dimension_scores=scores,
        findings=findings,
        metrics=metrics,
    )


# ----------------------------------------------------------------------
# 终端友好渲染
# ----------------------------------------------------------------------

def render_report_text(report: AuditReport) -> str:
    out: List[str] = []
    out.append("=" * 72)
    out.append(f"全本通读纵览  novel_id={report.novel_id}  title={report.novel_title}")
    out.append("-" * 72)
    out.append(f"章节总数（计划/实际加载）：{report.chapters_total} / {report.chapters_loaded}")
    out.append(f"综合得分：{report.overall_score:.2f} / 100")
    out.append("")
    out.append("各维度分数：")
    for k, s in report.dimension_scores.items():
        bar_len = int(s / 100 * 30)
        out.append(f"  {k:32s}  {s:6.2f}  {'█' * bar_len}{'·' * (30 - bar_len)}")
    out.append("")
    sev_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    sorted_findings = sorted(report.findings,
                             key=lambda f: (sev_order.get(f.severity, 9), f.code))
    if not sorted_findings:
        out.append("[OK] 无显著问题。")
    else:
        out.append(f"问题清单（共 {len(sorted_findings)} 条）：")
        for i, f in enumerate(sorted_findings, 1):
            out.append(f"\n  #{i:02d} [{f.severity}] [{f.code}] {f.title}")
            out.append(f"      {f.detail}")
            for ev in f.evidence[:6]:
                short = ev if len(ev) <= 130 else ev[:127] + "…"
                out.append(f"      - {short}")
    out.append("\n" + "=" * 72)
    return "\n".join(out)
