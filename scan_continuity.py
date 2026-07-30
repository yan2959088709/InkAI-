# -*- coding: utf-8 -*-
"""
启发式扫描卡间断裂点（人物突现 / 场景跳跃 / 道具承接缺失 / 首段未承接）

不调用 LLM，纯文本规则扫描。

用法：
    python scan_continuity.py --novel-id 8defce7e-38e6-4f01-9108-80643103876f
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import config


def load_volume_cards(novel_id: str) -> Dict[int, Dict[str, Any]]:
    """加载所有卷的 chapter_cards，返回 {chapter_number: card}"""
    outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
    cards: Dict[int, Dict[str, Any]] = {}
    for fn in sorted(os.listdir(outline_dir)):
        if not (fn.startswith("volume_") and fn.endswith("_chapters.json")):
            continue
        path = os.path.join(outline_dir, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue
        for card in payload.get("chapter_cards") or []:
            n = card.get("chapter_number")
            if isinstance(n, int):
                cards[n] = card
    return cards


def load_chapter_text(novel_id: str, n: int) -> Tuple[str, str]:
    """返回 (title, body)"""
    path = os.path.join(config.NOVELS_DIR, novel_id, "chapters_demo", f"chapter_{n}.txt")
    if not os.path.exists(path):
        return "", ""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    lines = raw.split("\n", 1)
    title = lines[0].strip() if lines else ""
    body = lines[1].lstrip("\n").rstrip() if len(lines) > 1 else ""
    return title, body


def split_must_appear(card: Dict[str, Any]) -> Dict[str, List[str]]:
    ma = card.get("must_appear") or {}
    return {
        "characters": [str(x).strip() for x in (ma.get("characters") or []) if str(x).strip()],
        "locations": [str(x).strip() for x in (ma.get("locations") or []) if str(x).strip()],
        "objects": [str(x).strip() for x in (ma.get("objects") or []) if str(x).strip()],
    }


def text_contains(text: str, term: str) -> bool:
    if not term:
        return False
    return term in text


# 简单的"过渡/移动/时间跳跃"动词集合，用于场景跳跃判定
TRANSITION_HINTS = [
    "回到", "返回", "赶到", "驶往", "驱车", "走进", "走出", "穿过", "推门", "登上", "下了",
    "三天后", "次日", "翌日", "第二天", "数小时后", "几天前", "随后", "稍晚",
    "他动身", "他启程", "她启程", "出发", "抵达", "推开门", "踏进", "钻进车",
    "车驶向", "上了车", "下了车", "回到办公室", "回到家", "返回",
]


def has_transition(text_first_200: str) -> bool:
    return any(h in text_first_200 for h in TRANSITION_HINTS)


def extract_first_segment(body: str, n: int = 300) -> str:
    """返回正文前 n 字"""
    return body[:n] if body else ""


def extract_last_segment(body: str, n: int = 300) -> str:
    return body[-n:] if body else ""


def scan_chapter_pair(
    prev_card: Optional[Dict[str, Any]],
    prev_title: str,
    prev_body: str,
    cur_card: Dict[str, Any],
    cur_title: str,
    cur_body: str,
    pre_history_chars: List[str],
    pre_history_locs: List[str],
    pre_history_objs: List[str],
) -> Dict[str, Any]:
    """对单个 (prev, cur) 对做断裂检测，返回 issues 列表"""
    issues: List[str] = []
    severity = 0  # 0~3, 3 最严重

    cur_n = cur_card.get("chapter_number")
    cur_ma = split_must_appear(cur_card)
    prev_ma = split_must_appear(prev_card) if prev_card else {"characters": [], "locations": [], "objects": []}

    cur_first = extract_first_segment(cur_body, 300)
    prev_last = extract_last_segment(prev_body, 300) if prev_body else ""

    # ---- 检测 1：人物突现 ----
    # 本章 must_appear.characters 中有人物，且该角色在前 3 章的 must_appear 与正文中都没出现
    surprise_chars: List[str] = []
    for ch_name in cur_ma["characters"]:
        if ch_name in prev_ma["characters"]:
            continue
        if ch_name in pre_history_chars:
            continue
        # 也允许"前章末段"或"本章首段过渡句"提到他的情况，不算突现
        if ch_name in prev_last or ch_name in cur_first:
            continue
        # 还需要：本章正文中确实重要地出现（>= 3 次），才算"突现且戏份足"
        if cur_body.count(ch_name) >= 3:
            surprise_chars.append(ch_name)
    if surprise_chars:
        issues.append(f"人物突现：{surprise_chars}（前 3 章未出现，本章直接成为关键角色）")
        severity = max(severity, 2)

    # ---- 检测 2：场景跳跃 ----
    # 本章 locations 与前章 locations 无任何交集，且本章首段没有过渡动词
    if prev_card and cur_ma["locations"] and prev_ma["locations"]:
        cur_loc_set = set(cur_ma["locations"])
        prev_loc_set = set(prev_ma["locations"])
        if not (cur_loc_set & prev_loc_set):
            # 进一步：检查首段里是否提到"任意一个前章 location"
            mentioned_prev_loc = any(loc in cur_first for loc in prev_ma["locations"])
            transition = has_transition(cur_first)
            if not mentioned_prev_loc and not transition:
                issues.append(
                    f"场景跳跃：前章 locations={prev_ma['locations']} → 本章 locations={cur_ma['locations']}，"
                    f"且首段无过渡词、未呼应前章场景"
                )
                severity = max(severity, 2)

    # ---- 检测 3：关键道具承接缺失（收紧：仅检查 ending_hook 显式高亮的道具） ----
    # 单章使用即归档的道具（如"染血指甲"用完即丢）不算断裂，
    # 真正的断裂是：前章 ending_hook 把某道具当作"未完成的悬念物"，本章却完全无视。
    drop_objs: List[str] = []
    hard_drop = False  # 是否是 ending_hook 显式提及的硬丢失
    if prev_card:
        prev_ending = (prev_card.get("ending_hook") or "").strip()
        prev_objs = prev_ma["objects"]
        # 仅当道具同时满足 (a) 在 prev_ma.objects 里 (b) 在 ending_hook 里被明确高亮
        # 才视为"必须承接的悬念物"
        # 道具与 ending_hook 之间允许"短词包含"匹配：
        # ending_hook 写"模糊车牌" 而 must_appear.objects 写"模糊车牌影像"也算命中
        def _ending_hits(obj: str) -> bool:
            if not obj:
                return False
            if obj in prev_ending:
                return True
            # 取道具前 3-4 字试一次
            if len(obj) >= 4 and obj[:4] in prev_ending:
                return True
            if len(obj) >= 3 and obj[:3] in prev_ending:
                return True
            return False
        ending_objs = [o for o in prev_objs if _ending_hits(o)]
        for obj in ending_objs:
            if obj and (obj not in cur_body) and (obj not in cur_ma["objects"]):
                drop_objs.append(obj)
                hard_drop = True
    if drop_objs:
        issues.append(f"⚠ ending_hook 道具承接缺失：前章末尾高亮的悬念道具 {drop_objs} 在本章正文与 must_appear 中均未出现")
        severity = max(severity, 3)

    # ---- 检测 4：首段未承接 ----
    # 本章首段 300 字内，没有提到前章任何 must_appear 名词（人/地/物）
    if prev_card and prev_body:
        anchor_terms: List[str] = []
        anchor_terms.extend(prev_ma["characters"])
        anchor_terms.extend(prev_ma["locations"])
        anchor_terms.extend(prev_ma["objects"])
        # 加上前章末段中出现的高频名词（这里偷懒：取末段中长度>=3且与 must_appear 重复的）
        anchor_terms = [t for t in set(anchor_terms) if t and len(t) >= 2]
        if anchor_terms:
            mentioned = [t for t in anchor_terms if t in cur_first]
            if len(mentioned) == 0:
                issues.append(
                    f"首段未承接：本章前 300 字未提及前章任何关键名词（候选 {anchor_terms[:6]}{'...' if len(anchor_terms)>6 else ''}）"
                )
                severity = max(severity, 2)

    return {
        "chapter": cur_n,
        "title": cur_title,
        "issues": issues,
        "severity": severity,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--novel-id", required=True)
    parser.add_argument("--start", type=int, default=2)
    parser.add_argument("--end", type=int, default=50)
    parser.add_argument("--min-severity", type=int, default=2,
                        help="只报告严重度 >= 此值的断裂")
    args = parser.parse_args()

    cards = load_volume_cards(args.novel_id)
    if not cards:
        print("[ERR] 未找到任何 chapter_cards", file=sys.stderr)
        sys.exit(1)

    reports: List[Dict[str, Any]] = []
    history_chars: List[str] = []
    history_locs: List[str] = []
    history_objs: List[str] = []
    history_window = 3  # 前 N 章作为"已露面"判定窗口

    for n in range(args.start, args.end + 1):
        cur_card = cards.get(n)
        if not cur_card:
            continue
        cur_title, cur_body = load_chapter_text(args.novel_id, n)
        if not cur_body:
            continue

        prev_card = cards.get(n - 1)
        prev_title, prev_body = load_chapter_text(args.novel_id, n - 1) if prev_card else ("", "")

        # 维护"前 history_window 章"的累计 must_appear（不包括本章和直接前章）
        old_chars: List[str] = []
        old_locs: List[str] = []
        old_objs: List[str] = []
        for k in range(max(1, n - 1 - history_window), n - 1):
            ck = cards.get(k)
            if not ck:
                continue
            ma = split_must_appear(ck)
            old_chars.extend(ma["characters"])
            old_locs.extend(ma["locations"])
            old_objs.extend(ma["objects"])

        report = scan_chapter_pair(
            prev_card=prev_card,
            prev_title=prev_title,
            prev_body=prev_body,
            cur_card=cur_card,
            cur_title=cur_title,
            cur_body=cur_body,
            pre_history_chars=old_chars,
            pre_history_locs=old_locs,
            pre_history_objs=old_objs,
        )
        if report["issues"] and report["severity"] >= args.min_severity:
            reports.append(report)

    # 输出
    print(f"=== 卡间断裂扫描报告（共 {len(reports)} 处需关注） ===\n")
    for r in reports:
        print(f"【第{r['chapter']}章 《{r['title']}》】 severity={r['severity']}")
        for i, msg in enumerate(r["issues"], 1):
            print(f"  ({i}) {msg}")
        print()

    # 同时按 severity 倒序生成 revise 优先级清单
    print("=== Revise 优先级清单（severity 倒序） ===")
    sorted_reports = sorted(reports, key=lambda r: -r["severity"])
    for r in sorted_reports:
        print(f"  ch{r['chapter']:>2}  sev={r['severity']}  {r['title']}  -- {len(r['issues'])} 项")

    # 落盘
    out_path = os.path.join(config.NOVELS_DIR, args.novel_id, "continuity_scan.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"min_severity": args.min_severity, "reports": reports}, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 报告已落盘: {out_path}")


if __name__ == "__main__":
    main()
