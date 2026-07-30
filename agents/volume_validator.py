"""
VolumeValidator —— 整卷质量校验器（独立组件，零侵入现有系统）

定位
----
OutlinePlanner 输出 ChapterCards，ChapterCardWriter 写章节正文，
VolumeValidator 在整卷写完后做一次"全卷体检"，把单章看不到的整体性问题挖出来。

设计原则
--------
1. 纯启发式 + 确定性，**不调 LLM**：快、省、可复现
2. 5 项独立检查，每项 0-100 分，综合得分 = 加权平均
3. 输出含 issues 与 recommendations，可直接喂回 OutlinePlanner 重规划
4. 输入只要：blueprint + volume_payload + chapter_texts，不依赖任何工作流上下文

输入 (process)
--------------
{
  "blueprint": {...},          # 必填
  "volume_index": int,         # 必填
  "volume_payload": {...},     # 必填，OutlinePlanner.generate_volume_chapter_cards 的产物
  "chapter_texts": {           # 必填，{chapter_number: full_body_text}
      11: "第11章 ...\n\n正文...",
      12: "...",
      ...
  }
}

输出
----
{
  "novel_id": str|None,
  "volume_index": int,
  "volume_title": str,
  "summary": {
    "overall_score": float,      # 0-100
    "passed": bool,              # 综合判定（>= 70 算 pass）
    "chapter_count": int,
    "total_words": int,
  },
  "checks": {
    "protagonist_consistency":   {...},
    "foreshadow_coverage":       {...},
    "pacing_density":            {...},
    "ending_hook_uniqueness":    {...},
    "must_appear_coverage":      {...},
    "cross_volume_consistency":  {...}   # 仅在 input_data 传入 dynamic_state 时出现
  },
  "recommendations": [str, ...]
}
"""

from typing import Dict, List, Any, Tuple
import math
import re

from base_agent import BaseAgent
from core.outline_planner import OutlinePlanner
from utils.must_appear_check import check_volume_must_appear


