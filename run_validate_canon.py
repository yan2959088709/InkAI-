"""
run_validate_canon.py —— 档案一致性校验 CLI

用途：
  对任意已存在的 novel，跑一次 characters.json ↔ storyline.json 的一致性审查。
  无需调用 LLM，纯本地规则，秒级出结果。

示例：
  # 用 novel_id 校验一本现存小说
  python run_validate_canon.py --novel-id 8defce7e-38e6-4f01-9108-80643103876f

  # 直接给 novel_dir
  python run_validate_canon.py --novel-dir data/novels/<novel_id>

  # 把报告落盘（默认会落到 <novel_dir>/canon_report.json，可用 --no-save 关闭）
  python run_validate_canon.py --novel-id <id> --save-path my_report.json

  # 只想跑一遍看终端输出
  python run_validate_canon.py --novel-id <id> --no-save
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import config
from core.canon_checker import load_and_check, render_report_text


def main() -> int:
    p = argparse.ArgumentParser(description="对一本小说做 characters.json ↔ storyline.json 一致性校验")
    p.add_argument("--novel-id", help="小说 id，将解析到 data/novels/<novel_id>")
    p.add_argument("--novel-dir", help="直接指定 novel 目录（与 --novel-id 二选一）")
    p.add_argument("--save-path", default=None,
                   help="报告 JSON 落盘路径；不指定则落到 <novel_dir>/canon_report.json")
    p.add_argument("--no-save", action="store_true", help="不落盘，仅打印终端报告")
    p.add_argument("--quiet", action="store_true", help="仅输出最终摘要，不打印详细 issue")
    args = p.parse_args()

    if not (args.novel_id or args.novel_dir):
        p.error("必须指定 --novel-id 或 --novel-dir 之一")

    novel_dir = args.novel_dir or os.path.join(config.NOVELS_DIR, args.novel_id)
    if not os.path.isdir(novel_dir):
        print(f"[ERROR] novel_dir 不存在：{novel_dir}")
        return 2

    report = load_and_check(novel_dir, novel_id=args.novel_id or os.path.basename(novel_dir))

    if args.quiet:
        s = report.summary
        print(f"[CANON] novel_id={report.novel_id}  "
              f"ERROR={s.get('ERROR', 0)}  WARNING={s.get('WARNING', 0)}  INFO={s.get('INFO', 0)}")
    else:
        print(render_report_text(report))

    if not args.no_save:
        save_path = args.save_path or os.path.join(novel_dir, "canon_report.json")
        os.makedirs(os.path.dirname(save_path), exist_ok=True) if os.path.dirname(save_path) else None
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\n[OK] 报告已落盘：{save_path}")

    # 退出码：有 ERROR 返回 1，否则 0；便于 CI/集成
    return 1 if report.has_errors() else 0


if __name__ == "__main__":
    sys.exit(main())
