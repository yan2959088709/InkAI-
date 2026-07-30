"""
OutlinePlanner Demo —— 用现有 novel_id 的人物/标签/需求跑一次大纲规划

用法：
  python run_outline_demo.py
  python run_outline_demo.py --novel-id 8defce7e-38e6-4f01-9108-80643103876f
  python run_outline_demo.py --novel-id <id> --volumes 5 --no-cards
  python run_outline_demo.py --novel-id <id> --volume-only 2

特性：
- 完全独立运行，不触碰现有 31 个 agent 与 39 个 core 模块
- 产物落到 data/novels/<id>/outline/ 下：
    blueprint.json
    volume_<N>_chapters.json
- 终端输出"紧凑视图"，让你一眼看到大纲是否合理

退出码：
  0 = 成功
  1 = 数据缺失或参数错误
  2 = LLM 阶段失败
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any, Optional

import config
from core.outline_planner import OutlinePlanner


DEFAULT_NOVEL_ID = "8defce7e-38e6-4f01-9108-80643103876f"


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_spec_from_novel(novel_id: str, total_chapters_override: Optional[int],
                           volume_count_override: Optional[int]) -> Dict[str, Any]:
    novel_dir = os.path.join(config.NOVELS_DIR, novel_id)
    if not os.path.isdir(novel_dir):
        raise FileNotFoundError(f"找不到小说目录: {novel_dir}")

    metadata = load_json(os.path.join(novel_dir, "metadata.json")) or {}
    characters = load_json(os.path.join(novel_dir, "characters.json")) or {}
    storyline = load_json(os.path.join(novel_dir, "storyline.json")) or {}

    title = metadata.get("title") or "未命名作品"
    user_requirements = metadata.get("user_requirements") or ""
    tags = (metadata.get("tags") or {}).get("recommended_tags") or metadata.get("tags") or {}

    main_character = characters.get("main_character") or {}
    supporting_raw = characters.get("supporting_characters") or []
    supporting_characters = []
    for sup in supporting_raw:
        if isinstance(sup, dict):
            supporting_characters.append(sup)

    overall = storyline.get("overall_storyline") or {}
    world_setting = overall.get("world_setting") or {}
    themes = overall.get("themes") or []

    total_chapters = total_chapters_override or _infer_total_chapters(user_requirements, default=50)

    spec = {
        "title": title,
        "user_requirements": user_requirements,
        "total_chapters": total_chapters,
        "protagonist": main_character,
        "supporting_characters": supporting_characters,
        "tags": tags,
        "world_setting": world_setting,
        "themes": themes,
        # 把完整的 overall_storyline 作为 storyline_arc 一并传入，
        # 让 OutlinePlanner 能注入 act1/2/3、midpoint_crisis、climax 等剧情骨架，
        # 防止 LLM 自行划分高潮位置与卷间转折时偏离原始故事设计。
        "storyline_arc": overall,
    }
    if volume_count_override:
        spec["volume_count"] = volume_count_override
    return spec


def _infer_total_chapters(user_requirements: str, default: int) -> int:
    import re
    if not user_requirements:
        return default
    m = re.search(r"(\d{1,4})\s*章", user_requirements)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return default


def print_blueprint_compact(blueprint: Dict[str, Any]) -> None:
    meta = blueprint.get("meta", {})
    arc = blueprint.get("global_arc", {})
    volumes = blueprint.get("volumes", [])
    ledger = blueprint.get("global_foreshadow_ledger", [])

    print("\n" + "=" * 78)
    print(f"  📖 整本蓝图   {meta.get('title')}   "
          f"主角：{meta.get('protagonist_name')}   "
          f"{meta.get('total_chapters')}章 / {meta.get('volume_count')}卷")
    print("=" * 78)

    if blueprint.get("_fallback"):
        print("⚠️ 当前蓝图为兜底骨架（LLM 解析失败时启用），内容为空白模板。\n")

    print(f"  • 主题   ：{meta.get('core_theme')}")
    print(f"  • 基调   ：{meta.get('tone')}")
    print(f"  • 命名白名单：{', '.join(meta.get('name_whitelist', []))}")
    print(f"\n  ─ 三幕节奏 ─")
    print(f"     第一幕  {arc.get('act1_range')}    "
          f"第二幕 {arc.get('act2_range')}    "
          f"第三幕 {arc.get('act3_range')}    "
          f"中点：第{arc.get('midpoint_chapter')}章")
    print(f"     明线：{arc.get('main_thread')}")
    print(f"     暗线：{arc.get('sub_thread')}")

    print(f"\n  ─ 卷划分 ({len(volumes)} 卷) ─")
    for vol in volumes:
        cr = vol.get("chapter_range", [0, 0])
        print(f"\n  【卷{vol.get('index')}】 {vol.get('title')}    "
              f"第 {cr[0]}-{cr[1]} 章    [{vol.get('phase')}]")
        print(f"      目标   ：{vol.get('goal')}")
        print(f"      主冲突 ：{vol.get('core_conflict')}")
        milestones = vol.get("key_milestones", []) or []
        if milestones:
            print(f"      里程碑 ：")
            for m in milestones:
                print(f"          - {m}")
        plant = vol.get("foreshadow_plant_hints", []) or []
        payoff = vol.get("foreshadow_payoff_hints", []) or []
        if plant:
            print(f"      埋伏笔 ：{', '.join(plant)}")
        if payoff:
            print(f"      回伏笔 ：{', '.join(payoff)}")
        print(f"      卷末态 ：{vol.get('ending_state')}")

    print(f"\n  ─ 全局伏笔账本 ({len(ledger)} 条) ─")
    for item in ledger:
        print(f"      [{item.get('id')}] (重要性:{item.get('importance')})  "
              f"卷{item.get('plant_volume')} → 卷{item.get('payoff_volume')}    "
              f"{item.get('content')}")
    print("\n" + "=" * 78)


def print_volume_cards_compact(payload: Dict[str, Any]) -> None:
    vol_idx = payload.get("volume_index")
    vol_title = payload.get("volume_title")
    cards = payload.get("chapter_cards", [])

    print("\n" + "=" * 78)
    print(f"  📑 章节卡  卷{vol_idx} 《{vol_title}》   共 {len(cards)} 章")
    print("=" * 78)

    if payload.get("_fallback"):
        print("⚠️ 当前章节卡为兜底骨架（LLM 解析失败），仅含章号与角色字段。\n")

    seen_endings = set()
    for card in cards:
        ch_num = card.get("chapter_number")
        role = card.get("role")
        title = card.get("title")
        tension = card.get("tension_level")
        tone = card.get("tone")
        summary = card.get("summary")
        beats = card.get("beats", []) or []
        must = card.get("must_appear", {}) or {}
        plant = card.get("foreshadow_plant", []) or []
        payoff = card.get("foreshadow_payoff", []) or []
        ending = card.get("ending_hook", "")

        bar = "█" * int(tension or 0)
        print(f"\n  ── 第{ch_num:>3}章  [{role}]  张力 {tension}/10 {bar}  色调:{tone}")
        print(f"      标题：{title}")
        if summary:
            print(f"      概要：{summary}")
        if beats:
            print(f"      节拍：")
            for b in beats:
                print(f"          • {b}")
        if must:
            chars = must.get("characters", []) or []
            locs = must.get("locations", []) or []
            objs = must.get("objects", []) or []
            if chars:
                print(f"      必现人物：{', '.join(chars)}")
            if locs:
                print(f"      必现场景：{', '.join(locs)}")
            if objs:
                print(f"      必现物件：{', '.join(objs)}")
        if plant:
            print(f"      埋伏笔  ：{', '.join(plant)}")
        if payoff:
            print(f"      回伏笔  ：{', '.join(payoff)}")
        if ending:
            warn = "  ⚠️ 与同卷前章重复！" if ending in seen_endings else ""
            print(f"      钩子    ：{ending}{warn}")
            seen_endings.add(ending)

    print("\n" + "=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description="OutlinePlanner demo runner")
    parser.add_argument("--novel-id", default=DEFAULT_NOVEL_ID, help="要规划的小说 ID（默认使用现有的暗夜追凶）")
    parser.add_argument("--total-chapters", type=int, default=None, help="总章数（默认从 user_requirements 推断或 50）")
    parser.add_argument("--volumes", type=int, default=None, help="卷数（默认按章数推断）")
    parser.add_argument("--no-cards", action="store_true", help="只生成蓝图，不展开任何卷的章节卡")
    parser.add_argument("--volume-only", type=int, default=None,
                        help="只展开指定卷的章节卡（默认展开第 1 卷做样本）")
    args = parser.parse_args()

    print(f"\n[INFO] 加载小说数据：novel_id = {args.novel_id}")
    try:
        spec = build_spec_from_novel(args.novel_id, args.total_chapters, args.volumes)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1

    proto_name = spec.get("protagonist", {}).get("basic_info", {}).get("name", "")
    sup_names = [c.get("basic_info", {}).get("name") for c in spec.get("supporting_characters", [])]
    sup_names = [n for n in sup_names if n]
    print(f"[INFO] 标题：{spec['title']}")
    print(f"[INFO] 主角：{proto_name}    配角：{', '.join(sup_names)}")
    print(f"[INFO] 计划：{spec['total_chapters']} 章 / {spec.get('volume_count') or '自动'} 卷")
    print(f"[INFO] 标签：{json.dumps(spec.get('tags', {}), ensure_ascii=False)}")
    print(f"[INFO] 模型：{config.MODEL_NAME}    规划温度：{OutlinePlanner.PLANNER_TEMPERATURE}")
    print()

    planner = OutlinePlanner()

    print("[STEP 1/2] 调用 LLM 生成整本蓝图...")
    blueprint = planner.generate_blueprint(spec)
    if "error" in blueprint:
        print(f"[ERROR] 蓝图生成失败：{blueprint['error']}")
        return 2
    bp_path = OutlinePlanner.save_blueprint(args.novel_id, blueprint)
    print(f"[OK] 蓝图已保存：{bp_path}")
    print_blueprint_compact(blueprint)

    if args.no_cards:
        print("\n[INFO] --no-cards 已设置，跳过章节卡生成。")
        return 0

    target_volume_index = args.volume_only or 1
    volumes = blueprint.get("volumes", [])
    if not any(int(v.get("index", -1)) == target_volume_index for v in volumes):
        print(f"[WARN] 蓝图中没有 index={target_volume_index} 的卷，跳过章节卡生成。")
        return 0

    print(f"\n[STEP 2/2] 调用 LLM 展开卷 {target_volume_index} 的章节卡...")
    cards_payload = planner.generate_volume_chapter_cards(
        blueprint=blueprint,
        volume_index=target_volume_index,
        banned_endings=[],
    )
    if "error" in cards_payload:
        print(f"[ERROR] 章节卡生成失败：{cards_payload['error']}")
        return 2
    cards_path = OutlinePlanner.save_volume_cards(args.novel_id, target_volume_index, cards_payload)
    print(f"[OK] 章节卡已保存：{cards_path}")
    print_volume_cards_compact(cards_payload)

    print("\n[DONE] 大纲产出完成。请检查：")
    print(f"   - 蓝图     ：{bp_path}")
    print(f"   - 章节卡   ：{cards_path}")
    print("\n建议你重点看：")
    print("   1. 主角名是否正确（应为：%s）" % proto_name)
    print("   2. 卷数是否符合预期，每卷目标是否清晰、互不重复")
    print("   3. 全局伏笔账本是否合理（plant_volume < payoff_volume）")
    print("   4. 卷一章节卡的 ending_hook 是否各异（无 ⚠️ 标注 = OK）")
    print("   5. 每章 must_appear.characters 是否在 name_whitelist 内")
    return 0


if __name__ == "__main__":
    sys.exit(main())
