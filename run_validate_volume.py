"""
VolumeValidator Demo —— 对指定卷做整卷质量校验

用法：
  python run_validate_volume.py --novel-id <id> --volume 1
  python run_validate_volume.py --novel-id <id> --volume 1 --json

特性：
- 完全独立运行，不调用 LLM，纯启发式校验
- 自动从 data/novels/<id>/outline/ 读 blueprint + volume_<N>_chapters.json
- 自动从 data/novels/<id>/chapters_demo/ 读已生成的 chapter_<n>.txt
- 校验报告保存到 data/novels/<id>/validation/volume_<N>_report.json

退出码：
  0 = 校验通过（综合分 ≥ 70）
  1 = 数据缺失或参数错误
  2 = 校验未通过
"""

import argparse
import json
import os
import sys
from typing import Dict, Any, Optional

import config
from agents.volume_validator import VolumeValidator


DEFAULT_NOVEL_ID = "8defce7e-38e6-4f01-9108-80643103876f"
DEFAULT_VOLUME = 1


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_chapter_texts(novel_id: str, start_ch: int, end_ch: int) -> Dict[int, str]:
    chapter_dir = os.path.join(config.NOVELS_DIR, novel_id, "chapters_demo")
    if not os.path.isdir(chapter_dir):
        return {}
    out: Dict[int, str] = {}
    for n in range(start_ch, end_ch + 1):
        path = os.path.join(chapter_dir, f"chapter_{n}.txt")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                out[n] = f.read()
        except Exception:
            continue
    return out


def print_report(report: Dict[str, Any]) -> None:
    s = report["summary"]
    print()
    print("=" * 70)
    print(f"卷 {report['volume_index']}  《{report.get('volume_title') or ''}》  整卷校验报告")
    print("=" * 70)
    flag = "[PASS]" if s["passed"] else "[WARN]"
    print(f"{flag}  综合分 = {s['overall_score']}/100   "
          f"卡数={s['chapter_count']}  正文数={s['body_count']}  总字数={s['total_words']}")

    print()
    print("--- 5 项检查 ---")
    for k, v in report["checks"].items():
        line_flag = "[OK]  " if v["passed"] else "[WARN]"
        print(f"  {line_flag} {k:<28s}  score={v['score']:.1f}")
        for issue in (v.get("issues") or []):
            print(f"         - {issue}")

    pacing = report["checks"]["pacing_density"]
    if pacing.get("role_sequence"):
        print()
        print(f"--- role 序列 ---  {pacing['role_sequence']}")
        ten = pacing["tension"]
        print(f"--- tension ---  values={ten['values']}  "
              f"avg={ten['avg']}  std={ten['std']}  min={ten['min']}  max={ten['max']}  flat={ten['flat']}")

    fs = report["checks"]["foreshadow_coverage"]
    print()
    print("--- 伏笔回收 ---")
    print(f"  期望回收: {len(fs.get('expected_payoffs', []))} 条")
    print(f"  已匹配  : {len(fs.get('matched_payoffs', []))} 条")
    print(f"  未回收  : {len(fs.get('missing_payoffs', []))} 条")
    print(f"  卡片声明 plant={fs.get('declared_plants')} payoff={fs.get('declared_payoffs')}")
    for m in fs.get("matched_payoffs", []):
        print(f"   [HIT]  {m['id']}  {m['content'][:30]}  card={m['card_hits']} text={m['text_hits']}")
    for m in fs.get("missing_payoffs", []):
        print(f"   [MISS] {m['id']}  {m['content'][:30]}  importance={m['importance']}")

    ma = report["checks"]["must_appear_coverage"]
    totals = ma.get("totals") or {}
    print()
    print("--- must_appear 覆盖率 ---")
    print(f"  期望出场项 {totals.get('expected', 0)} 个  "
          f"已覆盖 {totals.get('covered', 0)} 个（含'一笔带过'）  "
          f"正式出场 {totals.get('fully_ok', 0)} 个")
    print(f"  覆盖率={totals.get('coverage', 0)*100:.1f}%   "
          f"正式出场率={totals.get('fully_ok_ratio', 0)*100:.1f}%")
    if ma.get("issues"):
        print(f"  硬遗漏 {len(ma['issues'])} 处：")
        for issue in ma["issues"][:10]:
            print(f"    - {issue}")
        if len(ma["issues"]) > 10:
            print(f"    （还有 {len(ma['issues'])-10} 处省略）")

    eh = report["checks"]["ending_hook_uniqueness"]
    if eh.get("exact_dupes") or eh.get("similar_prefixes"):
        print()
        print("--- 钩子重复 ---")
        for d in eh.get("exact_dupes", []):
            print(f"  完全重复: '{d['hook']}'  出现于章 {d['chapters']}")
        for s2 in eh.get("similar_prefixes", []):
            print(f"  前缀相同: '{s2['prefix']}...'  出现于章 {s2['chapters']}")

    print()
    print("--- 修改建议 ---")
    for r in report["recommendations"]:
        print(f"  * {r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="VolumeValidator Demo")
    parser.add_argument("--novel-id", default=DEFAULT_NOVEL_ID, help="novel UUID")
    parser.add_argument("--volume", type=int, default=DEFAULT_VOLUME, help="要校验的卷序号")
    parser.add_argument("--json", action="store_true",
                        help="只输出 JSON 报告，不打印人类可读摘要（适合自动化管线）")
    args = parser.parse_args()

    novel_id = args.novel_id
    outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
    blueprint_path = os.path.join(outline_dir, "blueprint.json")
    cards_path = os.path.join(outline_dir, f"volume_{args.volume}_chapters.json")

    blueprint = load_json(blueprint_path)
    if not blueprint:
        print(f"[ERROR] 找不到蓝图：{blueprint_path}")
        return 1
    volume_payload = load_json(cards_path)
    if not volume_payload:
        print(f"[ERROR] 找不到卷 {args.volume} 的章节卡：{cards_path}")
        return 1

    chapter_range = volume_payload.get("chapter_range") or [0, 0]
    start_ch, end_ch = int(chapter_range[0]), int(chapter_range[1])

    chapter_texts = load_chapter_texts(novel_id, start_ch, end_ch)
    if not chapter_texts:
        print(f"[WARN] chapters_demo/ 中没有任何 chapter_{start_ch}..{end_ch}.txt，"
              f"将只校验 chapter cards（无法做主角/正文/白名单类检查）")

    validator = VolumeValidator()
    report = validator.process({
        "blueprint": blueprint,
        "volume_index": args.volume,
        "volume_payload": volume_payload,
        "chapter_texts": chapter_texts,
    })

    if report.get("error"):
        print(f"[ERROR] 校验失败：{report['error']}")
        return 1

    out_path = os.path.join(config.NOVELS_DIR, novel_id, "validation", f"volume_{args.volume}_report.json")
    save_json(out_path, report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
        print()
        print(f"[OK] 报告已落盘：{out_path}")

    return 0 if report["summary"]["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