class VolumeValidator(BaseAgent):
    """整卷质量校验器（纯启发式，不调用 LLM）"""

    PASS_THRESHOLD = 70.0

    # 6 项检查的权重（全部确定性检查，零硬编码黑名单）
    # cross_volume_consistency 来自 DynamicKnowledgeManager.health_check()，
    # 仅在调用方传入 dynamic_state 时才会跑；未传则按剩余 5 项重新归一化加权。
    CHECK_WEIGHTS = {
        "protagonist_consistency":   0.20,
        "foreshadow_coverage":       0.20,
        "pacing_density":            0.15,
        "ending_hook_uniqueness":    0.15,
        "must_appear_coverage":      0.15,
        "cross_volume_consistency":  0.15,
    }

    def __init__(self):
        super().__init__("整卷质量校验器")

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        validation = self.validate_input(input_data, ["blueprint", "volume_index", "volume_payload", "chapter_texts"])
        if not validation["is_valid"]:
            return {"error": validation["error"]}

        blueprint = input_data["blueprint"]
        volume_index = int(input_data["volume_index"])
        volume_payload = input_data["volume_payload"]
        chapter_texts: Dict[int, str] = {int(k): v for k, v in (input_data["chapter_texts"] or {}).items()}

        meta = blueprint.get("meta", {}) or {}
        protagonist_name = meta.get("protagonist_name", "")

        cards = volume_payload.get("chapter_cards", []) or []
        chapter_range = volume_payload.get("chapter_range") or [0, 0]
        start_ch, end_ch = int(chapter_range[0]), int(chapter_range[1])

        body_pairs = self._collect_body_pairs(chapter_texts, start_ch, end_ch)
        total_words = sum(len(b) for _, b in body_pairs)

        self.log(f"开始校验卷 {volume_index}：{len(cards)} 张卡 / {len(body_pairs)} 篇正文 / 共 {total_words} 字")

        checks = {
            "protagonist_consistency": self._check_protagonist(body_pairs, protagonist_name),
            "foreshadow_coverage":     self._check_foreshadow(blueprint, volume_index, cards, body_pairs),
            "pacing_density":          self._check_pacing(cards, start_ch, end_ch),
            "ending_hook_uniqueness":  self._check_ending_hooks(cards),
            "must_appear_coverage":    self._check_must_appear(cards, body_pairs),
        }

        # 可选第 6 维：跨卷一致性（来自 DynamicKnowledgeManager）
        # 调用方可传 "dynamic_state"（DKM 实例）或 "dynamic_state_health"（已计算好的 health 报告）
        cross = self._check_cross_volume(input_data, volume_index)
        if cross is not None:
            checks["cross_volume_consistency"] = cross

        # 加权平均时只算"实际跑了的 check"，缺失的权重按比例重归一
        active_weight = sum(self.CHECK_WEIGHTS[k] for k in checks if k in self.CHECK_WEIGHTS)
        if active_weight <= 0:
            overall_score = 0.0
        else:
            overall_score = sum(
                checks[k]["score"] * self.CHECK_WEIGHTS[k] for k in checks if k in self.CHECK_WEIGHTS
            ) / active_weight
        recommendations = self._build_recommendations(checks)

        result = {
            "novel_id": meta.get("novel_id"),
            "volume_index": volume_index,
            "volume_title": volume_payload.get("volume_title") or "",
            "summary": {
                "overall_score": round(overall_score, 2),
                "passed": overall_score >= self.PASS_THRESHOLD,
                "chapter_count": len(cards),
                "body_count": len(body_pairs),
                "total_words": total_words,
            },
            "checks": checks,
            "recommendations": recommendations,
        }
        tag = "PASS" if result["summary"]["passed"] else "WARN"
        self.log(f"卷 {volume_index} 校验完成：{tag} score={result['summary']['overall_score']}")
        return result

    # ------------------------------------------------------------------
    # check 1：主角一致性
    # ------------------------------------------------------------------
    def _check_protagonist(
        self, body_pairs: List[Tuple[int, str]], protagonist_name: str
    ) -> Dict[str, Any]:
        if not protagonist_name:
            return {"score": 0.0, "passed": False, "issues": ["蓝图未给出 protagonist_name"], "details": []}

        details = []
        absent = []
        light_chapters = []
        for ch_num, body in body_pairs:
            cnt = body.count(protagonist_name)
            ok = cnt >= 2
            details.append({"chapter": ch_num, "count": cnt, "ok": ok})
            if cnt == 0:
                absent.append(ch_num)
            elif cnt < 2:
                light_chapters.append(ch_num)

        if not body_pairs:
            return {"score": 0.0, "passed": False, "issues": ["卷内没有任何正文"], "details": []}

        ok_ratio = sum(1 for d in details if d["ok"]) / len(details)
        score = ok_ratio * 100

        issues = []
        if absent:
            issues.append(f"主角'{protagonist_name}'在以下章完全未出现：{absent}")
        if light_chapters:
            issues.append(f"主角'{protagonist_name}'在以下章仅出现 1 次（疑似旁观）：{light_chapters}")

        return {
            "score": round(score, 2),
            "passed": score >= 80,
            "details": details,
            "issues": issues,
        }

    # ------------------------------------------------------------------
    # check 2：伏笔回收
    # ------------------------------------------------------------------
    def _check_foreshadow(
        self,
        blueprint: Dict[str, Any],
        volume_index: int,
        cards: List[Dict[str, Any]],
        body_pairs: List[Tuple[int, str]],
    ) -> Dict[str, Any]:
        ledger = blueprint.get("global_foreshadow_ledger", []) or []
        expected = [
            {"id": item.get("id"), "content": item.get("content", ""),
             "importance": item.get("importance", "mid"),
             "plant_volume": item.get("plant_volume"),
             "payoff_volume": item.get("payoff_volume")}
            for item in ledger
            if int(item.get("payoff_volume", -1)) == volume_index
        ]

        # 卡上声明的 payoff
        declared_payoffs: List[Tuple[int, str]] = []
        for c in cards:
            for entry in (c.get("foreshadow_payoff") or []):
                if isinstance(entry, str) and entry.strip():
                    declared_payoffs.append((int(c.get("chapter_number", 0)), entry.strip()))

        # 卡上声明的 plant
        declared_plants = sum(len(c.get("foreshadow_plant") or []) for c in cards)

        matched: List[Dict[str, Any]] = []
        missing: List[Dict[str, Any]] = []
        for fs in expected:
            fid = (fs["id"] or "").strip()
            content = fs["content"] or ""
            keywords = self._foreshadow_keywords(content)

            hit_chapters: List[int] = []
            # 1) 通过 id 引用匹配
            for ch_num, decl in declared_payoffs:
                if fid and fid in decl:
                    hit_chapters.append(ch_num)
            # 2) 通过 content 关键词匹配卡片声明
            for ch_num, decl in declared_payoffs:
                if any(kw and kw in decl for kw in keywords):
                    hit_chapters.append(ch_num)
            # 3) 通过正文关键词匹配（弱信号）
            text_hits = []
            for ch_num, body in body_pairs:
                if any(kw and kw in body for kw in keywords):
                    text_hits.append(ch_num)

            hit_chapters = sorted(set(hit_chapters))
            text_hits = sorted(set(text_hits))

            if hit_chapters or text_hits:
                matched.append({
                    "id": fid, "content": content, "importance": fs["importance"],
                    "card_hits": hit_chapters, "text_hits": text_hits,
                })
            else:
                missing.append({"id": fid, "content": content, "importance": fs["importance"]})

        # 计分：必须回收的伏笔回收率为主，加上"卡片有声明 plant/payoff"的鼓励项
        if not expected:
            base = 100.0  # 无 payoff 任务直接满分
            issues = []
        else:
            ratio = len(matched) / len(expected)
            base = ratio * 100
            issues = []
            high_missing = [m for m in missing if m["importance"] == "high"]
            if high_missing:
                issues.append(f"high 优先级伏笔未回收：{[(m['id'], m['content'][:20]) for m in high_missing]}")
            mid_missing = [m for m in missing if m["importance"] == "mid"]
            if mid_missing:
                issues.append(f"mid 优先级伏笔未回收：{[(m['id'], m['content'][:20]) for m in mid_missing]}")

        if declared_plants == 0 and len(cards) >= 5:
            issues.append("整卷未声明任何新伏笔（foreshadow_plant 全空）")
            base = max(0.0, base - 15)

        return {
            "score": round(base, 2),
            "passed": base >= 70,
            "expected_payoffs": expected,
            "matched_payoffs": matched,
            "missing_payoffs": missing,
            "declared_plants": declared_plants,
            "declared_payoffs": len(declared_payoffs),
            "issues": issues,
        }

    @staticmethod
    def _foreshadow_keywords(content: str) -> List[str]:
        """从伏笔 content 抽几个关键词用于匹配。简单切：去掉标点，按 2-4 字滑窗。"""
        text = re.sub(r"[，。、；：！？\s\(\)（）\"'—…\.,\!\?]", "", content or "")
        if not text:
            return []
        # 取整段 + 头 4 字 + 末 4 字 + 中间 2-4 字 token
        tokens = {text}
        if len(text) >= 4:
            tokens.add(text[:4])
            tokens.add(text[-4:])
        if len(text) >= 6:
            tokens.add(text[2:6])
        # 去掉太短或纯虚词
        return [t for t in tokens if len(t) >= 2]

    # ------------------------------------------------------------------
    # check 3：节奏密度
    # ------------------------------------------------------------------
    def _check_pacing(
        self, cards: List[Dict[str, Any]], start_ch: int, end_ch: int
    ) -> Dict[str, Any]:
        if not cards:
            return {"score": 0.0, "passed": False, "issues": ["卷内无 chapter cards"]}

        role_seq = [c.get("role", "") for c in cards]
        prior: List[str] = []
        violations = []
        for c in cards:
            ch_num = int(c.get("chapter_number", 0))
            role = c.get("role", "")
            if role and OutlinePlanner._is_chapter_role_off(role, ch_num, start_ch, end_ch, prior):
                violations.append({"chapter": ch_num, "role": role, "issue": "role 与位置/前序不符"})
            prior.append(role)

        # 整卷至少 1 个 climax 或 twist
        has_climax_or_twist = any(r in {"climax", "twist"} for r in role_seq)

        # tension 分布
        tensions = [int(c.get("tension_level", 5)) for c in cards]
        avg = sum(tensions) / len(tensions)
        std = math.sqrt(sum((t - avg) ** 2 for t in tensions) / len(tensions))
        tens_min, tens_max = min(tensions), max(tensions)
        flat = std < 1.0  # 起伏过小

        # 计分
        score = 100.0
        issues = []
        if violations:
            score -= 10 * len(violations)
            issues.append(f"role 序列违例 {len(violations)} 处：{[(v['chapter'], v['role']) for v in violations]}")
        if not has_climax_or_twist:
            score -= 30
            issues.append("整卷既无 climax 也无 twist，节奏必然平庸")
        if flat:
            score -= 20
            issues.append(f"tension_level 起伏过小（std={std:.2f}），全卷节奏太平")
        if tens_max - tens_min < 3:
            score -= 10
            issues.append(f"tension_level 极差仅 {tens_max - tens_min}，缺乏对比")

        score = max(0.0, score)

        return {
            "score": round(score, 2),
            "passed": score >= 70,
            "role_sequence": role_seq,
            "role_violations": violations,
            "has_climax_or_twist": has_climax_or_twist,
            "tension": {
                "min": tens_min, "max": tens_max, "avg": round(avg, 2), "std": round(std, 2),
                "flat": flat, "values": tensions,
            },
            "issues": issues,
        }

    # ------------------------------------------------------------------
    # check 4：ending_hook 唯一性
    # ------------------------------------------------------------------
    def _check_ending_hooks(self, cards: List[Dict[str, Any]]) -> Dict[str, Any]:
        hooks = []
        for c in cards:
            h = (c.get("ending_hook") or "").strip()
            if h:
                hooks.append((int(c.get("chapter_number", 0)), h))

        if not hooks:
            return {"score": 0.0, "passed": False, "issues": ["全卷无任何 ending_hook"]}

        # 完全相同的
        bucket: Dict[str, List[int]] = {}
        for ch_num, h in hooks:
            bucket.setdefault(h, []).append(ch_num)
        exact_dupes = [{"hook": h, "chapters": chs} for h, chs in bucket.items() if len(chs) > 1]

        # 显著相似（前 8 字相同）
        similar: List[Dict[str, Any]] = []
        seen_prefix: Dict[str, List[int]] = {}
        for ch_num, h in hooks:
            key = h[:8]
            seen_prefix.setdefault(key, []).append(ch_num)
        for key, chs in seen_prefix.items():
            if len(chs) > 1:
                similar.append({"prefix": key, "chapters": chs})

        unique_ratio = len(set(h for _, h in hooks)) / len(hooks)
        score = unique_ratio * 100
        if exact_dupes:
            score -= 30 * len(exact_dupes)
        if similar:
            # 前 8 字撞车，每对 -10
            score -= 10 * sum(1 for s in similar if s["chapters"] != bucket.get(s["prefix"], []))
        score = max(0.0, score)

        issues = []
        if exact_dupes:
            issues.append(f"完全重复的 ending_hook：{exact_dupes}")
        if similar:
            issues.append(f"前 8 字相同的疑似复读：{similar}")

        return {
            "score": round(score, 2),
            "passed": not exact_dupes and not similar,
            "total": len(hooks),
            "unique": len(set(h for _, h in hooks)),
            "exact_dupes": exact_dupes,
            "similar_prefixes": similar,
            "issues": issues,
        }

    # ------------------------------------------------------------------
    # check 5：must_appear 覆盖率（替代旧的"白名单越界启发式"）
    #
    # OutlinePlanner 在 chapter_card.must_appear 里已经声明了
    # 本章必须出场的 characters/locations/objects；这里做一次确定性
    # 反查：声明的内容是否真的写进了正文。
    #
    # 这是零硬编码、跨题材通用、零误报的检查；真正抓的是
    # "LLM 写偏了——卡片说要出场结果忘了写"这类质量问题。
    # ------------------------------------------------------------------
    def _check_must_appear(
        self, cards: List[Dict[str, Any]], body_pairs: List[Tuple[int, str]]
    ) -> Dict[str, Any]:
        if not body_pairs:
            return {"score": 0.0, "passed": False, "issues": ["无正文可扫"]}
        result = check_volume_must_appear(cards, body_pairs)
        return result

    # ------------------------------------------------------------------
    # 公共
    # ------------------------------------------------------------------
    @staticmethod
    def _collect_body_pairs(
        chapter_texts: Dict[int, str], start_ch: int, end_ch: int
    ) -> List[Tuple[int, str]]:
        """解析 chapter_texts，从 'titie\\n\\nbody' 中切出 body；按章号排序"""
        out: List[Tuple[int, str]] = []
        for ch_num in range(start_ch, end_ch + 1):
            raw = chapter_texts.get(ch_num)
            if not raw:
                continue
            parts = raw.split("\n", 1)
            body = parts[1].lstrip("\n").rstrip() if len(parts) > 1 else raw
            out.append((ch_num, body))
        return out

    # ------------------------------------------------------------------
    # check 6（可选）：跨卷一致性 —— 复用 DynamicKnowledgeManager.health_check()
    # ------------------------------------------------------------------
    def _check_cross_volume(
        self, input_data: Dict[str, Any], volume_index: int
    ) -> Dict[str, Any]:
        """从 input_data 中拉取 DKM 状态做跨卷体检。未传则返回 None 跳过。"""
        health = input_data.get("dynamic_state_health")
        if not health:
            dkm = input_data.get("dynamic_state")
            if dkm is None:
                return None  # 调用方没传，跳过该检查
            try:
                health = dkm.health_check()
            except Exception as e:
                return {
                    "score": 0.0, "passed": False,
                    "issues": [f"health_check 调用失败: {e}"],
                    "summary": {}, "raw": None,
                }

        # 评分：高级问题强罚，中级中罚，低级轻罚
        s = health.get("summary", {})
        score = 100.0
        score -= 20.0 * s.get("high", 0)
        score -= 8.0 * s.get("medium", 0)
        score -= 2.0 * s.get("low", 0)
        score = max(0.0, min(100.0, score))

        issues_text: List[str] = []
        for i in (health.get("issues") or [])[:10]:
            issues_text.append(f"[{i.get('severity','?').upper()}] {i.get('message','')}")

        return {
            "score": round(score, 2),
            "passed": score >= 70,
            "issues": issues_text,
            "summary": s,
            "raw_health": health,
        }

    @staticmethod
    def _build_recommendations(checks: Dict[str, Any]) -> List[str]:
        recs: List[str] = []
        prot = checks["protagonist_consistency"]
        if not prot["passed"]:
            recs.append("【主角一致性】检查未通过：在 OutlinePlanner 中强化主角必出场约束，或针对低分章重写。")
        fs = checks["foreshadow_coverage"]
        if fs["missing_payoffs"]:
            high = [m for m in fs["missing_payoffs"] if m["importance"] == "high"]
            if high:
                recs.append(f"【伏笔回收】high 伏笔 {[m['id'] for m in high]} 未回收：建议在卷末追加专门回收章。")
            else:
                recs.append("【伏笔回收】存在未回收伏笔：可在下一卷开场作为冷启动钩子。")
        pace = checks["pacing_density"]
        if not pace["passed"]:
            if not pace.get("has_climax_or_twist"):
                recs.append("【节奏】整卷无 climax/twist：在卷末倒数 1-2 章插入对抗高潮。")
            if pace["tension"]["flat"]:
                recs.append("【节奏】tension_level 起伏过小：在中段安排 1 章 buffer 拉低值，让 climax 形成对比。")
        eh = checks["ending_hook_uniqueness"]
        if eh.get("exact_dupes"):
            recs.append("【钩子】发现完全重复的 ending_hook：在 OutlinePlanner 入参的 banned_endings 中加入这些句子并重排。")
        ma = checks["must_appear_coverage"]
        if ma.get("issues"):
            n = len(ma["issues"])
            recs.append(
                f"【出场一致性】发现 {n} 处 must_appear 与正文不一致：建议针对这些章重写或下次 prompt 强化人物/地点/物件出场约束。"
            )
            for issue in ma["issues"][:5]:
                recs.append(f"  · {issue}")

        cv = checks.get("cross_volume_consistency")
        if cv and not cv.get("passed"):
            s = cv.get("summary", {})
            n_over = s.get("foreshadowings_overdue", 0)
            if n_over:
                recs.append(
                    f"【跨卷】检测到 {n_over} 个伏笔已逾期未回收：在下一卷规划时优先把它们写进 foreshadow_payoff_hints。"
                )
            recs.append("【跨卷】DynamicKnowledgeManager 报告了若干跨卷一致性问题（角色/道具/伏笔），详见 cross_volume_consistency.issues。")
            for issue in (cv.get("issues") or [])[:5]:
                recs.append(f"  · {issue}")

        if not recs:
            recs.append("整卷质量良好，无显著问题。可推进到下一卷。")
        return recs
