"""
DynamicKnowledgeManager 初始化 / 重建脚本

用途：
- 在已有正文（data/novels/<id>/chapters_demo/chapter_*.txt）的基础上，
  根据 outline 里的 chapter_cards 一口气重建 dynamic_state/state.json。
- 对已经写了一半的项目特别有用——之前没接 DKM，跑一次这个脚本就能补上历史状态。
- 也可以用来调试：在 --print-snapshot N 模式下，输出"截至 chN-1 时的世界状态"
  渲染好的 prompt 字符串，所见即所得。

用法：
  # 重建并落盘
  python run_init_dynamic_state.py --novel-id <id>

  # 重建后立即打印某一章的 snapshot（不写盘可加 --dry-run）
  python run_init_dynamic_state.py --novel-id <id> --print-snapshot 20
  python run_init_dynamic_state.py --novel-id <id> --print-snapshot 20 --dry-run

  # 只看健康报告，不重新写盘（适合在已经有 state.json 时快速 health check）
  python run_init_dynamic_state.py --novel-id <id> --health-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import config
from core.dynamic_knowledge_manager import DynamicKnowledgeManager


DEFAULT_NOVEL_ID = "8defce7e-38e6-4f01-9108-80643103876f"


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_chapter_pairs(novel_id: str, blueprint: Dict[str, Any]) -> List[Tuple[Dict[str, Any], str]]:
    """按章号遍历所有卷，把 (chapter_card, chapter_body) 拉成扁平列表。

    缺正文的章会跳过（只用 outline 里有卡 + chapters_demo 里有正文的章）。
    """
    pairs: List[Tuple[Dict[str, Any], str]] = []
    outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
    chapter_dir = os.path.join(config.NOVELS_DIR, novel_id, "chapters_demo")

    for v in (blueprint.get("volumes") or []):
        vol_idx = v.get("index")
        cards_path = os.path.join(outline_dir, f"volume_{vol_idx}_chapters.json")
        vp = load_json(cards_path)
        if not vp:
            continue
        for card in (vp.get("chapter_cards") or []):
            ch = int(card.get("chapter_number") or 0)
            if ch <= 0:
                continue
            text_path = os.path.join(chapter_dir, f"chapter_{ch}.txt")
            if not os.path.exists(text_path):
                continue
            with open(text_path, "r", encoding="utf-8") as f:
                body = f.read()
            pairs.append((card, body))

    pairs.sort(key=lambda p: int(p[0].get("chapter_number") or 0))
    return pairs


def print_health(report: Dict[str, Any]) -> None:
    s = report["summary"]
    print()
    print("=" * 70)
    print(f"[HEALTH] 截至 ch{report['as_of_chapter']}  总问题 {s['total_issues']} "
          f"(高{s['high']} 中{s['medium']} 低{s['low']})")
    print(f"  角色 {s['characters_count']}  道具 {s['objects_count']}  地点 {s['locations_count']}")
    print(f"  伏笔：未回收 {s['foreshadowings_open']}  已回收 {s['foreshadowings_closed']}  "
          f"逾期 {s['foreshadowings_overdue']}")
    print("=" * 70)
    if not report["issues"]:
        print("  暂无问题")
        return
    for i in report["issues"]:
        print(f"  [{i['severity'].upper():<6s}] [{i['kind']:<28s}] {i['message']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="DynamicKnowledgeManager 初始化/重建工具")
    parser.add_argument("--novel-id", default=DEFAULT_NOVEL_ID)
    parser.add_argument("--dry-run", action="store_true",
                        help="不写盘，只在内存里跑一遍（适合配合 --print-snapshot 调试）")
    parser.add_argument("--print-snapshot", type=int, default=None, metavar="CH",
                        help="重建后打印 '截至 ch CH-1 时的 prompt 字符串'，所见即所得")
    parser.add_argument("--health-only", action="store_true",
                        help="不重建（用已有 state.json），只跑一次 health_check 输出报告")
    args = parser.parse_args()

    novel_id = args.novel_id
    bp_path = os.path.join(config.NOVELS_DIR, novel_id, "outline", "blueprint.json")
    blueprint = load_json(bp_path)
    if not blueprint:
        print(f"[ERROR] 找不到蓝图：{bp_path}")
        return 1

    print(f"[INFO] novel_id={novel_id}")
    print(f"[INFO] 蓝图：{blueprint.get('meta',{}).get('title')}  "
          f"主角={blueprint.get('meta',{}).get('protagonist_name')}")

    dkm = DynamicKnowledgeManager(novel_id=novel_id, blueprint=blueprint)

    if args.health_only:
        loaded = dkm.load_state()
        if not loaded:
            print(f"[ERROR] 找不到 state.json（{dkm.state_path}），请先重建")
            return 1
        print_health(dkm.health_check())
        return 0

    pairs = collect_chapter_pairs(novel_id, blueprint)
    if not pairs:
        print("[WARN] 没有找到任何已落盘的正文章节，state 将是初始空状态")
    else:
        print(f"[INFO] 收集到 {len(pairs)} 章正文，开始重建动态状态…")
        dkm.rebuild_from_scratch(pairs)

    s = dkm.state["stats"]
    print(f"[OK] 重建完成 → 已索引 {s['total_chapters_indexed']} 章 / 共 {s['total_words']} 字")
    print(f"     角色 {len(dkm.state['characters'])} / 道具 {len(dkm.state['objects'])} / "
          f"地点 {len(dkm.state['locations'])} / 伏笔 {len(dkm.state['foreshadowings'])}")

    if not args.dry_run:
        path = dkm.save_state()
        print(f"[OK] state.json 已落盘：{path}")
    else:
        print("[DRY-RUN] 未写盘")

    if args.print_snapshot is not None:
        snap = dkm.snapshot_for_chapter(args.print_snapshot)
        print()
        print("=" * 70)
        print(f"[SNAPSHOT] 写第 {args.print_snapshot} 章前会注入到 LLM prompt 的内容如下：")
        print("=" * 70)
        print(DynamicKnowledgeManager.format_snapshot_for_prompt(snap))

    print_health(dkm.health_check())
    return 0


if __name__ == "__main__":
    sys.exit(main())
