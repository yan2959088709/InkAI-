"""
run_init_novel.py —— 一键根据题材初始化一本新小说项目

输出：
  data/novels/<novel_id>/metadata.json
  data/novels/<novel_id>/characters.json
  data/novels/<novel_id>/storyline.json

可选：
  --also-blueprint   连带调用 OutlinePlanner 生成 blueprint.json（注入 GenrePack）

用法：
  python run_init_novel.py --genre xianxia --title 九霄道行 --protagonist 林朝歌
  python run_init_novel.py --genre detective --title 长夜终途 --protagonist 周深 --total-chapters 60 --also-blueprint
  python run_init_novel.py --list-genres

"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict

import config
from agents.storyline_generator import StorylineGeneratorAgent
from core.canon_checker import load_and_check, render_report_text
from core.genre_pack import GenrePack
from core.outline_planner import OutlinePlanner


def _wrap_title(title: str) -> str:
    title = title.strip()
    if not title:
        return ""
    if title.startswith("《") and title.endswith("》"):
        return title
    return f"《{title}》"


def build_three_files(spec: Dict[str, Any], pack: GenrePack, novel_id: str) -> Dict[str, Any]:
    """把 spec 拆成 metadata / characters / storyline 三件套（结构与现有 novels 目录兼容）。"""
    now = datetime.now().isoformat(timespec="seconds")

    proto = spec.get("protagonist") or {}
    proto_name = (proto.get("basic_info") or {}).get("name", "")
    supporting = spec.get("supporting_characters") or []

    metadata = {
        "novel_id": novel_id,
        "title": spec.get("title") or "",
        "user_requirements": spec.get("user_requirements") or "",
        "created_at": now,
        "updated_at": now,
        "status": "in_progress",
        "_genre": pack.name,
        "_genre_display": pack.display_name,
        "tags": {
            "recommended_tags": spec.get("tags") or {},
            "selected_tags": spec.get("tags") or {},
        },
        "main_character_name": proto_name,
        "supporting_character_names": [
            (s.get("basic_info") or {}).get("name", "") for s in supporting
        ],
        "total_chapters_planned": int(spec.get("total_chapters") or 50),
    }

    characters = {
        "main_character": proto,
        "supporting_characters": supporting,
        "_genre": pack.name,
    }

    storyline = {
        "overall_storyline": {
            "world_setting": spec.get("world_setting") or {},
            "themes": spec.get("themes") or [],
            "_seeded_by_genre": pack.name,
        },
    }

    return {
        "metadata": metadata,
        "characters": characters,
        "storyline": storyline,
    }


def write_three_files(novel_dir: str, payloads: Dict[str, Any]) -> None:
    os.makedirs(novel_dir, exist_ok=True)
    for key in ("metadata", "characters", "storyline"):
        path = os.path.join(novel_dir, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payloads[key], f, ensure_ascii=False, indent=2)
        print(f"[OK] 写入 {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="基于 GenrePack 一键初始化新小说项目")
    parser.add_argument("--list-genres", action="store_true", help="列出所有可用题材后退出")
    parser.add_argument("--genre", help="题材 name（对应 data/genres/<name>.json）")
    parser.add_argument("--title", help="作品标题（不含书名号也行，会自动加《》）")
    parser.add_argument("--protagonist", help="主角姓名")
    parser.add_argument("--total-chapters", type=int, default=50, help="总章数（默认 50）")
    parser.add_argument("--novel-id", default=None,
                        help="可选 novel_id；不填则自动生成 uuid4")
    parser.add_argument("--extra", default="",
                        help="附加在 user_requirements 末尾的自由文本（用户特别强调的设定）")
    parser.add_argument("--also-storyline", action="store_true",
                        help="调用 StorylineGeneratorAgent 把 storyline.json 从 GenrePack 骨架"
                             "展开为完整三幕剧（main_goal / core_conflict / act1-3 / first_module / subplot_hints）")
    parser.add_argument("--also-blueprint", action="store_true",
                        help="顺带调用 OutlinePlanner.generate_blueprint 落盘 blueprint.json")
    parser.add_argument("--force", action="store_true",
                        help="若 novel_dir 已存在，允许覆盖")
    parser.add_argument("--strict-canon", action="store_true",
                        help="档案一致性校验出现 ERROR 时直接终止（默认仅警告并继续）")
    parser.add_argument("--no-canon", action="store_true",
                        help="跳过档案一致性校验（不推荐）")
    args = parser.parse_args()

    if args.list_genres:
        names = GenrePack.list_registry()
        if not names:
            print(f"[WARN] {config.GENRES_DIR} 下还没有任何题材包，请先放置 *.json")
            return 0
        print(f"[INFO] 可用题材（共 {len(names)} 个）：")
        for n in names:
            try:
                p = GenrePack.from_registry(n)
                print(f"  - {n:18s}  {p.display_name}    {p.one_liner}")
            except Exception as exc:
                print(f"  - {n:18s}  [ERR] 无法加载：{exc}")
        return 0

    missing = [k for k in ("genre", "title", "protagonist") if not getattr(args, k)]
    if missing:
        parser.error("缺少必填参数：" + ", ".join(f"--{m.replace('_', '-')}" for m in missing))

    pack = GenrePack.from_registry(args.genre)
    if pack is None:
        print(f"[ERROR] 找不到题材包 '{args.genre}'。可用：{GenrePack.list_registry()}")
        return 1

    novel_id = args.novel_id or str(uuid.uuid4())
    novel_dir = os.path.join(config.NOVELS_DIR, novel_id)
    if os.path.exists(novel_dir) and not args.force:
        print(f"[ERROR] novel_dir 已存在：{novel_dir}（用 --force 覆盖）")
        return 2

    title = _wrap_title(args.title)
    spec = pack.render_spec(
        title=title,
        protagonist_name=args.protagonist.strip(),
        total_chapters=args.total_chapters,
        extra_user_requirements=args.extra,
    )

    print(f"[INFO] 题材：{pack.display_name} ({pack.name})")
    print(f"[INFO] novel_id={novel_id}")
    print(f"[INFO] 标题={title}  主角={args.protagonist}  总章={args.total_chapters}")

    payloads = build_three_files(spec, pack, novel_id)
    write_three_files(novel_dir, payloads)

    if args.also_storyline:
        print("\n=== 调用 StorylineGeneratorAgent 展开 storyline 骨架 ===")
        characters = payloads["characters"]
        main_name = (characters.get("main_character") or {}).get("basic_info", {}).get("name", "")
        sup_names = [
            (s.get("basic_info") or {}).get("name", "")
            for s in (characters.get("supporting_characters") or [])
        ]
        sup_names = [n for n in sup_names if n]
        # 在 user_requirements 末尾注入"角色名硬约束"，强制 LLM 只用注册名
        roster = ", ".join([main_name] + sup_names)
        constraint_block = (
            "\n\n【硬性约束 — 角色档案不可改写】\n"
            f"本作所有出场角色已在 characters.json 中注册，唯一合法的角色名清单为：{roster}。\n"
            "请在生成 storyline、first_module、subplot_hints 时严格遵循以下规则：\n"
            f"1. 主角必须使用『{main_name}』这个姓名，禁止改名或起别名；\n"
            "2. 涉及配角时，必须从上述清单中选用真实姓名，禁止凭空创造新角色名（如『林某某真人』『苏某某』『陈某某』等具名角色）；\n"
            "3. 若剧情确需新角色，请使用通用职务称谓（如『支队领导』『技术警员』『法医』等）而非具体姓名；\n"
            "4. 不得给已注册角色赋予与 characters.json 中 role 字段冲突的身份（如把『反派』写成『搭档』）；\n"
            "5. 角色性别必须与 characters.json 中的 gender 字段一致。"
        )
        spec_for_storyline = dict(spec)
        spec_for_storyline["user_requirements"] = (
            (spec.get("user_requirements") or "") + constraint_block
        )
        agent = StorylineGeneratorAgent()
        story_input = {
            "selected_tags": spec.get("tags") or {},
            "characters": characters,
            "user_requirements": spec_for_storyline["user_requirements"],
        }
        try:
            story_result = agent.process(story_input)
        except Exception as exc:
            print(f"[ERROR] storyline 展开失败：{exc}")
            return 5
        # 落盘——同时保留原 GenrePack 骨架的 themes / world_setting，作为 LLM 输出的兜底
        new_storyline = {
            "overall_storyline": story_result.get("overall_storyline") or {},
            "first_module": story_result.get("first_module") or {},
            "subplot_hints": story_result.get("subplot_hints") or {},
            "story_structure": story_result.get("story_structure") or {},
        }
        # 把 GenrePack 中的种子标记保留下来，方便后续追踪
        if not new_storyline["overall_storyline"].get("_seeded_by_genre"):
            new_storyline["overall_storyline"]["_seeded_by_genre"] = pack.name
        story_path = os.path.join(novel_dir, "storyline.json")
        with open(story_path, "w", encoding="utf-8") as f:
            json.dump(new_storyline, f, ensure_ascii=False, indent=2)
        print(f"[OK] 已展开并落盘：{story_path}")
        os_acts = new_storyline.get("overall_storyline") or {}
        print(f"     main_goal: {os_acts.get('main_goal', '<空>')[:80]}")
        print(f"     act1.setup: {(os_acts.get('act1') or {}).get('setup', '<空>')[:80]}")
        fm = new_storyline.get("first_module") or {}
        print(f"     first_module.title: {fm.get('chapter_title', '<空>')}")

    if not args.no_canon:
        print("\n=== 档案一致性校验（characters.json ↔ storyline.json） ===")
        canon_report = load_and_check(novel_dir, novel_id=novel_id)
        print(render_report_text(canon_report))
        report_path = os.path.join(novel_dir, "canon_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(canon_report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"[OK] 校验报告已落盘：{report_path}")
        if canon_report.has_errors():
            print(f"[WARN] 发现 {canon_report.summary.get('ERROR', 0)} 项 ERROR 级冲突，"
                  f"建议在生成 blueprint 之前先修正 characters.json / storyline.json。")
            if args.strict_canon:
                print("[FATAL] --strict-canon 已开启，因档案冲突中止流程。")
                return 4

    if args.also_blueprint:
        print("\n=== 调用 OutlinePlanner 生成 blueprint（带 GenrePack 注入） ===")
        planner = OutlinePlanner(genre_pack=pack)
        blueprint = planner.generate_blueprint(spec)
        if blueprint.get("error"):
            print(f"[ERROR] blueprint 生成失败：{blueprint['error']}")
            return 3
        out_dir = os.path.join(novel_dir, "outline")
        os.makedirs(out_dir, exist_ok=True)
        bp_path = os.path.join(out_dir, "blueprint.json")
        with open(bp_path, "w", encoding="utf-8") as f:
            json.dump(blueprint, f, ensure_ascii=False, indent=2)
        meta = blueprint.get("meta") or {}
        print(f"[OK] blueprint 已落盘：{bp_path}")
        print(f"     标题={meta.get('title')}  主角={meta.get('protagonist_name')}  "
              f"卷数={meta.get('volume_count')}  总章={meta.get('total_chapters')}")
        vols = blueprint.get("volumes") or (blueprint.get("global_arc") or {}).get("volumes") or []
        for v in vols[:5]:
            idx = v.get("volume_index") or v.get("index")
            print(f"     - 卷{idx} 《{v.get('title')}》  "
                  f"phase={v.get('phase')}  ch={v.get('chapter_range')}")
        if len(vols) > 5:
            print(f"     ... 共 {len(vols)} 卷")

    print(f"\n[DONE] 新小说项目已就位：{novel_dir}")
    print(f"       下一步：python run_outline_demo.py --novel-id {novel_id}"
          + ("" if args.also_blueprint else "    （生成 blueprint）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
