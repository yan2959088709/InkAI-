"""
ChapterCardWriter Demo —— 从 outline blueprint 中挑一张/一段 ChapterCard，试写章节

用法：
  # 单章模式
  python run_chapter_demo.py --novel-id <id> --volume 1 --chapter 11
  python run_chapter_demo.py --novel-id <id> --volume 1 --chapter 11 --target-words 2500

  # 批量模式（自动跨卷加载 chapter cards、自动累加 banned_endings、自动注入 recent_chapters）
  python run_chapter_demo.py --novel-id <id> --start-chapter 11 --end-chapter 20
  python run_chapter_demo.py --novel-id <id> --start-chapter 11 --end-chapter 25 --stop-on-fail

特性：
- 完全独立运行，不触碰现有 31 个 agent 与 39 个 core 模块
- 自动从 data/novels/<id>/outline/ 读 blueprint
- 如果指定卷的 chapter_cards 文件不存在，会现场调用 OutlinePlanner 生成
- 批量模式下：每章写完立即落盘，下一章会自动读取最新落盘文件作为 recent_chapters
- 产物落到 data/novels/<id>/chapters_demo/ 下：
    chapter_<N>.txt           单章正文
    chapter_<N>.meta.json     主角名/字数/校验报告等元数据

退出码：
  0 = 全部成功
  1 = 数据缺失或参数错误
  2 = 至少一章 LLM 阶段失败（批量模式默认继续，--stop-on-fail 才中断）
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Any, Optional

import config
from core.outline_planner import OutlinePlanner
from core.dynamic_knowledge_manager import DynamicKnowledgeManager
from agents.chapter_card_writer import ChapterCardWriter
from agents.volume_validator import VolumeValidator


DEFAULT_NOVEL_ID = "8defce7e-38e6-4f01-9108-80643103876f"
DEFAULT_VOLUME = 1
DEFAULT_CHAPTER = 1
DEFAULT_TARGET_WORDS = 2500
DEFAULT_RECENT_COUNT = 5


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def find_chapter_card(volume_payload: Dict[str, Any], chapter_number: int) -> Optional[Dict[str, Any]]:
    for card in volume_payload.get("chapter_cards", []) or []:
        if int(card.get("chapter_number", -1)) == int(chapter_number):
            return card
    return None


def find_volume_by_chapter(blueprint: Dict[str, Any], chapter_number: int) -> Optional[int]:
    """根据全局章节号定位它属于哪个卷"""
    for vol in blueprint.get("volumes", []) or []:
        cr = vol.get("chapter_range") or [0, 0]
        if int(cr[0]) <= chapter_number <= int(cr[1]):
            return int(vol.get("index", 0))
    return None


def load_recent_chapters(
    novel_id: str,
    current_chapter: int,
    count: int,
) -> List[Dict[str, Any]]:
    """从 chapters_demo/ 读最近 N 篇已生成章节作为上下文。

    文件格式约定（由本 demo 自身写入）：
        第一行 = title
        其余 = chapter body（中间空行）
    返回 ChapterCardWriter 接受的 schema：
        [{"chapter_number": int, "title": str, "content": str}, ...]
    """
    if count <= 0 or current_chapter <= 1:
        return []

    chapter_dir = os.path.join(config.NOVELS_DIR, novel_id, "chapters_demo")
    if not os.path.isdir(chapter_dir):
        return []

    results: List[Dict[str, Any]] = []
    for n in range(max(1, current_chapter - count), current_chapter):
        path = os.path.join(chapter_dir, f"chapter_{n}.txt")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            continue
        lines = raw.split("\n", 1)
        title = lines[0].strip() if lines else f"第{n}章"
        body = lines[1].lstrip("\n").rstrip() if len(lines) > 1 else ""
        if not body:
            continue
        results.append({
            "chapter_number": n,
            "title": title,
            "content": body,
        })
    return results


def collect_banned_endings(volume_payload: Dict[str, Any], up_to_chapter: int) -> List[str]:
    """收集本卷中 [start_ch, up_to_chapter-1] 已经用过的 ending_hook 句式"""
    used = []
    for card in volume_payload.get("chapter_cards", []) or []:
        ch = int(card.get("chapter_number", -1))
        if ch < up_to_chapter:
            ending = (card.get("ending_hook") or "").strip()
            if ending and ending not in used:
                used.append(ending)
    return used


def ensure_volume_cards(
    novel_id: str,
    blueprint: Dict[str, Any],
    volume_index: int,
    planner: OutlinePlanner,
) -> Optional[Dict[str, Any]]:
    """优先读现成的 volume_<N>_chapters.json，不存在就现场调 LLM 生成并落盘"""
    outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
    cards_path = os.path.join(outline_dir, f"volume_{volume_index}_chapters.json")
    payload = load_json(cards_path)
    if payload and payload.get("chapter_cards"):
        print(f"[INFO] 复用已存在的章节卡：{cards_path}")
        return payload

    print(f"[INFO] 未找到 {cards_path}，现场生成卷 {volume_index} 的章节卡 ...")
    payload = planner.generate_volume_chapter_cards(
        blueprint=blueprint,
        volume_index=volume_index,
        banned_endings=[],
    )
    if payload.get("error"):
        print(f"[ERROR] 生成章节卡失败：{payload['error']}")
        return None

    OutlinePlanner.save_volume_cards(novel_id, volume_index, payload)
    print(f"[INFO] 章节卡已落盘：{cards_path}")
    return payload


def print_chapter_card_compact(card: Dict[str, Any]) -> None:
    print("\n=== ChapterCard ===")
    print(f"  第 {card.get('chapter_number')} 章 / 卷 {card.get('volume')} / role={card.get('role')}")
    print(f"  标题：{card.get('title')}")
    print(f"  概要：{card.get('summary')}")
    print(f"  必出场：{card.get('must_appear', {})}")
    print(f"  beats：")
    for b in card.get("beats", []):
        print(f"    - {b}")
    print(f"  埋伏笔：{card.get('foreshadow_plant')}")
    print(f"  收伏笔：{card.get('foreshadow_payoff')}")
    print(f"  钩子：{card.get('ending_hook')}")
    print(f"  tone={card.get('tone')}  tension={card.get('tension_level')}")


def print_validation_compact(v: Dict[str, Any]) -> None:
    print("\n=== 校验结果 ===")
    flag = "[PASS]" if v.get("passed") else "[WARN]"
    print(f"  {flag} 通过={v.get('passed')}")
    print(f"  主角出现={v.get('protagonist_count')}（present={v.get('protagonist_present')}）")
    print(f"  字数={v.get('word_count')} / 目标={v.get('word_count_target')}（ok={v.get('word_count_ok')}）")
    print(f"  banned 命中={v.get('banned_hits')}")

    ma = v.get("must_appear") or {}
    if ma:
        for dim in ("characters", "locations", "objects"):
            d = ma.get(dim) or {}
            exp = d.get("expected") or []
            if not exp:
                continue
            ok_n = len(d.get("ok") or [])
            light_n = len(d.get("light") or [])
            miss_n = len(d.get("missing") or [])
            tag = "[OK]" if miss_n == 0 else "[MISS]"
            line = f"  must_appear.{dim}: {tag} 共{len(exp)}  正式出场={ok_n}  仅一笔带过={light_n}  完全缺失={miss_n}"
            if d.get("missing"):
                line += f"  缺失项={[m['name'] for m in d['missing']]}"
            print(line)


def process_one_chapter(
    novel_id: str,
    blueprint: Dict[str, Any],
    chapter_number: int,
    target_words: int,
    recent_count: int,
    planner: OutlinePlanner,
    writer: ChapterCardWriter,
    volume_cache: Dict[int, Dict[str, Any]],
    verbose: bool = True,
    revise: bool = False,
    dkm: Optional[DynamicKnowledgeManager] = None,
    character_profiles: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """单章写作完整流水线，可被单章/批量两种模式共用。

    返回 {"ok": bool, "chapter_number": int, "validation": {...}, "error": str|None,
          "word_count": int, "retried": bool}
    """
    volume_index = find_volume_by_chapter(blueprint, chapter_number)
    if volume_index is None:
        return {"ok": False, "chapter_number": chapter_number,
                "error": f"章节 {chapter_number} 不在任何卷的范围内"}

    if volume_index not in volume_cache:
        payload = ensure_volume_cards(novel_id, blueprint, volume_index, planner)
        if not payload:
            return {"ok": False, "chapter_number": chapter_number,
                    "error": f"卷 {volume_index} 章节卡加载/生成失败"}
        volume_cache[volume_index] = payload
    volume_payload = volume_cache[volume_index]

    target_card = find_chapter_card(volume_payload, chapter_number)
    if not target_card:
        avail = [c.get("chapter_number") for c in volume_payload.get("chapter_cards", [])]
        return {"ok": False, "chapter_number": chapter_number,
                "error": f"卷 {volume_index} 中找不到第 {chapter_number} 章，可用={avail}"}

    if verbose:
        print_chapter_card_compact(target_card)

    banned_endings = collect_banned_endings(volume_payload, up_to_chapter=chapter_number)
    if verbose:
        print(f"\n[INFO] 卷内已用 ending_hook（共 {len(banned_endings)} 条）")
        for b in banned_endings:
            print(f"  - {b}")

    recent_chapters = load_recent_chapters(novel_id, chapter_number, recent_count)
    if verbose:
        if recent_chapters:
            print(f"\n[INFO] 注入最近 {len(recent_chapters)} 章作为上下文：")
            for ch in recent_chapters:
                print(f"  - 第{ch['chapter_number']}章 《{ch['title']}》  正文 {len(ch['content'])} 字")
        else:
            print(f"\n[INFO] 未注入 recent_chapters（recent_count={recent_count}）")

    force_feedback: Optional[Dict[str, Any]] = None
    if revise:
        prev_meta_path = os.path.join(
            config.NOVELS_DIR, novel_id, "chapters_demo", f"chapter_{chapter_number}.meta.json"
        )
        prev_meta = load_json(prev_meta_path)
        if prev_meta and prev_meta.get("validation"):
            force_feedback = prev_meta["validation"]
            if verbose:
                print(f"\n[REVISE] 检测到上次 validation，将作为强制 retry_feedback 喂给 writer")
                summary_bits = []
                if force_feedback.get("must_characters_missing"):
                    summary_bits.append(f"缺角色={force_feedback['must_characters_missing']}")
                ma = force_feedback.get("must_appear") or {}
                for dim in ("locations", "objects"):
                    miss = [m["name"] for m in (ma.get(dim) or {}).get("missing") or []]
                    if miss:
                        summary_bits.append(f"缺{dim}={miss}")
                if force_feedback.get("banned_hits"):
                    summary_bits.append(f"钩子重复={force_feedback['banned_hits']}")
                if summary_bits:
                    print(f"[REVISE] 上次问题：{'; '.join(summary_bits)}")
        else:
            if verbose:
                print(f"\n[REVISE] 未找到 {prev_meta_path}，按普通新写处理")

    dynamic_state_block = ""
    if dkm is not None:
        snap = dkm.snapshot_for_chapter(chapter_number)
        dynamic_state_block = DynamicKnowledgeManager.format_snapshot_for_prompt(snap)
        if verbose and dynamic_state_block:
            print(f"\n[DKM] 截至 ch{snap['as_of_chapter']} 注入动态状态："
                  f"角色 {len(snap['active_characters'])} 个，道具 {len(snap['objects_in_play'])} 个，"
                  f"未回收伏笔 {len(snap['open_foreshadowings'])} 个，"
                  f"逾期 {len(snap['overdue_foreshadowings'])} 个")

    writer_input: Dict[str, Any] = {
        "chapter_card": target_card,
        "blueprint": blueprint,
        "recent_chapters": recent_chapters,
        "banned_endings": banned_endings,
        "style_anchor": "",
        "target_word_count": target_words,
        "force_revise_feedback": force_feedback,
        "dynamic_state_block": dynamic_state_block,
    }
    # 显式透传完整人物档案（最高优先级）。
    # 即便 blueprint 是早期生成、未带 _source_briefs 缓存，这里也能补齐。
    if character_profiles:
        writer_input["character_profiles"] = character_profiles
    result = writer.process(writer_input)

    if result.get("error"):
        return {"ok": False, "chapter_number": chapter_number,
                "error": result["error"]}

    chapter_dir = os.path.join(config.NOVELS_DIR, novel_id, "chapters_demo")
    text_path = os.path.join(chapter_dir, f"chapter_{chapter_number}.txt")
    meta_path = os.path.join(chapter_dir, f"chapter_{chapter_number}.meta.json")

    full_text = f"{result.get('title', '')}\n\n{result.get('chapter_content', '')}\n"
    save_text(text_path, full_text)
    save_json(meta_path, {
        "novel_id": novel_id,
        "volume": volume_index,
        "chapter_number": result.get("chapter_number"),
        "title": result.get("title"),
        "word_count": result.get("word_count"),
        "validation": result.get("validation"),
        "_generation": result.get("_generation"),
    })

    if dkm is not None:
        dkm.update_with_chapter(target_card, result.get("chapter_content") or "")
        dkm.save_state()
        if verbose:
            print(f"[DKM] 已增量更新动态状态至 ch{dkm.state['last_updated_chapter']} → {dkm.state_path}")

    if verbose:
        print(f"\n[OK] 正文已落盘：{text_path}")
        print(f"[OK] 元数据已落盘：{meta_path}")
        print_validation_compact(result.get("validation") or {})
        body = result.get("chapter_content") or ""
        print("\n=== 正文头 300 字 ===")
        print(body[:300].replace("\n", " "))
        print("\n=== 正文末 200 字 ===")
        print(body[-200:].replace("\n", " "))
        print(f"\n[INFO] 是否重写过：{(result.get('_generation') or {}).get('retried')}")

    validation = result.get("validation") or {}
    return {
        "ok": True,
        "chapter_number": chapter_number,
        "volume": volume_index,
        "title": result.get("title"),
        "word_count": result.get("word_count"),
        "validation": validation,
        "retried": bool((result.get("_generation") or {}).get("retried")),
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ChapterCardWriter Demo (single + batch)")
    parser.add_argument("--novel-id", default=DEFAULT_NOVEL_ID, help="novel UUID")
    parser.add_argument("--volume", type=int, default=DEFAULT_VOLUME,
                        help="（仅打印用）卷序号；批量模式下会按章号自动定位卷")
    parser.add_argument("--chapter", type=int, default=DEFAULT_CHAPTER,
                        help="单章模式下要写的章号；批量模式下被 --start-chapter 取代")
    parser.add_argument("--start-chapter", type=int, default=None,
                        help="批量模式起始章号（包含）")
    parser.add_argument("--end-chapter", type=int, default=None,
                        help="批量模式结束章号（包含）。仅指定 --end-chapter 时 --start-chapter 默认=--chapter")
    parser.add_argument("--target-words", type=int, default=DEFAULT_TARGET_WORDS, help="目标字数")
    parser.add_argument(
        "--recent-count", type=int, default=DEFAULT_RECENT_COUNT,
        help="向 writer 注入的最近章节数（默认 2）",
    )
    parser.add_argument(
        "--no-recent", action="store_true",
        help="禁用 recent_chapters 上下文（等价于 --recent-count 0）",
    )
    parser.add_argument(
        "--stop-on-fail", action="store_true",
        help="批量模式下任意一章失败即中断；默认是记录失败继续下一章",
    )
    parser.add_argument(
        "--quiet-each", action="store_true",
        help="批量模式下每章只打印一行摘要，详情写入 meta.json",
    )
    parser.add_argument(
        "--no-validate", action="store_true",
        help="批量模式收尾时不自动跑 VolumeValidator（默认会对涉及到的所有卷各跑一遍）",
    )
    parser.add_argument(
        "--revise", action="store_true",
        help="对已有正文的章重新生成：读 chapter_<N>.meta.json 里的 last validation，"
             "把'缺角色 / 缺关键道具 / 钩子重复'等问题作为 retry_feedback 强制传给 LLM。"
             "适合先批量生成→Validator 报告→针对硬遗漏章 --revise 修补的闭环。",
    )
    parser.add_argument(
        "--no-dynamic-state", action="store_true",
        help="不使用 DynamicKnowledgeManager（不读 state.json，不向 prompt 注入跨章状态，"
             "也不在写完后更新状态）。默认开启动态状态注入。",
    )
    args = parser.parse_args()

    novel_id = args.novel_id
    outline_dir = os.path.join(config.NOVELS_DIR, novel_id, "outline")
    blueprint_path = os.path.join(outline_dir, "blueprint.json")

    blueprint = load_json(blueprint_path)
    if not blueprint:
        print(f"[ERROR] 找不到蓝图：{blueprint_path}")
        print("       请先运行：python run_outline_demo.py --novel-id <id>")
        return 1

    print(f"[INFO] 已加载蓝图：{blueprint_path}")
    meta = blueprint.get("meta", {}) or {}
    print(f"[INFO] 标题={meta.get('title')}  主角={meta.get('protagonist_name')}  "
          f"卷数={meta.get('volume_count')}  总章={meta.get('total_chapters')}")

    # 显式加载人物档案——即便蓝图未带 _source_briefs（如旧蓝图），也能向 ChapterCardWriter 注入档案。
    # 这是把"人物身份/阵营/与主角关系"这类硬约束确保抵达正文 prompt 的最后一道兜底。
    characters_path = os.path.join(config.NOVELS_DIR, novel_id, "characters.json")
    raw_characters = load_json(characters_path) or {}
    character_profiles: Optional[Dict[str, Any]] = None
    if raw_characters:
        character_profiles = {
            "main_character": raw_characters.get("main_character") or {},
            "supporting_characters": raw_characters.get("supporting_characters") or [],
        }
        sup_count = len(character_profiles["supporting_characters"])
        main_present = bool(character_profiles["main_character"])
        print(f"[INFO] 已加载人物档案：{characters_path}（main={main_present}, supporting={sup_count}）")
    else:
        print(f"[WARN] 未找到 characters.json（{characters_path}）；"
              f"将不向 Writer 注入人物档案，请确认这是否符合预期")

    # 兼容旧蓝图：若蓝图未携带 _source_briefs，则在内存中临时回填，
    # 让 OutlinePlanner（重生成卷章节卡时）与 ChapterCardWriter 都能拿到完整档案。
    # 注意：只修改内存副本，不回写 blueprint.json，避免污染原蓝图文件。
    if "_source_briefs" not in blueprint:
        storyline_path = os.path.join(config.NOVELS_DIR, novel_id, "storyline.json")
        raw_storyline = load_json(storyline_path) or {}
        storyline_arc = raw_storyline.get("overall_storyline") or {}
        # 仅当至少一项有内容时才注入，避免出现孤零零的空标题
        if raw_characters or storyline_arc:
            blueprint["_source_briefs"] = OutlinePlanner._render_source_briefs({
                "protagonist": (raw_characters or {}).get("main_character") or {},
                "supporting_characters": (raw_characters or {}).get("supporting_characters") or [],
                "storyline_arc": storyline_arc,
            })
            print(f"[INFO] 旧蓝图未携带 _source_briefs，已在内存中回填（不会写回磁盘）")

    is_batch = args.end_chapter is not None
    if is_batch:
        start_ch = args.start_chapter if args.start_chapter is not None else args.chapter
        end_ch = args.end_chapter
        if end_ch < start_ch:
            print(f"[ERROR] --end-chapter ({end_ch}) < start ({start_ch})")
            return 1
        chapter_list = list(range(start_ch, end_ch + 1))
        print(f"[BATCH] 计划写作 {len(chapter_list)} 章：{start_ch}..{end_ch}")
    else:
        chapter_list = [args.chapter]

    recent_count = 0 if args.no_recent else max(0, args.recent_count)
    planner = OutlinePlanner()
    writer = ChapterCardWriter()
    volume_cache: Dict[int, Dict[str, Any]] = {}

    dkm: Optional[DynamicKnowledgeManager] = None
    if not args.no_dynamic_state:
        dkm = DynamicKnowledgeManager(novel_id=novel_id, blueprint=blueprint)
        loaded = dkm.load_state()
        print(f"[DKM] 动态状态：{'已从 ' + dkm.state_path + ' 加载' if loaded else '空状态（state.json 不存在，将随写作累加）'}"
              f"  当前 last_updated_chapter={dkm.state['last_updated_chapter']}")

    summaries: List[Dict[str, Any]] = []
    for idx, ch_num in enumerate(chapter_list, start=1):
        print()
        print("#" * 70)
        print(f"# [{idx}/{len(chapter_list)}] 第 {ch_num} 章")
        print("#" * 70)
        verbose = (not is_batch) or (not args.quiet_each)

        outcome = process_one_chapter(
            novel_id=novel_id,
            blueprint=blueprint,
            chapter_number=ch_num,
            target_words=args.target_words,
            recent_count=recent_count,
            planner=planner,
            writer=writer,
            volume_cache=volume_cache,
            verbose=verbose,
            revise=args.revise,
            dkm=dkm,
            character_profiles=character_profiles,
        )
        summaries.append(outcome)

        if not outcome["ok"]:
            print(f"[FAIL] 第 {ch_num} 章失败：{outcome['error']}")
            if args.stop_on_fail:
                print("[BATCH] --stop-on-fail 触发，中断剩余任务")
                break
        else:
            v = outcome["validation"]
            tag = "[PASS]" if v.get("passed") else "[WARN]"
            print(f"[DONE] 第{ch_num}章 {tag} 字数={outcome['word_count']} "
                  f"主角={v.get('protagonist_count')} retried={outcome['retried']}")

    if is_batch:
        print()
        print("=" * 70)
        print("[BATCH 总结]")
        print("=" * 70)
        ok_cnt = sum(1 for s in summaries if s["ok"])
        pass_cnt = sum(1 for s in summaries if s["ok"] and (s["validation"] or {}).get("passed"))
        retry_cnt = sum(1 for s in summaries if s["ok"] and s["retried"])
        print(f"完成 {ok_cnt}/{len(summaries)}  其中通过校验 {pass_cnt}  重写过 {retry_cnt}")
        for s in summaries:
            if s["ok"]:
                v = s["validation"] or {}
                tag = "PASS" if v.get("passed") else "WARN"
                print(f"  ch{s['chapter_number']:>3d} vol{s['volume']:>2d} [{tag}]  "
                      f"字数={s['word_count']:>5d}  主角={v.get('protagonist_count'):>3d}  "
                      f"banned={len(v.get('banned_hits') or [])}  retried={s['retried']}")
            else:
                print(f"  ch{s['chapter_number']:>3d} [FAIL] {s['error']}")
        if not args.no_validate:
            run_post_batch_validation(novel_id, blueprint, summaries, volume_cache, dkm=dkm)

        if ok_cnt < len(summaries):
            return 2
    else:
        return 0 if summaries and summaries[0]["ok"] else 2

    return 0


def run_post_batch_validation(
    novel_id: str,
    blueprint: Dict[str, Any],
    summaries: List[Dict[str, Any]],
    volume_cache: Dict[int, Dict[str, Any]],
    dkm: Optional[DynamicKnowledgeManager] = None,
) -> None:
    """批量收尾：对本次涉及到的所有卷各跑一次 VolumeValidator。

    报告写入 data/novels/<id>/validation/volume_<N>_report.json，
    并在控制台打印一份精简摘要（避免淹没批量日志）。
    """
    touched_volumes = sorted({s["volume"] for s in summaries if s.get("ok") and s.get("volume")})
    if not touched_volumes:
        return

    print()
    print("=" * 70)
    print(f"[POST-VALIDATE] 开始对涉及到的 {len(touched_volumes)} 个卷做整卷校验")
    print("=" * 70)

    validator = VolumeValidator()
    for vol_idx in touched_volumes:
        volume_payload = volume_cache.get(vol_idx)
        if not volume_payload:
            cards_path = os.path.join(config.NOVELS_DIR, novel_id, "outline", f"volume_{vol_idx}_chapters.json")
            volume_payload = load_json(cards_path)
        if not volume_payload:
            print(f"  [SKIP] 卷 {vol_idx} 找不到 chapter cards 文件")
            continue

        cr = volume_payload.get("chapter_range") or [0, 0]
        start_ch, end_ch = int(cr[0]), int(cr[1])

        chapter_dir = os.path.join(config.NOVELS_DIR, novel_id, "chapters_demo")
        chapter_texts: Dict[int, str] = {}
        for n in range(start_ch, end_ch + 1):
            p = os.path.join(chapter_dir, f"chapter_{n}.txt")
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    chapter_texts[n] = f.read()

        report = validator.process({
            "blueprint": blueprint,
            "volume_index": vol_idx,
            "volume_payload": volume_payload,
            "chapter_texts": chapter_texts,
            "dynamic_state": dkm,
        })
        if report.get("error"):
            print(f"  [ERROR] 卷 {vol_idx} 校验失败：{report['error']}")
            continue

        out_path = os.path.join(config.NOVELS_DIR, novel_id, "validation", f"volume_{vol_idx}_report.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        s = report["summary"]
        flag = "[PASS]" if s["passed"] else "[WARN]"
        print(f"\n  卷 {vol_idx}  《{report.get('volume_title') or ''}》  {flag}  "
              f"综合={s['overall_score']:.2f}/100  正文 {s['body_count']}/{s['chapter_count']} 章 共 {s['total_words']} 字")
        for k, v in report["checks"].items():
            sub_flag = "OK  " if v["passed"] else "WARN"
            print(f"    [{sub_flag}] {k:<28s}  score={v['score']:.1f}")
        if report["recommendations"]:
            print("    建议：")
            for r in report["recommendations"][:5]:
                print(f"      * {r}")
        print(f"    报告：{out_path}")


if __name__ == "__main__":
    sys.exit(main())
