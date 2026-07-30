"""
run_cleanup_orphan_files.py —— 清理 novel 目录中的"旧流水线孤儿文件"

背景：
  InkAI 项目早期的 inkai_workflow_optimized.py 等旧流水线会写出一批
  辅助文件（tags.json / workflow_context.json / *_quality_assessment.json /
  core_knowledge.json / dynamic_knowledge.json / foreshadowing_lifecycle.json）。
  新流水线（run_init_novel + run_outline_demo + run_chapter_demo）已经不再
  使用这些文件，但它们仍堆在历史小说目录里，让结构难懂。

本工具就是把这些孤儿文件**安全地**移出 novel 目录：
  - 默认 dry-run，不动文件，只列出会被处理的清单；
  - 加 --yes 才真正移动；
  - 默认会把孤儿文件备份到 <novel_dir>/_orphan_backup_<timestamp>/，
    可用 --no-backup 直接删除（不推荐）。

详细的归属表请见：docs/development/data_files_catalog.md

示例：
  # 干跑：列出所有 novel 中将被清理的孤儿
  python run_cleanup_orphan_files.py --all --dry-run

  # 真清理某一本（带备份）
  python run_cleanup_orphan_files.py --novel-id <id> --yes

  # 一次清理所有（带备份）
  python run_cleanup_orphan_files.py --all --yes

  # 不要备份直接删（只在你完全明白时使用）
  python run_cleanup_orphan_files.py --novel-id <id> --yes --no-backup
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime
from typing import List, Tuple

import config


# 要清理的孤儿文件白名单（保守选择，全部位于 novel_dir 根部）
ORPHAN_FILES: Tuple[str, ...] = (
    "tags.json",
    "workflow_context.json",
    "character_quality_assessment.json",
    "storyline_quality_assessment.json",
    "continuation_storyline_quality_assessment.json",
    "core_knowledge.json",
    "dynamic_knowledge.json",
    "foreshadowing_lifecycle.json",
)


def find_orphans_in_novel(novel_dir: str) -> List[str]:
    """返回某个 novel_dir 下实际存在的孤儿文件相对路径列表。"""
    found: List[str] = []
    for name in ORPHAN_FILES:
        path = os.path.join(novel_dir, name)
        if os.path.isfile(path):
            found.append(name)
    return found


def cleanup_one_novel(
    novel_dir: str,
    *,
    dry_run: bool,
    backup: bool,
) -> Tuple[int, int]:
    """清理一个 novel 目录。返回 (找到孤儿数, 已处理数)。"""
    novel_id = os.path.basename(os.path.normpath(novel_dir))
    orphans = find_orphans_in_novel(novel_dir)
    if not orphans:
        print(f"[SKIP] {novel_id}：无孤儿文件")
        return (0, 0)
    print(f"\n[NOVEL] {novel_id}（{novel_dir}）")
    for name in orphans:
        full = os.path.join(novel_dir, name)
        size = os.path.getsize(full)
        print(f"   - {name}  ({size} bytes)")
    if dry_run:
        print(f"   → DRY-RUN：未实际处理（如需真清理，请加 --yes）")
        return (len(orphans), 0)

    handled = 0
    backup_dir = ""
    if backup:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(novel_dir, f"_orphan_backup_{ts}")
        os.makedirs(backup_dir, exist_ok=True)
        print(f"   → 备份目录：{backup_dir}")

    for name in orphans:
        full = os.path.join(novel_dir, name)
        try:
            if backup:
                shutil.move(full, os.path.join(backup_dir, name))
            else:
                os.remove(full)
            handled += 1
        except OSError as exc:
            print(f"   [ERR] 处理 {name} 失败：{exc}")

    action = "已备份并移除" if backup else "已直接删除"
    print(f"   ✓ {action} {handled}/{len(orphans)} 个孤儿文件")
    return (len(orphans), handled)


def main() -> int:
    p = argparse.ArgumentParser(description="清理 novel 目录中的旧流水线孤儿文件")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--novel-id", help="只清理某个 novel_id")
    grp.add_argument("--novel-dir", help="只清理某个 novel 目录（绝对路径）")
    grp.add_argument("--all", action="store_true", help="清理 data/novels/ 下所有 novel")
    p.add_argument("--yes", action="store_true",
                   help="真正执行清理（不加则为 dry-run，仅列出清单）")
    p.add_argument("--no-backup", action="store_true",
                   help="不创建备份直接删除（不推荐；仅在确信不需要时使用）")
    args = p.parse_args()

    dry_run = not args.yes
    backup = not args.no_backup

    targets: List[str] = []
    if args.all:
        if not os.path.isdir(config.NOVELS_DIR):
            print(f"[ERROR] novels 根目录不存在：{config.NOVELS_DIR}")
            return 2
        for entry in sorted(os.listdir(config.NOVELS_DIR)):
            full = os.path.join(config.NOVELS_DIR, entry)
            if os.path.isdir(full):
                targets.append(full)
    elif args.novel_dir:
        targets.append(args.novel_dir)
    else:
        targets.append(os.path.join(config.NOVELS_DIR, args.novel_id))

    if dry_run:
        print("[MODE] DRY-RUN（不会改动任何文件，只列出清单）")
    else:
        print(f"[MODE] {'BACKUP+REMOVE' if backup else 'DELETE-ONLY'}（真正执行清理）")

    total_found = 0
    total_handled = 0
    for novel_dir in targets:
        if not os.path.isdir(novel_dir):
            print(f"[WARN] 跳过：{novel_dir}（目录不存在）")
            continue
        found, handled = cleanup_one_novel(
            novel_dir, dry_run=dry_run, backup=backup
        )
        total_found += found
        total_handled += handled

    print()
    print("=" * 64)
    if dry_run:
        print(f"[SUMMARY] DRY-RUN 共发现 {total_found} 个孤儿文件，"
              f"覆盖 {len(targets)} 个 novel 目录。")
        print("           如要真正清理，请重新运行并加 --yes。")
    else:
        print(f"[SUMMARY] 共处理 {total_handled}/{total_found} 个孤儿文件，"
              f"覆盖 {len(targets)} 个 novel 目录。")
        if backup:
            print("           已备份到各 novel 目录下的 _orphan_backup_<timestamp>/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
