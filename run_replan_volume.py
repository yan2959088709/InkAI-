"""
run_replan_volume.py
====================

基于 DynamicKnowledgeManager 的状态对某一卷重新规划章节卡。
专门用于"前几卷已写、后续卷还没生成（或想推翻重来）"时把 DKM 反馈
（逾期伏笔、本卷应收伏笔、未埋伏笔等）强制喂给 OutlinePlanner，
让规划阶段就主动安排回收，而不是在 Validator 阶段才发现问题。

典型用法
--------
1) dry-run（看 LLM 会安排成什么样，不动磁盘）：
   python run_replan_volume.py --novel-id <id> --volume 3 --dry-run

2) 正式覆盖（自动备份原 volume_<N>_chapters.json 为 .bak.<时间戳>）：
   python run_replan_volume.py --novel-id <id> --volume 3

3) 不让 DKM 介入（退化为"不带债务上下文的纯重新规划"，用于对照）：
   python run_replan_volume.py --novel-id <id> --volume 3 --no-dkm

返回值（打印到终端）
-------------------
- 必收伏笔覆盖数 / 重试是否触发
- 每章被分配的 foreshadow_payoff（按 id 列出）
- 与原章节卡比较的 diff（粗粒度：标题、role、伏笔分布）
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from typing import Any, Dict, List, Optional

import config
from core.outline_planner import OutlinePlanner
from core.dynamic_knowledge_manager import DynamicKnowledgeManager


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def collect_banned_endings_from_prior_volumes(
    novel_id: str,
    blueprint: Dict[str, Any],
    target_volume_index: int,
) -> List[str]:
    """收集所有 < target_volume_index 卷的 ending_hook（含已落盘 chapter_<N>.meta.json
    中真正用过的钩子；若仅有 chapter_card，也用它的 ending_hook 字段）。"""
    used: List[str] = []
    outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
    chapters_dir = os.path.join(config.NOVELS_DIR, novel_id, "chapters_demo")

    # 1) 章节卡中的钩子
    for v in blueprint.get("volumes", []):
        v_idx = int(v.get("index", -1))
        if v_idx <= 0 or v_idx >= target_volume_index:
            continue
        cards_path = os.path.join(outline_dir, f"volume_{v_idx}_chapters.json")
        payload = load_json(cards_path)
        if not payload:
            continue
        for card in payload.get("chapter_cards", []) or []:
            e = (card.get("ending_hook") or "").strip()
            if e and e not in used:
                used.append(e)

    # 2) 已落盘正文 meta 中的真实钩子（更可信）
    if os.path.isdir(chapters_dir):
        for fn in sorted(os.listdir(chapters_dir)):
            if not fn.endswith(".meta.json"):
                continue
            meta = load_json(os.path.join(chapters_dir, fn))
            if not meta:
                continue
            ch_n = meta.get("chapter_number")
            v_idx = meta.get("volume_index")
            if not ch_n or not v_idx or v_idx >= target_volume_index:
                continue
            ed = ((meta.get("chapter_card") or {}).get("ending_hook") or "").strip()
            if ed and ed not in used:
                used.append(ed)
    return used


def diff_payload(old_payload: Optional[Dict[str, Any]], new_payload: Dict[str, Any]) -> List[str]:
    """生成简短 diff 摘要，按章号对齐打印。"""
    lines: List[str] = []
    old_cards = (old_payload or {}).get("chapter_cards", []) or []
    new_cards = new_payload.get("chapter_cards", []) or []
    old_idx = {int(c.get("chapter_number", 0)): c for c in old_cards}
    new_idx = {int(c.get("chapter_number", 0)): c for c in new_cards}

    all_chs = sorted(set(old_idx.keys()) | set(new_idx.keys()))
    for ch in all_chs:
        o = old_idx.get(ch)
        n = new_idx.get(ch)
        if o is None:
            lines.append(f"  + ch{ch} 新增：{n.get('title')!r}  role={n.get('role')}  "
                         f"plant={n.get('foreshadow_plant')}  payoff={n.get('foreshadow_payoff')}")
            continue
        if n is None:
            lines.append(f"  - ch{ch} 移除：{o.get('title')!r}")
            continue

        bits = []
        if (o.get("title") or "") != (n.get("title") or ""):
            bits.append(f"title: {o.get('title')!r} → {n.get('title')!r}")
        if (o.get("role") or "") != (n.get("role") or ""):
            bits.append(f"role: {o.get('role')} → {n.get('role')}")
        op = sorted(o.get("foreshadow_payoff") or [])
        np_ = sorted(n.get("foreshadow_payoff") or [])
        if op != np_:
            bits.append(f"payoff: {op} → {np_}")
        opl = sorted(o.get("foreshadow_plant") or [])
        npl = sorted(n.get("foreshadow_plant") or [])
        if opl != npl:
            bits.append(f"plant: {opl} → {npl}")
        if bits:
            lines.append(f"  ~ ch{ch}：" + "; ".join(bits))
        else:
            lines.append(f"  = ch{ch}：无显著差异（{n.get('title')}）")
    return lines


def print_payload_summary(payload: Dict[str, Any]) -> None:
    print(f"\n=== 重新规划结果（卷 {payload.get('volume_index')} · {payload.get('volume_title')}） ===")
    cov = payload.get("debt_coverage") or {}
    if cov.get("must_count"):
        print(f"  必收伏笔覆盖：{cov.get('covered_count')}/{cov.get('must_count')}"
              f"   覆盖={cov.get('covered')}   未覆盖={cov.get('uncovered')}"
              f"   重试触发={bool(cov.get('retried'))}")
        if cov.get("by_chapter"):
            print(f"  分配明细（章 → 收哪些 id）：{cov.get('by_chapter')}")
    else:
        print("  必收伏笔覆盖：0/0  （DKM 未提供任何必收项）")

    print("\n  章节列表：")
    for c in payload.get("chapter_cards", []):
        plant = c.get("foreshadow_plant") or []
        payoff = c.get("foreshadow_payoff") or []
        print(f"    ch{c.get('chapter_number')} [{c.get('role')}] {c.get('title')}"
              f"  | plant={plant}  payoff={payoff}")


def main() -> int:
    parser = argparse.ArgumentParser(description="基于 DKM 状态重新规划某一卷的章节卡")
    parser.add_argument("--novel-id", required=True, help="novel id（data/novels 下子目录名）")
    parser.add_argument("--volume", type=int, required=True, help="目标卷号（从 1 起）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只生成不写盘；终端打印结果与 diff")
    parser.add_argument("--no-dkm", action="store_true",
                        help="不加载 DKM state，退化为不带债务上下文的纯重新规划（对照用）")
    parser.add_argument("--no-banned", action="store_true",
                        help="不收集前序卷已用 ending_hook（默认会收集）")
    args = parser.parse_args()

    novel_id = args.novel_id
    target_v = args.volume

    blueprint_path = os.path.join(config.NOVELS_DIR, novel_id, "outline", "blueprint.json")
    blueprint = load_json(blueprint_path)
    if not blueprint:
        print(f"[ERROR] 未找到蓝图 {blueprint_path}")
        return 2
    print(f"[INFO] 已加载蓝图：{blueprint_path}")
    print(f"[INFO] 标题=《{blueprint.get('meta', {}).get('title')}》  "
          f"主角={blueprint.get('meta', {}).get('protagonist_name')}  "
          f"卷数={len(blueprint.get('volumes', []))}")

    target_vol = next((v for v in blueprint.get("volumes", [])
                       if int(v.get("index", -1)) == target_v), None)
    if not target_vol:
        print(f"[ERROR] 蓝图中没有卷 {target_v}")
        return 2
    print(f"[INFO] 目标卷：vol{target_v} 《{target_vol.get('title')}》  "
          f"chapter_range={target_vol.get('chapter_range')}  phase={target_vol.get('phase')}")

    dkm: Optional[DynamicKnowledgeManager] = None
    if not args.no_dkm:
        dkm = DynamicKnowledgeManager(novel_id=novel_id)
        loaded = dkm.load_state()
        if loaded:
            print(f"[DKM] 已加载状态：last_updated_chapter={dkm.state.get('last_updated_chapter')}  "
                  f"角色 {len(dkm.state.get('characters', {}))} 个 / "
                  f"伏笔 {len(dkm.state.get('foreshadowings', {}))} 个")
        else:
            print(f"[DKM] 未找到 state 文件，将以空状态运行（无债务可注入），"
                  f"等价于 --no-dkm 但保留 DKM 框架")

    banned: List[str] = []
    if not args.no_banned:
        banned = collect_banned_endings_from_prior_volumes(novel_id, blueprint, target_v)
        print(f"[INFO] 收集到前序卷已用 ending_hook 共 {len(banned)} 条")

    planner = OutlinePlanner()
    payload = planner.process({
        "mode": "volume_cards",
        "blueprint": blueprint,
        "volume_index": target_v,
        "banned_endings": banned,
        "dkm": dkm,
    })
    if payload.get("error"):
        print(f"[ERROR] OutlinePlanner 失败：{payload['error']}")
        return 3

    print_payload_summary(payload)

    cards_path = os.path.join(config.NOVELS_DIR, novel_id, "outline", f"volume_{target_v}_chapters.json")
    old_payload = load_json(cards_path)
    if old_payload:
        print("\n=== 与原章节卡的 diff（按章号） ===")
        for line in diff_payload(old_payload, payload):
            print(line)

    if args.dry_run:
        print("\n[DRY-RUN] 未写盘。如需正式覆盖，去掉 --dry-run 重跑。")
        return 0

    if old_payload:
        ts = time.strftime("%Y%m%d_%H%M%S")
        bak_path = f"{cards_path}.bak.{ts}"
        shutil.copy2(cards_path, bak_path)
        print(f"\n[OK] 原章节卡已备份：{bak_path}")
    save_json(cards_path, payload)
    print(f"[OK] 新章节卡已落盘：{cards_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
