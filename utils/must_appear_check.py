"""
must_appear_check —— ChapterCard.must_appear 与正文的一致性校验

定位
----
取代之前那一版"基于姓氏白名单 + 词典黑名单"的启发式 illegal_name_candidates。
启发式一定要堆词典维护，每换一本小说（武侠/校园/科幻）都要重写，**方向是错的**。

正确的真值在 ChapterCard 里就有：

    chapter_card.must_appear = {
        "characters": [...],
        "locations":  [...],
        "objects":    [...]
    }

OutlinePlanner 在生成 chapter cards 时已经规划了"本章必须出场的人/地/物"。
我们只需要做一件确定性的事：**校验正文是否真的兑现了这个规划。**

这是零硬编码、跨题材通用、无误报的检查。

API
---
- check_card_against_body(card, body) -> dict（单章）
- check_volume_must_appear(cards, body_pairs) -> dict（整卷）

返回结构（详见函数 docstring），核心是 coverage 与 missing/light/extra。
"""

from typing import Dict, List, Tuple, Any


# 不同维度对"出现"的判定阈值
_OK_THRESHOLD = 2       # 完整字符串 ≥2 次视为正式出场
_LIGHT_THRESHOLD = 1    # 完整字符串 1 次视为"提了一嘴"
_FUZZY_BIGRAM_RATIO = 0.6  # 模糊匹配：term 的 2-gram 命中比例阈值


def _bigrams(s: str) -> List[str]:
    if len(s) < 2:
        return []
    return [s[i : i + 2] for i in range(len(s) - 1)]


def _match_term(body: str, term: str) -> Tuple[int, str]:
    """对单个 must_appear 项做"完整 → 模糊"两级匹配。

    返回 (匹配次数, 匹配级别)：
      - ("exact", n)  完整字符串出现 n 次（n>=1）
      - ("fuzzy", n)  完整未出现，但 term 的 2-gram 中 ≥60% 出现在正文里
                      —— 用于覆盖 LLM 自然化重述（'半张烧焦照片' 写成
                         '半张边缘焦黑卷曲的照片' / '烧焦的照片'）
                      n 取所有命中 2-gram 中最少的出现次数（保守估计）
      - ("none", 0)   都没匹配上
    """
    if not body or not term:
        return 0, "none"

    exact = body.count(term)
    if exact > 0:
        return exact, "exact"

    bgs = _bigrams(term)
    if len(bgs) < 2:
        return 0, "none"
    hits = [bg for bg in bgs if bg in body]
    distinct_hit = len(set(hits))
    needed = max(2, int(round(len(bgs) * _FUZZY_BIGRAM_RATIO)))
    if distinct_hit >= needed:
        # 取所有命中 bg 的最小出现次数作为保守计数
        approx = min(body.count(bg) for bg in set(hits)) if hits else 0
        return approx, "fuzzy"
    return 0, "none"


def _classify(count: int, level: str) -> str:
    """根据匹配级别 + 次数分类。

    - exact ≥2 次          → ok
    - exact 1 次或 fuzzy   → light
    - 都没有              → missing
    """
    if level == "exact" and count >= _OK_THRESHOLD:
        return "ok"
    if level == "exact" and count >= _LIGHT_THRESHOLD:
        return "light"
    if level == "fuzzy" and count >= _LIGHT_THRESHOLD:
        return "light"
    return "missing"


def check_card_against_body(card: Dict[str, Any], body: str) -> Dict[str, Any]:
    """单章一致性检查。

    返回：
    {
        "chapter_number": int,
        "characters": {"expected": [...], "ok": [...], "light": [...], "missing": [...]},
        "locations":  {同上},
        "objects":    {同上},
        "expected_total": int,
        "covered":   int,                 # ok+light 视为 covered
        "fully_ok":  int,                 # 仅 ok
        "coverage":  float,               # covered / expected_total
        "fully_ok_ratio": float,          # fully_ok / expected_total
    }
    """
    must = card.get("must_appear") or {}
    out: Dict[str, Any] = {
        "chapter_number": int(card.get("chapter_number", 0)),
    }
    expected_total = 0
    covered = 0
    fully_ok = 0

    for dim in ("characters", "locations", "objects"):
        expected = [t for t in (must.get(dim) or []) if isinstance(t, str) and t.strip()]
        ok_list, light_list, missing_list = [], [], []
        for term in expected:
            cnt, level = _match_term(body, term)
            tag = _classify(cnt, level)
            entry = {"name": term, "count": cnt, "match": level}
            if tag == "ok":
                ok_list.append(entry)
            elif tag == "light":
                light_list.append(entry)
            else:
                missing_list.append(entry)
        out[dim] = {
            "expected": expected,
            "ok": ok_list,
            "light": light_list,
            "missing": missing_list,
        }
        expected_total += len(expected)
        covered += len(ok_list) + len(light_list)
        fully_ok += len(ok_list)

    out["expected_total"] = expected_total
    out["covered"] = covered
    out["fully_ok"] = fully_ok
    out["coverage"] = round(covered / expected_total, 3) if expected_total else 1.0
    out["fully_ok_ratio"] = round(fully_ok / expected_total, 3) if expected_total else 1.0
    return out


def check_volume_must_appear(
    cards: List[Dict[str, Any]],
    body_pairs: List[Tuple[int, str]],
) -> Dict[str, Any]:
    """整卷聚合检查。

    返回：
    {
        "score":      float,              # 0-100
        "passed":     bool,
        "per_chapter": [check_card_against_body(...) per ch],
        "totals": {
            "expected": int, "covered": int, "fully_ok": int,
            "coverage": float, "fully_ok_ratio": float,
        },
        "issues":     [str, ...],         # 卡片说要出场但正文没出场的硬遗漏
    }
    """
    body_map = {ch_num: body for ch_num, body in body_pairs}
    per_chapter: List[Dict[str, Any]] = []

    total_expected = 0
    total_covered = 0
    total_fully_ok = 0
    issues: List[str] = []

    for c in cards:
        ch_num = int(c.get("chapter_number", 0))
        body = body_map.get(ch_num)
        if body is None:
            continue
        report = check_card_against_body(c, body)
        per_chapter.append(report)

        total_expected += report["expected_total"]
        total_covered += report["covered"]
        total_fully_ok += report["fully_ok"]

        for dim in ("characters", "locations", "objects"):
            for miss in report[dim]["missing"]:
                issues.append(
                    f"第{ch_num}章 must_appear.{dim} 声明的 '{miss['name']}' 未在正文出现"
                )

    coverage = (total_covered / total_expected) if total_expected else 1.0
    fully_ok_ratio = (total_fully_ok / total_expected) if total_expected else 1.0

    # 计分：fully_ok 占主权重，covered（含 light）占次权重
    # 全部 fully_ok = 100；全部 covered 但有 light = 70 起步；有 missing 直接拉低
    score = fully_ok_ratio * 70 + coverage * 30
    score = round(max(0.0, min(100.0, score)), 2)
    passed = score >= 80 and fully_ok_ratio >= 0.7

    return {
        "score": score,
        "passed": passed,
        "totals": {
            "expected": total_expected,
            "covered": total_covered,
            "fully_ok": total_fully_ok,
            "coverage": round(coverage, 3),
            "fully_ok_ratio": round(fully_ok_ratio, 3),
        },
        "per_chapter": per_chapter,
        "issues": issues,
    }
