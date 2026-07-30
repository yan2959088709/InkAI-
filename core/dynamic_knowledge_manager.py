"""
DynamicKnowledgeManager —— 跨章/跨卷的动态状态追踪器

设计原则：
- 零硬编码：所有"角色/道具/地点"实体都来自 ChapterCard.must_appear（OutlinePlanner 的产出），
  不预设任何中文姓名/常用词词典。
- 确定性：纯文件 IO + 字符串聚合，**不调用 LLM**。
- 增量优先：每写完一章调 update_with_chapter() 累加；也支持 rebuild_from_scratch()。
- 输出三类视图：
    1) Writer 用的章前快照（snapshot_for_chapter）
    2) Validator/Planner 用的健康报告（health_check）
    3) 持久化 JSON（落盘到 data/novels/<id>/dynamic_state/state.json）

数据结构（state.json）：
{
  "novel_id": str,
  "last_updated_chapter": int,
  "last_updated_at": iso str,
  "stats": {"total_chapters_indexed": int, "total_words": int},
  "characters": {
      <name>: {
          "first_appearance_ch": int,
          "last_appearance_ch": int,
          "appearance_chapters": [int, ...],
          "total_mentions": int,                       # body.count(name) 累加
          "currently_holds": [str, ...],               # 启发式：最近一次同章出场的 must_appear.objects
          "co_appearance": {<other_name>: int, ...}    # 同章共现次数
      }
  },
  "objects": {
      <name>: {
          "first_seen_ch": int,
          "last_seen_ch": int,
          "appearance_chapters": [int, ...],
          "holders_chain": [{"ch": int, "holder": str|None}, ...],
          "current_holder": str | None
      }
  },
  "locations": {
      <name>: {
          "first_seen_ch": int,
          "last_seen_ch": int,
          "appearance_chapters": [int, ...],
          "appearance_count": int,
          "is_recurring": bool
      }
  },
  "foreshadowings": {
      <fid>: {
          "id": str, "content": str, "importance": str,
          "plant_volume": int, "payoff_volume": int,
          "actually_planted_in_ch": int | None,
          "actually_paid_off_in_ch": int | None,
          "age_chapters": int | None,
          "status": "open" | "planted" | "closed" | "overdue"
      }
  },
  "events_timeline": [
      {"ch": int, "volume": int, "title": str, "summary": str, "tone": str, "tension": int}
  ]
}
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json
import os

import config
from utils.logger import get_logger

_logger = get_logger("dynamic_knowledge_manager")


# 启发式参数（保留为模块常量，外层可改）
RECURRING_LOCATION_THRESHOLD = 3       # 出现 >= 3 章算常驻场景
FORESHADOW_OVERDUE_AGE = 12            # 埋下后 >12 章未回收即标 overdue
DEFAULT_SNAPSHOT_RECENT_EVENTS = 5     # snapshot 默认带最近 N 章 summary
DEFAULT_SNAPSHOT_TOP_CHARACTERS = 8    # snapshot 默认带活跃度 Top N 角色
DEFAULT_SNAPSHOT_OBJECTS_PER_CHARACTER = 6  # 每个角色最多展示的"在手道具"数（按最近持有截断）
DEFAULT_SNAPSHOT_RECENT_OBJECT_WINDOW = 5   # 道具"近 N 章内出现过"才视为仍在剧情中
HEALTH_OBJECT_LOST_GAP = 10            # 道具 gap >= 该值才算 lost
HEALTH_OBJECT_LOST_MIN_APPEARANCES = 2 # 道具至少出现过 N 章，才纳入 lost 检测（过滤一次性装饰）


class DynamicKnowledgeManager:
    """跨章动态知识库

    刻意**不继承 BaseAgent**：
    - 本类零 LLM 调用，BaseAgent 提供的 client/temperature 等能力一律不需要
    - 继承 BaseAgent 会让 core/__init__.py 在 base_agent.py 还没初始化时就触发循环导入

    用法：
        dkm = DynamicKnowledgeManager(novel_id="...", blueprint=bp)
        dkm.load_state()                                      # 已有就读盘，没有就空状态
        dkm.update_with_chapter(chapter_card, chapter_body)   # 每写完一章
        dkm.save_state()
        snap = dkm.snapshot_for_chapter(target_chapter=20)    # 写下一章前
        prompt_block = dkm.format_snapshot_for_prompt(snap)
    """

    STATE_DIR = "dynamic_state"
    STATE_FILENAME = "state.json"

    def __init__(self, novel_id: str, blueprint: Optional[Dict[str, Any]] = None):
        self.name = "动态知识库管理"
        self.novel_id = novel_id
        self.blueprint = blueprint or {}
        self.state: Dict[str, Any] = self._empty_state()

    def log(self, msg: str) -> None:
        _logger.info(f"[{self.name}] {msg}")

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    @property
    def state_path(self) -> str:
        return os.path.join(config.NOVELS_DIR, self.novel_id, self.STATE_DIR, self.STATE_FILENAME)

    def load_state(self) -> bool:
        """从盘上读，若没有则保留空状态。返回是否真的读到了。"""
        if not os.path.exists(self.state_path):
            self.state = self._empty_state()
            return False
        with open(self.state_path, "r", encoding="utf-8") as f:
            self.state = json.load(f)
        # 兼容性：补齐缺失键
        empty = self._empty_state()
        for k, v in empty.items():
            self.state.setdefault(k, v)
        return True

    def save_state(self) -> str:
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        self.state["last_updated_at"] = datetime.now().isoformat(timespec="seconds")
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
        return self.state_path

    def _empty_state(self) -> Dict[str, Any]:
        # 把 blueprint 里的伏笔账本预填进去（status=open）
        forshadowings: Dict[str, Any] = {}
        for fl in (self.blueprint.get("global_foreshadow_ledger") or []):
            fid = fl.get("id")
            if not fid:
                continue
            forshadowings[fid] = {
                "id": fid,
                "content": fl.get("content", ""),
                "importance": fl.get("importance", "medium"),
                "plant_volume": fl.get("plant_volume"),
                "payoff_volume": fl.get("payoff_volume"),
                "actually_planted_in_ch": None,
                "actually_paid_off_in_ch": None,
                "age_chapters": None,
                "status": "open",
            }
        return {
            "novel_id": self.novel_id,
            "last_updated_chapter": 0,
            "last_updated_at": None,
            "stats": {"total_chapters_indexed": 0, "total_words": 0},
            "characters": {},
            "objects": {},
            "locations": {},
            "foreshadowings": forshadowings,
            "events_timeline": [],
        }

    # ------------------------------------------------------------------
    # 单章增量
    # ------------------------------------------------------------------
    def update_with_chapter(self, chapter_card: Dict[str, Any], chapter_body: str) -> None:
        ch = int(chapter_card.get("chapter_number") or 0)
        if ch <= 0:
            return
        body = chapter_body or ""
        vol = int(chapter_card.get("volume") or 0)
        ma = chapter_card.get("must_appear") or {}
        characters: List[str] = [c for c in (ma.get("characters") or []) if c]
        objects: List[str] = [o for o in (ma.get("objects") or []) if o]
        locations: List[str] = [l for l in (ma.get("locations") or []) if l]

        # 1) characters
        for name in characters:
            rec = self.state["characters"].setdefault(name, {
                "first_appearance_ch": ch,
                "last_appearance_ch": ch,
                "appearance_chapters": [],
                "total_mentions": 0,
                "currently_holds": [],
                "co_appearance": {},
            })
            rec["first_appearance_ch"] = min(rec["first_appearance_ch"], ch)
            rec["last_appearance_ch"] = max(rec["last_appearance_ch"], ch)
            if ch not in rec["appearance_chapters"]:
                rec["appearance_chapters"].append(ch)
                rec["appearance_chapters"].sort()
            rec["total_mentions"] += body.count(name)
            # 共现：本章其它角色 +1
            for other in characters:
                if other == name:
                    continue
                rec["co_appearance"][other] = rec["co_appearance"].get(other, 0) + 1
            # 道具持有者启发式：本章主角第一位接管 must_appear.objects
            # 只把"本章首次出场"的对象加进 currently_holds，避免重复
            if characters and name == characters[0]:
                for obj in objects:
                    if obj not in rec["currently_holds"]:
                        rec["currently_holds"].append(obj)

        # 2) objects
        primary_holder = characters[0] if characters else None
        for obj in objects:
            rec = self.state["objects"].setdefault(obj, {
                "first_seen_ch": ch,
                "last_seen_ch": ch,
                "appearance_chapters": [],
                "holders_chain": [],
                "current_holder": None,
            })
            rec["first_seen_ch"] = min(rec["first_seen_ch"], ch)
            rec["last_seen_ch"] = max(rec["last_seen_ch"], ch)
            if ch not in rec["appearance_chapters"]:
                rec["appearance_chapters"].append(ch)
                rec["appearance_chapters"].sort()
            # 持有链：仅在 holder 发生变化时追加
            last = rec["holders_chain"][-1] if rec["holders_chain"] else None
            if not last or last.get("holder") != primary_holder or last.get("ch") != ch:
                if not last or last.get("holder") != primary_holder:
                    rec["holders_chain"].append({"ch": ch, "holder": primary_holder})
            rec["current_holder"] = primary_holder

        # 3) locations
        for loc in locations:
            rec = self.state["locations"].setdefault(loc, {
                "first_seen_ch": ch,
                "last_seen_ch": ch,
                "appearance_chapters": [],
                "appearance_count": 0,
                "is_recurring": False,
            })
            rec["first_seen_ch"] = min(rec["first_seen_ch"], ch)
            rec["last_seen_ch"] = max(rec["last_seen_ch"], ch)
            if ch not in rec["appearance_chapters"]:
                rec["appearance_chapters"].append(ch)
                rec["appearance_chapters"].sort()
            rec["appearance_count"] = len(rec["appearance_chapters"])
            rec["is_recurring"] = rec["appearance_count"] >= RECURRING_LOCATION_THRESHOLD

        # 4) foreshadowings：按卡片字段更新生命周期
        for raw_ref in (chapter_card.get("foreshadow_plant") or []):
            fid = self._resolve_foreshadow_id(raw_ref, kind="plant", ch=ch)
            if fid is None:
                continue
            f = self.state["foreshadowings"].setdefault(fid, {
                "id": fid, "content": "", "importance": "medium",
                "plant_volume": vol, "payoff_volume": None,
                "actually_planted_in_ch": None, "actually_paid_off_in_ch": None,
                "age_chapters": None, "status": "open",
            })
            if f.get("actually_planted_in_ch") is None or ch < f["actually_planted_in_ch"]:
                f["actually_planted_in_ch"] = ch
            if f.get("status") == "open":
                f["status"] = "planted"

        for raw_ref in (chapter_card.get("foreshadow_payoff") or []):
            fid = self._resolve_foreshadow_id(raw_ref, kind="payoff", ch=ch)
            if fid is None:
                continue
            f = self.state["foreshadowings"].setdefault(fid, {
                "id": fid, "content": "", "importance": "medium",
                "plant_volume": None, "payoff_volume": vol,
                "actually_planted_in_ch": None, "actually_paid_off_in_ch": None,
                "age_chapters": None, "status": "open",
            })
            if f.get("actually_paid_off_in_ch") is None or ch > f["actually_paid_off_in_ch"]:
                f["actually_paid_off_in_ch"] = ch
            f["status"] = "closed"

        # 5) events timeline
        existing_chs = {e.get("ch") for e in self.state["events_timeline"]}
        if ch not in existing_chs:
            self.state["events_timeline"].append({
                "ch": ch,
                "volume": vol,
                "title": chapter_card.get("title", ""),
                "summary": chapter_card.get("summary", ""),
                "tone": chapter_card.get("tone", ""),
                "tension": chapter_card.get("tension_level", 0),
            })
            self.state["events_timeline"].sort(key=lambda e: e["ch"])

        # 6) stats
        self.state["last_updated_chapter"] = max(self.state["last_updated_chapter"], ch)
        self.state["stats"]["total_chapters_indexed"] = len({e["ch"] for e in self.state["events_timeline"]})
        self.state["stats"]["total_words"] = self.state["stats"].get("total_words", 0) + len(body)

        # 7) 全局 foreshadow age + overdue 推导（每次都跑，便宜）
        self._refresh_foreshadow_ages()

    @staticmethod
    def _looks_like_canonical_id(s: str) -> bool:
        """规范 ID：短（≤8）、纯 ASCII、且含至少一个字母。如 F03 / Y12 / FX01。"""
        if not isinstance(s, str):
            return False
        s = s.strip()
        if not (0 < len(s) <= 8):
            return False
        if not all(ord(c) < 128 for c in s):
            return False
        if not any(c.isalpha() for c in s):
            return False
        return True

    def _resolve_foreshadow_id(self, raw: Any, kind: str, ch: int) -> Optional[str]:
        """把 LLM 在 chapter_card.foreshadow_plant/payoff 写的字符串规范化为 ledger 中真正的 fid。

        规则（按优先级）：
        1) 字符串本身是规范 ID 且已存在于 self.state["foreshadowings"] → 直接用
        2) 字符串本身是规范 ID 但状态里没有 → 也接受（视为新增孤儿伏笔，但记 warn）
        3) 字符串看起来是"内容描述"（含中文/超长）：
           尝试在已有 foreshadowings 中按 content 双向包含匹配，命中即返回 ledger fid
        4) 都不行：丢弃并 warn，避免污染状态（曾经把整段中文当 fid 的脏数据问题）
        """
        if raw is None:
            return None
        s = str(raw).strip()
        if not s:
            return None

        # 拆出可能的"前缀 ID"，例如 "F03 - 账本中的空白页" → "F03"
        head = s.split()[0].split("-")[0].split("：")[0].split(":")[0].strip()
        candidates = [s, head]

        existing = self.state.get("foreshadowings") or {}

        # 1+2) 任一候选是规范 ID
        for c in candidates:
            if self._looks_like_canonical_id(c):
                if c in existing:
                    return c
                # 规范 ID 但 ledger 没有：当作新增孤儿，warn 一次
                self.log(
                    f"[ID-WARN] ch{ch} {kind} 引用了 ledger 之外的规范 ID '{c}'，已作为新增伏笔登记"
                )
                return c

        # 3) 在 ledger 中按 content 模糊匹配
        s_norm = s.replace("（", "(").replace("）", ")").strip()
        for fid, rec in existing.items():
            content = (rec.get("content") or "").strip()
            if not content:
                continue
            if s_norm == content or s_norm in content or content in s_norm:
                self.log(
                    f"[ID-MAP] ch{ch} {kind} 描述 '{s[:20]}...' 已映射到 ledger 中的 {fid}"
                )
                return fid

        # 4) 真·脏数据
        self.log(
            f"[ID-DROP] ch{ch} {kind} 引用 '{s[:30]}...' 既非规范 ID 也无 ledger 内容匹配，已丢弃"
        )
        return None

    def _refresh_foreshadow_ages(self) -> None:
        cur = self.state["last_updated_chapter"]
        for f in self.state["foreshadowings"].values():
            planted = f.get("actually_planted_in_ch")
            paid = f.get("actually_paid_off_in_ch")
            if planted and paid and paid >= planted:
                f["age_chapters"] = paid - planted
                f["status"] = "closed"
            elif planted and not paid:
                f["age_chapters"] = max(0, cur - planted)
                if f["age_chapters"] > FORESHADOW_OVERDUE_AGE:
                    f["status"] = "overdue"
                else:
                    f["status"] = "planted"
            elif not planted:
                f["age_chapters"] = None
                f["status"] = "open"

    # ------------------------------------------------------------------
    # 重建
    # ------------------------------------------------------------------
    def rebuild_from_scratch(
        self,
        chapter_pairs: Iterable[Tuple[Dict[str, Any], str]],
    ) -> None:
        """根据 [(chapter_card, body), ...] 重置状态后逐章 update。

        chapter_pairs 必须按章号升序传入。
        """
        self.state = self._empty_state()
        for card, body in chapter_pairs:
            self.update_with_chapter(card, body)

    # ------------------------------------------------------------------
    # 输出 1：Writer 用的快照
    # ------------------------------------------------------------------
    def snapshot_for_chapter(
        self,
        target_chapter: int,
        recent_events: int = DEFAULT_SNAPSHOT_RECENT_EVENTS,
        top_characters: int = DEFAULT_SNAPSHOT_TOP_CHARACTERS,
    ) -> Dict[str, Any]:
        """返回截至 target_chapter-1 时的世界状态快照。

        注意：状态本身按 last_updated_chapter 计算，调用方有责任
        在调用前 update 完所有 < target_chapter 的章。
        """
        cur = min(self.state["last_updated_chapter"], target_chapter - 1)

        # ----- 道具索引（用于反查角色 in-hand）：按 cur 过滤 last_seen，展示最近窗口内仍在场的 -----
        objs_in_play_idx: Dict[str, Dict[str, Any]] = {}
        objs = []
        for name, rec in self.state["objects"].items():
            chs = [c for c in (rec.get("appearance_chapters") or []) if c <= cur]
            if not chs:
                continue
            last_ch = max(chs)
            o = {
                "name": name,
                "first_ch": min(chs),
                "last_ch": last_ch,
                "current_holder": rec.get("current_holder"),
                "appearance_count": len(chs),
                "chapters_since_last": cur - last_ch,
            }
            objs.append(o)
            objs_in_play_idx[name] = o
        objs.sort(key=lambda o: o["last_ch"], reverse=True)
        # "在剧情中流动"= 最近 N 章内出现过的，截断展示
        objects_in_play = [
            o for o in objs if o["chapters_since_last"] <= DEFAULT_SNAPSHOT_RECENT_OBJECT_WINDOW
        ]

        # ----- 角色：严格按 cur 过滤 appearance_chapters 后再算 last_ch / count -----
        chars = []
        for name, rec in self.state["characters"].items():
            chs = [c for c in (rec.get("appearance_chapters") or []) if c <= cur]
            if not chs:
                continue
            last_ch = max(chs)
            # currently_holds 只保留"近 N 章 must_appear.objects 里仍属于该角色的"，最多 K 个
            held_recent = [
                obj for obj in (rec.get("currently_holds") or [])
                if obj in objs_in_play_idx
                   and objs_in_play_idx[obj]["chapters_since_last"] <= DEFAULT_SNAPSHOT_RECENT_OBJECT_WINDOW
            ]
            held_recent_sorted = sorted(
                held_recent, key=lambda n: -objs_in_play_idx[n]["last_ch"]
            )[:DEFAULT_SNAPSHOT_OBJECTS_PER_CHARACTER]
            chars.append({
                "name": name,
                "first_ch": min(chs),
                "last_ch": last_ch,
                "appearance_count": len(chs),
                "total_mentions": rec.get("total_mentions", 0),
                "currently_holds": held_recent_sorted,
                "chapters_since_last": cur - last_ch,
            })
        chars.sort(key=lambda c: (c["appearance_count"], c["total_mentions"]), reverse=True)
        active_chars = chars[:top_characters]
        ghost_chars = [c for c in chars if c["chapters_since_last"] >= 5 and c["appearance_count"] >= 1]

        # ----- 地点：同样按 cur 过滤 -----
        locs = []
        for name, rec in self.state["locations"].items():
            chs = [c for c in (rec.get("appearance_chapters") or []) if c <= cur]
            if not chs:
                continue
            locs.append({
                "name": name,
                "appearance_count": len(chs),
                "last_ch": max(chs),
            })
        locs.sort(key=lambda l: l["appearance_count"], reverse=True)
        recurring_locs = [l for l in locs if l["appearance_count"] >= RECURRING_LOCATION_THRESHOLD]

        # 伏笔分桶
        open_or_planted = []
        overdue = []
        recently_closed = []
        for f in self.state["foreshadowings"].values():
            planted = f.get("actually_planted_in_ch")
            paid = f.get("actually_paid_off_in_ch")
            status = f.get("status")
            if status == "closed" and paid and paid <= cur and paid >= cur - 5:
                recently_closed.append(f)
            elif status == "overdue":
                overdue.append(f)
            elif status in ("open", "planted"):
                # 只展示已经"应该埋下或已埋下"的（payoff_volume 在当前及以后任意，都列）
                open_or_planted.append(f)

        open_or_planted.sort(key=lambda f: (-(f.get("age_chapters") or 0), f.get("id") or ""))
        overdue.sort(key=lambda f: -(f.get("age_chapters") or 0))

        # 事件时间线（最近 N 章）
        timeline = [e for e in self.state["events_timeline"] if e["ch"] <= cur]
        recent = timeline[-recent_events:] if recent_events > 0 else []

        return {
            "as_of_chapter": cur,
            "target_chapter": target_chapter,
            "active_characters": active_chars,
            "ghost_characters": ghost_chars,
            "objects_in_play": objects_in_play,
            "all_objects": objs,
            "recurring_locations": recurring_locs,
            "all_locations": locs,
            "open_foreshadowings": open_or_planted,
            "overdue_foreshadowings": overdue,
            "recently_closed_foreshadowings": recently_closed,
            "recent_events": recent,
        }

    # ------------------------------------------------------------------
    # 输出 2：渲染成 prompt 文本
    # ------------------------------------------------------------------
    @staticmethod
    def format_snapshot_for_prompt(snapshot: Dict[str, Any]) -> str:
        """把 snapshot dict 渲染成可直接拼接到 LLM prompt 里的中文 markdown 块。

        刻意保持紧凑（避免吞 context），重点突出"必须保持一致的状态"。
        """
        lines: List[str] = []
        cur = snapshot.get("as_of_chapter", 0)
        tgt = snapshot.get("target_chapter", cur + 1)
        lines.append(f"=== 截至第 {cur} 章末的世界状态（写第 {tgt} 章必须沿用，不可矛盾） ===")

        # 角色
        ac = snapshot.get("active_characters") or []
        if ac:
            lines.append("\n[活跃角色 · 名字 · 已出场章数 · 当前持有的关键物 · 距上次出场已过章]：")
            for c in ac:
                holds = "、".join(c["currently_holds"]) if c["currently_holds"] else "无"
                lines.append(
                    f"  - {c['name']}：出场 {c['appearance_count']} 章（首{c['first_ch']}/末{c['last_ch']}）"
                    f"，手中：{holds}，已隔 {c['chapters_since_last']} 章未出场"
                )

        gc = snapshot.get("ghost_characters") or []
        if gc:
            names = "、".join(c["name"] for c in gc[:6])
            lines.append(f"\n[长时间未出场角色（请勿凭空让他们再出现，除非剧情需要召回）]：{names}")

        # 道具持有链
        objs = snapshot.get("objects_in_play") or []
        if objs:
            lines.append("\n[当前在剧情中流动的关键道具 · 持有者 · 上次出现章]：")
            for o in objs[:10]:
                holder = o.get("current_holder") or "未知"
                lines.append(f"  - {o['name']}（持有：{holder}，上次出现 ch{o['last_ch']}）")

        # 常驻场景
        rl = snapshot.get("recurring_locations") or []
        if rl:
            names = "、".join(f"{l['name']}({l['appearance_count']}次)" for l in rl[:6])
            lines.append(f"\n[常驻场景，可直接引用不必重新介绍]：{names}")

        # 伏笔
        def _fmt_fid_content(f: Dict[str, Any]) -> str:
            """容错渲染：content 优先；若为空则用 id 作为内容；
            若 id 看起来不是规范的 ID（超长 / 含中文），整体作为 content 显示并标记 ID="?"。"""
            fid = f.get("id") or "?"
            content = (f.get("content") or "").strip()
            looks_like_real_id = (
                isinstance(fid, str)
                and 0 < len(fid) <= 8
                and all(ord(c) < 128 for c in fid)
            )
            if not looks_like_real_id:
                # 这是脏数据：fid 本身就是描述
                return f"[?|{f.get('importance','?')}] {fid}"
            if not content:
                content = "(未提供描述，仅在某 ChapterCard.foreshadow_plant 中按 ID 引用)"
            return f"[{fid}|{f.get('importance','?')}] {content}"

        op = snapshot.get("open_foreshadowings") or []
        if op:
            lines.append("\n[未回收伏笔（请勿与之矛盾；若到回收时机请按 ChapterCard.foreshadow_payoff 兑现）]：")
            for f in op[:8]:
                age = f.get("age_chapters")
                age_s = f"已搁置{age}章" if age is not None else "尚未埋下"
                pv = f.get("plant_volume") or "?"
                yv = f.get("payoff_volume") or "?"
                lines.append(
                    f"  - {_fmt_fid_content(f)}（计划 vol{pv} 埋 → vol{yv} 收，{age_s}）"
                )

        od = snapshot.get("overdue_foreshadowings") or []
        if od:
            lines.append("\n[⚠️ 已逾期未回收伏笔 —— 若本章可承接请优先回收]：")
            for f in od[:5]:
                lines.append(f"  - {_fmt_fid_content(f)}（已搁置 {f.get('age_chapters')} 章）")

        # 最近事件
        re_ = snapshot.get("recent_events") or []
        if re_:
            lines.append("\n[最近若干章已发生的关键事件（避免情节回退/重复）]：")
            for e in re_:
                lines.append(f"  - 第{e['ch']}章《{e.get('title','')}》：{e.get('summary','')}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 输出 3：健康检查
    # ------------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        """跨卷一致性体检。返回 issues 列表与简要统计。"""
        issues: List[Dict[str, Any]] = []

        # 1) 逾期伏笔
        for f in self.state["foreshadowings"].values():
            if f.get("status") == "overdue":
                issues.append({
                    "kind": "foreshadow_overdue",
                    "severity": "high" if f.get("importance") == "high" else "medium",
                    "id": f["id"],
                    "message": (
                        f"伏笔 {f['id']}（{f.get('content','')}）于 ch{f.get('actually_planted_in_ch')} 埋下，"
                        f"已搁置 {f.get('age_chapters')} 章未回收"
                    ),
                })

        # 2) 计划与实际不符（plant_volume / payoff_volume vs 实际章号）
        for f in self.state["foreshadowings"].values():
            pv = f.get("plant_volume")
            actual_p = f.get("actually_planted_in_ch")
            if pv and actual_p:
                vol_of_actual = self._chapter_to_volume(actual_p)
                if vol_of_actual and vol_of_actual != pv:
                    issues.append({
                        "kind": "foreshadow_plant_volume_mismatch",
                        "severity": "low",
                        "id": f["id"],
                        "message": f"伏笔 {f['id']} 计划在 vol{pv} 埋下，实际埋于 ch{actual_p}（vol{vol_of_actual}）",
                    })

        # 3) 幽灵角色：出场过 1-2 章后再也没出现，且已过去 8 章
        cur = self.state["last_updated_chapter"]
        for name, rec in self.state["characters"].items():
            gap = cur - rec["last_appearance_ch"]
            if gap >= 8 and len(rec["appearance_chapters"]) <= 2:
                issues.append({
                    "kind": "ghost_character",
                    "severity": "low",
                    "id": name,
                    "message": (
                        f"角色 {name} 仅出场 {len(rec['appearance_chapters'])} 章"
                        f"（最后于 ch{rec['last_appearance_ch']}），已隔 {gap} 章未再出现"
                    ),
                })

        # 4) 道具陷入"消失"：曾出现过 >=2 章的道具（视为剧情承重），10 章以上未再出现
        # 一次性出现的道具（如某章用过的"打火机""烧杯"）不算异常，避免噪声淹没。
        for name, rec in self.state["objects"].items():
            gap = cur - rec["last_seen_ch"]
            if (
                gap >= HEALTH_OBJECT_LOST_GAP
                and len(rec["appearance_chapters"]) >= HEALTH_OBJECT_LOST_MIN_APPEARANCES
            ):
                issues.append({
                    "kind": "object_lost",
                    "severity": "low",
                    "id": name,
                    "message": (
                        f"关键道具 {name} 出场 {len(rec['appearance_chapters'])} 章后，"
                        f"自 ch{rec['last_seen_ch']} 已 {gap} 章未再出现"
                    ),
                })

        # 排序：高 > 中 > 低
        sev_rank = {"high": 0, "medium": 1, "low": 2}
        issues.sort(key=lambda i: sev_rank.get(i.get("severity"), 3))
        
        return {
            "as_of_chapter": cur,
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "high": sum(1 for i in issues if i["severity"] == "high"),
                "medium": sum(1 for i in issues if i["severity"] == "medium"),
                "low": sum(1 for i in issues if i["severity"] == "low"),
                "characters_count": len(self.state["characters"]),
                "objects_count": len(self.state["objects"]),
                "locations_count": len(self.state["locations"]),
                "foreshadowings_open": sum(
                    1 for f in self.state["foreshadowings"].values() if f.get("status") in ("open", "planted")
                ),
                "foreshadowings_closed": sum(
                    1 for f in self.state["foreshadowings"].values() if f.get("status") == "closed"
                ),
                "foreshadowings_overdue": sum(
                    1 for f in self.state["foreshadowings"].values() if f.get("status") == "overdue"
                ),
            },
        }

    def _chapter_to_volume(self, chapter_number: int) -> Optional[int]:
        for v in (self.blueprint.get("volumes") or []):
            cr = v.get("chapter_range") or [0, 0]
            if cr[0] <= chapter_number <= cr[1]:
                return v.get("index")
        return None

    # ------------------------------------------------------------------
    # BaseAgent 接口（占位，本类不调用 LLM）
    # ------------------------------------------------------------------
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """允许通过统一入口调用：根据 action 分发。

        action ∈ {"update", "snapshot", "health", "rebuild"}
        """
        action = input_data.get("action") or "snapshot"
        if action == "update":
            self.update_with_chapter(input_data["chapter_card"], input_data.get("chapter_body", ""))
            self.save_state()
            return {"ok": True, "last_updated_chapter": self.state["last_updated_chapter"]}
        if action == "snapshot":
            tgt = int(input_data.get("target_chapter") or (self.state["last_updated_chapter"] + 1))
            snap = self.snapshot_for_chapter(tgt)
            return {"snapshot": snap, "prompt_block": self.format_snapshot_for_prompt(snap)}
        if action == "health":
            return self.health_check()
        if action == "rebuild":
            self.rebuild_from_scratch(input_data["chapter_pairs"])
            self.save_state()
            return {"ok": True, "indexed": self.state["stats"]["total_chapters_indexed"]}
        return {"error": f"未知 action: {action}"}
