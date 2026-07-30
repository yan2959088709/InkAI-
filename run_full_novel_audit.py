"""
run_full_novel_audit.py —— 全本通读探针 CLI

对一本（已生成至少部分章节的）小说做六维质量纵览：
  M1 基础规模  M2 角色分布  M3 钩子重复  M4 跨章档案  M5 伏笔账本  M6 风格连续

详细维度说明：core/full_novel_auditor.py 文件头注释。

示例：
  python run_full_novel_audit.py --novel-id <id>
  python run_full_novel_audit.py --novel-id <id> --quiet
  python run_full_novel_audit.py --novel-id <id> --save-path my_audit.json
  python run_full_novel_audit.py --compare <id_a> <id_b>   # 同时审两本，并打印对比表
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

# Windows PowerShell 默认 cp936，需要强制 utf-8 才能正确显示中文
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from core.full_novel_auditor import (
    audit_full_novel,
    render_report_text,
    DIMENSION_WEIGHTS,
)


def _audit_and_save(novel_id: str, novel_dir: str, save_default_name: str = "audit_report.json"):
    report = audit_full_novel(novel_dir, novel_id=novel_id)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="全本通读六维纵览（M1-M6）")
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--novel-id", help="要审计的 novel_id")
    grp.add_argument("--novel-dir", help="直接给 novel 目录")
    grp.add_argument("--compare", nargs=2, metavar=("ID_A", "ID_B"),
                     help="对两本小说做横向对比")
    p.add_argument("--save-path", default=None, help="JSON 报告落盘路径（默认到 <novel_dir>/audit_report.json）")
    p.add_argument("--no-save", action="store_true", help="只打印不落盘")
    p.add_argument("--quiet", action="store_true", help="只打印综合分一行")
    args = p.parse_args()

    if args.compare:
        ids = args.compare
        reports = []
        for nid in ids:
            ndir = os.path.join(config.NOVELS_DIR, nid)
            if not os.path.isdir(ndir):
                print(f"[ERROR] novel_dir 不存在：{ndir}")
                return 2
            rpt = audit_full_novel(ndir, novel_id=nid)
            reports.append(rpt)
        # 横向对比表
        print("=" * 72)
        print(f"  横向对比  {ids[0]}  vs  {ids[1]}")
        print("-" * 72)
        a, b = reports
        print(f"  {'title':36s}  {a.novel_title:<28s}  {b.novel_title}")
        print(f"  {'chapters_total/loaded':36s}  "
              f"{a.chapters_total}/{a.chapters_loaded:<28d}  "
              f"{b.chapters_total}/{b.chapters_loaded}")
        print(f"  {'overall_score':36s}  {a.overall_score:<28.2f}  {b.overall_score:.2f}")
        print(f"  {'-' * 36}  {'-' * 28}  {'-' * 8}")
        for k in DIMENSION_WEIGHTS:
            sa = a.dimension_scores.get(k, 0.0)
            sb = b.dimension_scores.get(k, 0.0)
            arrow = "↑" if sa > sb else ("↓" if sa < sb else "=")
            print(f"  {k:36s}  {sa:<28.2f}  {sb:.2f}  {arrow}")
        print("-" * 72)
        for r, label in zip(reports, ids):
            errs = sum(1 for f in r.findings if f.severity == "ERROR")
            wrns = sum(1 for f in r.findings if f.severity == "WARNING")
            infs = sum(1 for f in r.findings if f.severity == "INFO")
            print(f"  [{label}] findings: ERROR={errs} WARNING={wrns} INFO={infs}")
        print("=" * 72)
        # 保存对比报告
        if not args.no_save:
            for rpt, nid in zip(reports, ids):
                ndir = os.path.join(config.NOVELS_DIR, nid)
                save_path = os.path.join(ndir, "audit_report.json")
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(rpt.to_dict(), f, ensure_ascii=False, indent=2)
                print(f"[OK] 已落盘：{save_path}")
        return 0

    novel_dir = args.novel_dir or os.path.join(config.NOVELS_DIR, args.novel_id)
    if not os.path.isdir(novel_dir):
        print(f"[ERROR] novel_dir 不存在：{novel_dir}")
        return 2
    nid = args.novel_id or os.path.basename(os.path.normpath(novel_dir))
    report = audit_full_novel(novel_dir, novel_id=nid)

    if args.quiet:
        errs = sum(1 for f in report.findings if f.severity == "ERROR")
        wrns = sum(1 for f in report.findings if f.severity == "WARNING")
        infs = sum(1 for f in report.findings if f.severity == "INFO")
        print(f"[AUDIT] novel_id={report.novel_id} title={report.novel_title} "
              f"score={report.overall_score:.2f}/100 "
              f"E={errs} W={wrns} I={infs} "
              f"chapters={report.chapters_loaded}/{report.chapters_total}")
    else:
        print(render_report_text(report))

    if not args.no_save:
        save_path = args.save_path or os.path.join(novel_dir, "audit_report.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True) if os.path.dirname(save_path) else None
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\n[OK] 报告已落盘：{save_path}")

    # 退出码：综合分 < 60 视为不合格
    return 0 if report.overall_score >= 60 else 3


if __name__ == "__main__":
    sys.exit(main())
