"""
server.py —— InkAI 新流水线的 Web 后端 + 前端静态托管

本服务把新一代 InkAI 流水线（run_init_novel / run_outline_demo /
run_chapter_demo / run_validate_canon / run_full_novel_audit / 等）的能力
统一暴露为 REST API，并直接服务 frontend/ 下的静态前端。

设计：
  - Flask + flask-cors，零额外依赖（requirements.txt 已自带）
  - 长任务（章节生成 / 蓝图生成 / storyline 展开）用 threading 后台跑，
    前端轮询 /api/tasks/{task_id} 拿进度
  - API 风格：{"ok": bool, "data": ..., "error": ...}
  - 不写入任何旧流水线的孤儿文件；新文件全走新管道

启动：
  python server.py
  # 浏览器打开 http://127.0.0.1:5000

详细 API 见 frontend/app.js 与本文件的路由定义。
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

# Windows 终端 utf-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

import config
from core.canon_checker import load_and_check as canon_check
from core.full_novel_auditor import audit_full_novel
from core.genre_pack import GenrePack
from core.outline_planner import OutlinePlanner

# ----------------------------------------------------------------------
# Flask 与全局
# ----------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

app = Flask(__name__, static_folder=None)
CORS(app)

# 后台任务表：task_id -> dict
_tasks: Dict[str, Dict[str, Any]] = {}
_tasks_lock = threading.Lock()


def _ok(data: Any = None, **extra) -> Any:
    payload = {"ok": True, "data": data}
    payload.update(extra)
    return jsonify(payload)


def _err(msg: str, status: int = 400, **extra) -> Any:
    payload = {"ok": False, "error": msg}
    payload.update(extra)
    resp = jsonify(payload)
    resp.status_code = status
    return resp


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _novel_dir(novel_id: str) -> str:
    return os.path.join(config.NOVELS_DIR, novel_id)


def _ensure_novel(novel_id: str) -> str:
    nd = _novel_dir(novel_id)
    if not os.path.isdir(nd):
        abort(404, description=f"novel_id 不存在：{novel_id}")
    return nd


# ----------------------------------------------------------------------
# 后台任务调度
# ----------------------------------------------------------------------
def _new_task(task_type: str, novel_id: Optional[str] = None,
              total: int = 1) -> Dict[str, Any]:
    tid = uuid.uuid4().hex[:12]
    t = {
        "task_id": tid,
        "type": task_type,
        "novel_id": novel_id,
        "status": "pending",
        "started_at": time.time(),
        "ended_at": None,
        "progress": {"current": 0, "total": total, "msg": "排队中…"},
        "logs": [],
        "result": None,
        "error": None,
    }
    with _tasks_lock:
        _tasks[tid] = t
    return t


def _task_log(task: Dict[str, Any], msg: str) -> None:
    with _tasks_lock:
        task["logs"].append({"t": time.time(), "msg": msg})
        if len(task["logs"]) > 1000:
            task["logs"] = task["logs"][-1000:]


def _task_progress(task: Dict[str, Any], current: int,
                   total: Optional[int] = None,
                   msg: Optional[str] = None) -> None:
    with _tasks_lock:
        task["progress"]["current"] = current
        if total is not None:
            task["progress"]["total"] = total
        if msg is not None:
            task["progress"]["msg"] = msg


def _task_done(task: Dict[str, Any], result: Any = None,
               error: Optional[str] = None) -> None:
    with _tasks_lock:
        task["status"] = "failed" if error else "succeeded"
        task["ended_at"] = time.time()
        task["result"] = result
        task["error"] = error


def _run_in_thread(target_fn, task: Dict[str, Any]):
    def _worker():
        with _tasks_lock:
            task["status"] = "running"
        try:
            target_fn(task)
        except Exception as exc:
            import traceback
            tb = traceback.format_exc(limit=4)
            _task_log(task, f"[FATAL] {exc}\n{tb}")
            _task_done(task, error=str(exc))
    th = threading.Thread(target=_worker, daemon=True)
    th.start()


# ======================================================================
# 系统级 API
# ======================================================================

@app.route("/api/health")
def api_health():
    return _ok({
        "service": "InkAI Server",
        "novels_dir": config.NOVELS_DIR,
        "model": config.MODEL_NAME,
    })


@app.route("/api/config", methods=["GET"])
def api_config_get():
    """返回当前配置状态（不泄露完整 key）。开源版只读，配置通过环境变量。"""
    key = config.API_KEY
    emb_key = config.EMBEDDING_API_KEY
    return _ok({
        "has_api_key": bool(key),
        "api_key_preview": (key[:8] + "..." + key[-4:]) if len(key) > 12 else ("***" if key else ""),
        "base_url": config.BASE_URL,
        "model": config.MODEL_NAME,
        "provider": config.PROVIDER,
        "available_providers": list(config.PROVIDER_PRESETS.keys()),
        "has_embedding_key": bool(emb_key) and emb_key != key,
        "embedding_base_url": config.EMBEDDING_BASE_URL,
        "embedding_status": config.EMBEDDING_STATUS,
    })


@app.route("/api/genres", methods=["GET"])
def api_list_genres():
    """题材包列表（GenrePack）"""
    out: List[Dict[str, Any]] = []
    for name in GenrePack.list_registry():
        try:
            p = GenrePack.from_registry(name)
            out.append({
                "name": p.name,
                "display_name": p.display_name,
                "one_liner": p.one_liner,
                "default_tags": dict(p.default_tags or {}),
            })
        except Exception as exc:
            out.append({"name": name, "display_name": name,
                        "one_liner": f"[加载失败] {exc}", "default_tags": {}})
    return _ok(out)


@app.route("/api/genres/<name>", methods=["GET"])
def api_get_genre(name):
    """获取单个题材包的完整 JSON 结构。"""
    p = GenrePack.from_registry(name)
    if p is None:
        return _err(f"题材 '{name}' 不存在", 404)
    return _ok(p.to_dict())


def _genre_path(name: str) -> str:
    return os.path.join(config.GENRES_DIR, f"{name}.json")


def _validate_genre_name(name: str) -> Optional[str]:
    """校验题材 name 字段：纯小写字母/数字/下划线，长度 2-32。返回 None 表示合法，否则返回错误。"""
    import re
    if not name:
        return "name 不能为空"
    if not re.match(r"^[a-z0-9_]{2,32}$", name):
        return "name 只能包含小写字母 / 数字 / 下划线，长度 2-32"
    return None


@app.route("/api/genres", methods=["POST"])
def api_create_genre():
    """新建题材包。payload 是完整的 GenrePack JSON。"""
    payload = request.get_json(force=True, silent=True) or {}
    name = (payload.get("name") or "").strip().lower()
    err = _validate_genre_name(name)
    if err:
        return _err(err, 400)
    path = _genre_path(name)
    if os.path.exists(path):
        return _err(f"题材 '{name}' 已存在，请改名或用 PUT 更新", 409)
    # 用 GenrePack.from_dict 校验结构
    try:
        gp = GenrePack.from_dict(payload)
    except Exception as exc:
        return _err(f"题材结构非法：{exc}", 400)
    os.makedirs(config.GENRES_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gp.to_dict(), f, ensure_ascii=False, indent=2)
    return _ok(gp.to_dict())


@app.route("/api/genres/<name>", methods=["PUT"])
def api_update_genre(name):
    path = _genre_path(name)
    if not os.path.exists(path):
        return _err(f"题材 '{name}' 不存在", 404)
    payload = request.get_json(force=True, silent=True) or {}
    payload["name"] = name  # name 不能改
    try:
        gp = GenrePack.from_dict(payload)
    except Exception as exc:
        return _err(f"题材结构非法：{exc}", 400)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gp.to_dict(), f, ensure_ascii=False, indent=2)
    return _ok(gp.to_dict())


@app.route("/api/genres/<name>", methods=["DELETE"])
def api_delete_genre(name):
    path = _genre_path(name)
    if not os.path.exists(path):
        return _err(f"题材 '{name}' 不存在", 404)
    # 检查是否有小说在用这个题材
    in_use = []
    if os.path.isdir(config.NOVELS_DIR):
        for entry in os.listdir(config.NOVELS_DIR):
            md = _read_json(os.path.join(config.NOVELS_DIR, entry, "metadata.json")) or {}
            if md.get("_genre") == name:
                in_use.append({"novel_id": entry, "title": md.get("title", "")})
    if in_use:
        return _err(
            f"题材 '{name}' 正被 {len(in_use)} 本小说使用，无法删除",
            409, in_use=in_use,
        )
    os.remove(path)
    return _ok({"name": name, "deleted": True})


@app.route("/api/genres/generate", methods=["POST"])
def api_generate_genre():
    """LLM 根据自由描述生成完整 GenrePack JSON（不落盘）。
    payload: { description: "...", name: "可选建议名" }
    返回的 JSON 用户可以预览修改后再调 POST /api/genres 落盘。
    """
    payload = request.get_json(force=True, silent=True) or {}
    description = (payload.get("description") or "").strip()
    suggested = (payload.get("name") or "").strip()
    if not description:
        return _err("description 必填", 400)
    task = _new_task("generate_genre", novel_id=None, total=2)

    def _job(t):
        from agents.genre_pack_generator import GenrePackGenerator
        _task_progress(t, 0, msg="LLM 生成题材结构…")
        agent = GenrePackGenerator()
        result = agent.process({"description": description, "name": suggested})
        if result.get("error"):
            raise RuntimeError(result["error"])
        # 自动避免与已有同名冲突
        existing = set(GenrePack.list_registry())
        base = result.get("name") or "custom_genre"
        new_name = base
        i = 2
        while new_name in existing:
            new_name = f"{base}_{i}"
            i += 1
        result["name"] = new_name
        _task_progress(t, 1, msg="校验完成")
        _task_done(t, result={"genre": result})

    _run_in_thread(_job, task)
    return _ok({"task_id": task["task_id"]})


# ======================================================================
# 小说集合
# ======================================================================

def _summarize_novel(novel_id: str, ndir: str) -> Dict[str, Any]:
    metadata = _read_json(os.path.join(ndir, "metadata.json")) or {}
    characters = _read_json(os.path.join(ndir, "characters.json")) or {}
    storyline = _read_json(os.path.join(ndir, "storyline.json")) or {}
    blueprint = _read_json(os.path.join(ndir, "outline", "blueprint.json")) or {}

    # 章节统计
    cd = os.path.join(ndir, "chapters_demo")
    ch_done = 0
    if os.path.isdir(cd):
        for fn in os.listdir(cd):
            if fn.startswith("chapter_") and fn.endswith(".txt"):
                ch_done += 1

    # 子流程标记
    has_storyline_full = bool(
        (storyline.get("overall_storyline") or {}).get("main_goal")
    )
    canon_report = _read_json(os.path.join(ndir, "canon_report.json")) or {}
    audit_report = _read_json(os.path.join(ndir, "audit_report.json")) or {}

    return {
        "novel_id": novel_id,
        "title": metadata.get("title") or "",
        "main_character_name": metadata.get("main_character_name") or "",
        "supporting_character_names": metadata.get("supporting_character_names") or [],
        "total_chapters_planned": metadata.get("total_chapters_planned") or 0,
        "genre": metadata.get("_genre") or characters.get("_genre") or "",
        "genre_display": metadata.get("_genre_display") or "",
        "created_at": metadata.get("created_at") or "",
        "updated_at": metadata.get("updated_at") or "",
        "status": metadata.get("status") or "",
        "stage": {
            "init": True,
            "storyline_expanded": has_storyline_full,
            "canon_report": bool(canon_report),
            "blueprint": bool(blueprint),
            "chapters_done": ch_done,
        },
        "canon_summary": canon_report.get("summary") or {},
        "audit_overall_score": audit_report.get("overall_score"),
    }


@app.route("/api/novels", methods=["GET"])
def api_novels_list():
    if not os.path.isdir(config.NOVELS_DIR):
        return _ok([])
    out: List[Dict[str, Any]] = []
    for entry in sorted(os.listdir(config.NOVELS_DIR)):
        ndir = os.path.join(config.NOVELS_DIR, entry)
        if not os.path.isdir(ndir):
            continue
        try:
            out.append(_summarize_novel(entry, ndir))
        except Exception as exc:
            out.append({"novel_id": entry, "title": "", "error": str(exc)})
    # 按更新时间倒序
    out.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return _ok(out)


@app.route("/api/novels", methods=["POST"])
def api_novels_create():
    """
    创建一本新小说（init）。
    payload: {
      title: "...", protagonist: "...", genre: "xianxia",
      total_chapters: 30, extra: "...",
      also_storyline: true | false  (默认 true，会用 LLM 展开 storyline 骨架)
    }
    """
    payload = request.get_json(force=True, silent=True) or {}
    title = (payload.get("title") or "").strip()
    protagonist = (payload.get("protagonist") or "").strip()
    genre = (payload.get("genre") or "").strip()
    total_chapters = int(payload.get("total_chapters") or 30)
    extra = (payload.get("extra") or "").strip()
    also_storyline = bool(payload.get("also_storyline", True))

    if not (title and protagonist and genre):
        return _err("title / protagonist / genre 必填", 400)

    pack = GenrePack.from_registry(genre)
    if pack is None:
        return _err(f"题材包 '{genre}' 不存在", 400)

    novel_id = str(uuid.uuid4())
    task = _new_task("create_novel", novel_id=novel_id, total=4 if also_storyline else 3)

    def _job(t):
        from datetime import datetime
        from run_init_novel import build_three_files, write_three_files, _wrap_title

        novel_dir = _novel_dir(novel_id)
        if os.path.exists(novel_dir):
            raise RuntimeError(f"novel_dir 已存在：{novel_dir}")
        _task_progress(t, 0, msg="渲染题材骨架…")
        spec = pack.render_spec(
            title=_wrap_title(title),
            protagonist_name=protagonist,
            total_chapters=total_chapters,
            extra_user_requirements=extra,
        )
        _task_progress(t, 1, msg="写入 metadata / characters / storyline 骨架…")
        payloads = build_three_files(spec, pack, novel_id)
        write_three_files(novel_dir, payloads)
        _task_log(t, f"[OK] 三件套落盘：{novel_dir}")

        if also_storyline:
            from agents.storyline_generator import StorylineGeneratorAgent
            _task_progress(t, 2, msg="调用 LLM 展开 storyline 骨架…")
            characters = payloads["characters"]
            main_name = (characters.get("main_character") or {}).get("basic_info", {}).get("name", "")
            sup_names = [
                (s.get("basic_info") or {}).get("name", "")
                for s in (characters.get("supporting_characters") or [])
            ]
            sup_names = [n for n in sup_names if n]
            roster = ", ".join([main_name] + sup_names)
            constraint_block = (
                "\n\n【硬性约束 — 角色档案不可改写】\n"
                f"本作所有出场角色已在 characters.json 中注册，唯一合法的角色名清单为：{roster}。\n"
                "请在生成 storyline、first_module、subplot_hints 时严格遵循以下规则：\n"
                f"1. 主角必须使用『{main_name}』这个姓名，禁止改名或起别名；\n"
                "2. 涉及配角时必须从清单中选用真实姓名，禁止凭空创造新角色名；\n"
                "3. 若剧情确需新角色，请使用通用职务称谓（如『支队领导』『法医』）；\n"
                "4. 不得给已注册角色赋予与 characters.json 中 role 字段冲突的身份；\n"
                "5. 角色性别必须与 characters.json 中的 gender 字段一致。"
            )
            agent = StorylineGeneratorAgent()
            story_input = {
                "selected_tags": spec.get("tags") or {},
                "characters": characters,
                "user_requirements": (spec.get("user_requirements") or "") + constraint_block,
            }
            story_result = agent.process(story_input)
            new_storyline = {
                "overall_storyline": story_result.get("overall_storyline") or {},
                "first_module": story_result.get("first_module") or {},
                "subplot_hints": story_result.get("subplot_hints") or {},
                "story_structure": story_result.get("story_structure") or {},
            }
            new_storyline["overall_storyline"]["_seeded_by_genre"] = pack.name
            with open(os.path.join(novel_dir, "storyline.json"), "w", encoding="utf-8") as f:
                json.dump(new_storyline, f, ensure_ascii=False, indent=2)
            _task_log(t, "[OK] storyline 已展开并落盘")

        # 校验
        _task_progress(t, t["progress"]["total"] - 1, msg="档案一致性校验…")
        report = canon_check(novel_dir, novel_id=novel_id)
        with open(os.path.join(novel_dir, "canon_report.json"), "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        _task_log(t, f"[OK] canon: ERROR={report.summary.get('ERROR', 0)} "
                     f"WARNING={report.summary.get('WARNING', 0)}")
        _task_progress(t, t["progress"]["total"], msg="完成")
        _task_done(t, result={
            "novel_id": novel_id,
            "summary": _summarize_novel(novel_id, novel_dir),
        })

    _run_in_thread(_job, task)
    return _ok({"task_id": task["task_id"], "novel_id": novel_id})


@app.route("/api/novels/<novel_id>", methods=["DELETE"])
def api_novel_delete(novel_id):
    ndir = _ensure_novel(novel_id)
    import shutil
    shutil.rmtree(ndir)
    return _ok({"novel_id": novel_id, "deleted": True})


# ======================================================================
# 单本小说
# ======================================================================

@app.route("/api/novels/<novel_id>", methods=["GET"])
def api_novel_summary(novel_id):
    ndir = _ensure_novel(novel_id)
    return _ok(_summarize_novel(novel_id, ndir))


@app.route("/api/novels/<novel_id>/metadata", methods=["GET"])
def api_novel_metadata_get(novel_id):
    ndir = _ensure_novel(novel_id)
    return _ok(_read_json(os.path.join(ndir, "metadata.json")) or {})


@app.route("/api/novels/<novel_id>/metadata", methods=["PUT"])
def api_novel_metadata_put(novel_id):
    """更新 metadata 中允许的字段（不能改 novel_id / created_at / _genre）。"""
    ndir = _ensure_novel(novel_id)
    payload = request.get_json(force=True, silent=True) or {}
    path = os.path.join(ndir, "metadata.json")
    md = _read_json(path) or {}
    from datetime import datetime
    EDITABLE = {"title", "user_requirements", "main_character_name",
                "supporting_character_names", "total_chapters_planned", "status"}
    for k in EDITABLE:
        if k in payload:
            md[k] = payload[k]
    md["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(md, f, ensure_ascii=False, indent=2)
    return _ok(md)


@app.route("/api/novels/<novel_id>/characters", methods=["GET"])
def api_novel_characters(novel_id):
    ndir = _ensure_novel(novel_id)
    return _ok(_read_json(os.path.join(ndir, "characters.json")) or {})


@app.route("/api/novels/<novel_id>/characters", methods=["PUT"])
def api_novel_characters_put(novel_id):
    """整体覆写 characters.json（前端在 UI 编辑后整体提交）。"""
    ndir = _ensure_novel(novel_id)
    payload = request.get_json(force=True, silent=True) or {}
    if "main_character" not in payload and "supporting_characters" not in payload:
        return _err("payload 必须包含 main_character 或 supporting_characters", 400)
    path = os.path.join(ndir, "characters.json")
    cur = _read_json(path) or {}
    cur["main_character"] = payload.get("main_character", cur.get("main_character") or {})
    cur["supporting_characters"] = payload.get("supporting_characters",
                                                cur.get("supporting_characters") or [])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
    return _ok(cur)


@app.route("/api/novels/<novel_id>/storyline", methods=["GET"])
def api_novel_storyline(novel_id):
    ndir = _ensure_novel(novel_id)
    return _ok(_read_json(os.path.join(ndir, "storyline.json")) or {})


@app.route("/api/novels/<novel_id>/storyline", methods=["PUT"])
def api_novel_storyline_put(novel_id):
    ndir = _ensure_novel(novel_id)
    payload = request.get_json(force=True, silent=True) or {}
    path = os.path.join(ndir, "storyline.json")
    cur = _read_json(path) or {}
    if "overall_storyline" in payload:
        cur["overall_storyline"] = payload["overall_storyline"]
    if "first_module" in payload:
        cur["first_module"] = payload["first_module"]
    if "subplot_hints" in payload:
        cur["subplot_hints"] = payload["subplot_hints"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
    return _ok(cur)


@app.route("/api/novels/<novel_id>/canon", methods=["GET"])
def api_novel_canon_get(novel_id):
    ndir = _ensure_novel(novel_id)
    return _ok(_read_json(os.path.join(ndir, "canon_report.json")) or {})


@app.route("/api/novels/<novel_id>/canon", methods=["POST"])
def api_novel_canon_run(novel_id):
    ndir = _ensure_novel(novel_id)
    report = canon_check(ndir, novel_id=novel_id)
    with open(os.path.join(ndir, "canon_report.json"), "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    return _ok(report.to_dict())


@app.route("/api/novels/<novel_id>/blueprint", methods=["GET"])
def api_novel_blueprint_get(novel_id):
    ndir = _ensure_novel(novel_id)
    return _ok(_read_json(os.path.join(ndir, "outline", "blueprint.json")) or {})


@app.route("/api/novels/<novel_id>/blueprint", methods=["POST"])
def api_novel_blueprint_create(novel_id):
    """异步生成 blueprint。"""
    ndir = _ensure_novel(novel_id)
    metadata = _read_json(os.path.join(ndir, "metadata.json")) or {}
    pack_name = metadata.get("_genre")
    pack = GenrePack.from_registry(pack_name) if pack_name else None
    task = _new_task("generate_blueprint", novel_id=novel_id, total=2)

    def _job(t):
        # 复用 run_outline_demo 的 spec 装配
        from run_outline_demo import build_spec_from_novel
        _task_progress(t, 0, msg="装配 spec…")
        spec = build_spec_from_novel(novel_id, None, None)
        _task_progress(t, 1, msg="LLM 生成蓝图…")
        planner = OutlinePlanner(genre_pack=pack)
        bp = planner.generate_blueprint(spec)
        if bp.get("error"):
            raise RuntimeError(bp["error"])
        out_dir = os.path.join(ndir, "outline")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "blueprint.json"), "w", encoding="utf-8") as f:
            json.dump(bp, f, ensure_ascii=False, indent=2)
        _task_log(t, "[OK] blueprint.json 已落盘")
        _task_progress(t, 2, msg="完成")
        _task_done(t, result={"blueprint": bp})

    _run_in_thread(_job, task)
    return _ok({"task_id": task["task_id"]})


@app.route("/api/novels/<novel_id>/volumes")
def api_novel_volumes(novel_id):
    ndir = _ensure_novel(novel_id)
    out_dir = os.path.join(ndir, "outline")
    out: List[Dict[str, Any]] = []
    if os.path.isdir(out_dir):
        for fn in sorted(os.listdir(out_dir)):
            if fn.startswith("volume_") and fn.endswith("_chapters.json"):
                payload = _read_json(os.path.join(out_dir, fn)) or {}
                out.append({
                    "file": fn,
                    "volume_index": payload.get("volume_index"),
                    "title": payload.get("title"),
                    "chapter_range": payload.get("chapter_range"),
                    "card_count": len(payload.get("chapter_cards") or []),
                })
    return _ok(out)


@app.route("/api/novels/<novel_id>/volumes/<int:vol>/cards")
def api_novel_volume_cards(novel_id, vol):
    ndir = _ensure_novel(novel_id)
    path = os.path.join(ndir, "outline", f"volume_{vol}_chapters.json")
    return _ok(_read_json(path) or {})


@app.route("/api/novels/<novel_id>/chapters")
def api_novel_chapters(novel_id):
    """章节列表（章号 / 标题 / 字数 / 是否生成 / 校验摘要）"""
    ndir = _ensure_novel(novel_id)
    cd = os.path.join(ndir, "chapters_demo")
    out: List[Dict[str, Any]] = []
    if not os.path.isdir(cd):
        return _ok(out)
    metas: Dict[int, Dict[str, Any]] = {}
    for fn in sorted(os.listdir(cd)):
        if fn.endswith(".meta.json"):
            try:
                n = int(fn[len("chapter_"):-len(".meta.json")])
            except Exception:
                continue
            metas[n] = _read_json(os.path.join(cd, fn)) or {}
    for n in sorted(metas.keys()):
        m = metas[n]
        v = m.get("validation") or {}
        out.append({
            "chapter_number": n,
            "volume": m.get("volume"),
            "title": m.get("title") or "",
            "word_count": m.get("word_count") or 0,
            "protagonist_count": v.get("protagonist_count") or 0,
            "passed": bool(v.get("word_count_ok") and v.get("protagonist_present")),
        })
    return _ok(out)


@app.route("/api/novels/<novel_id>/chapters/<int:n>", methods=["GET"])
def api_novel_chapter_text(novel_id, n):
    ndir = _ensure_novel(novel_id)
    path = os.path.join(ndir, "chapters_demo", f"chapter_{n}.txt")
    if not os.path.isfile(path):
        return _err(f"章节 {n} 未生成", 404)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    meta = _read_json(os.path.join(ndir, "chapters_demo", f"chapter_{n}.meta.json")) or {}
    lines = text.split("\n", 1)
    title = lines[0].strip() if lines else ""
    body = lines[1].lstrip("\n") if len(lines) > 1 else ""
    return _ok({
        "chapter_number": n,
        "title": title,
        "body": body,
        "meta": meta,
    })


@app.route("/api/novels/<novel_id>/chapters/<int:n>", methods=["PUT"])
def api_novel_chapter_save(novel_id, n):
    """整体覆写一章正文（含标题）；同时刷新 .meta.json 的 word_count 等浅层字段。"""
    ndir = _ensure_novel(novel_id)
    payload = request.get_json(force=True, silent=True) or {}
    title = (payload.get("title") or "").strip() or f"第{n}章"
    body = payload.get("body") or ""
    text = f"{title}\n\n{body.strip()}\n"
    txt_path = os.path.join(ndir, "chapters_demo", f"chapter_{n}.txt")
    if not os.path.isfile(txt_path):
        return _err(f"章节 {n} 不存在，无法编辑", 404)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    # 同步 meta 的字数（不重跑 LLM 校验）
    meta_path = os.path.join(ndir, "chapters_demo", f"chapter_{n}.meta.json")
    meta = _read_json(meta_path) or {}
    meta["title"] = title
    # 估算字数：去掉空白后的中文/英文单词长度近似
    body_no_ws = "".join(body.split())
    meta["word_count"] = len(body_no_ws)
    if "validation" in meta and isinstance(meta["validation"], dict):
        meta["validation"]["_manually_edited"] = True
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return _ok({"chapter_number": n, "title": title, "word_count": meta["word_count"]})


@app.route("/api/novels/<novel_id>/chapters/generate", methods=["POST"])
def api_novel_chapters_generate(novel_id):
    """
    批量生成章节。
    payload: { start: 1, end: 30, target_words: 2300, no_dynamic_state: false }
    """
    ndir = _ensure_novel(novel_id)
    payload = request.get_json(force=True, silent=True) or {}
    start = int(payload.get("start") or 1)
    end = int(payload.get("end") or start)
    target_words = int(payload.get("target_words") or 2300)
    no_ds = bool(payload.get("no_dynamic_state", False))
    if end < start:
        return _err("end < start", 400)
    task = _new_task("generate_chapters", novel_id=novel_id, total=end - start + 1)

    def _job(t):
        from run_chapter_demo import process_one_chapter, load_json
        from agents.chapter_card_writer import ChapterCardWriter
        from core.dynamic_knowledge_manager import DynamicKnowledgeManager

        _task_log(t, f"[INFO] 启动批量生成 ch{start}..{end}（target={target_words}）")
        bp_path = os.path.join(ndir, "outline", "blueprint.json")
        blueprint = load_json(bp_path) or {}
        if not blueprint:
            raise RuntimeError("未找到 blueprint.json，请先生成蓝图")

        raw_chars = _read_json(os.path.join(ndir, "characters.json")) or {}
        character_profiles = None
        if raw_chars:
            character_profiles = {
                "main_character": raw_chars.get("main_character") or {},
                "supporting_characters": raw_chars.get("supporting_characters") or [],
            }
        # 老蓝图回填 _source_briefs（与 run_chapter_demo.main 同款逻辑）
        if "_source_briefs" not in blueprint:
            raw_story = _read_json(os.path.join(ndir, "storyline.json")) or {}
            story_arc = raw_story.get("overall_storyline") or {}
            if raw_chars or story_arc:
                blueprint["_source_briefs"] = OutlinePlanner._render_source_briefs({
                    "protagonist": (raw_chars or {}).get("main_character") or {},
                    "supporting_characters": (raw_chars or {}).get("supporting_characters") or [],
                    "storyline_arc": story_arc,
                })

        # 装配 process_one_chapter 所需的 4 个组件
        planner = OutlinePlanner()
        writer = ChapterCardWriter()
        volume_cache: Dict[int, Dict[str, Any]] = {}
        dkm = None if no_ds else DynamicKnowledgeManager(novel_id=novel_id)

        for idx, ch_no in enumerate(range(start, end + 1), 1):
            _task_progress(t, idx - 1, msg=f"正在写第 {ch_no} 章…")
            try:
                outcome = process_one_chapter(
                    novel_id=novel_id,
                    blueprint=blueprint,
                    chapter_number=ch_no,
                    target_words=target_words,
                    recent_count=5,
                    planner=planner,
                    writer=writer,
                    volume_cache=volume_cache,
                    verbose=False,
                    revise=False,
                    dkm=dkm,
                    character_profiles=character_profiles,
                )
                ok = outcome.get("ok", False)
                wc = outcome.get("word_count", 0)
                _task_log(t, f"[ch{ch_no}] {'PASS' if ok else 'FAIL'} 字数={wc}")
            except Exception as exc:
                _task_log(t, f"[ch{ch_no}] [ERROR] {exc}")

        _task_progress(t, end - start + 1, msg="完成")
        _task_done(t, result={"start": start, "end": end})

    _run_in_thread(_job, task)
    return _ok({"task_id": task["task_id"]})


@app.route("/api/novels/<novel_id>/audit", methods=["GET"])
def api_novel_audit_get(novel_id):
    ndir = _ensure_novel(novel_id)
    return _ok(_read_json(os.path.join(ndir, "audit_report.json")) or {})


@app.route("/api/novels/<novel_id>/audit", methods=["POST"])
def api_novel_audit_run(novel_id):
    ndir = _ensure_novel(novel_id)
    rpt = audit_full_novel(ndir, novel_id=novel_id)
    with open(os.path.join(ndir, "audit_report.json"), "w", encoding="utf-8") as f:
        json.dump(rpt.to_dict(), f, ensure_ascii=False, indent=2)
    return _ok(rpt.to_dict())


# ======================================================================
# 任务状态
# ======================================================================
@app.route("/api/tasks/<task_id>")
def api_task_status(task_id):
    with _tasks_lock:
        t = _tasks.get(task_id)
    if not t:
        return _err("task 不存在", 404)
    # 浅拷贝，截断 logs 太长
    out = {**t, "logs": t["logs"][-50:]}
    return _ok(out)


@app.route("/api/tasks")
def api_task_list():
    with _tasks_lock:
        out = [
            {
                "task_id": t["task_id"], "type": t["type"],
                "novel_id": t["novel_id"], "status": t["status"],
                "started_at": t["started_at"], "ended_at": t["ended_at"],
                "progress": t["progress"],
            }
            for t in _tasks.values()
        ]
    out.sort(key=lambda x: x["started_at"], reverse=True)
    return _ok(out[:50])


# ======================================================================
# 静态前端托管
# ======================================================================
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    # SPA fallback: 任何不存在的路径都返回 index.html（前端路由处理）
    return send_from_directory(FRONTEND_DIR, "index.html")


# ======================================================================
# 入口
# ======================================================================
if __name__ == "__main__":
    print("=" * 64)
    print(f"  InkAI Server 启动")
    print(f"  novels_dir = {config.NOVELS_DIR}")
    print(f"  frontend   = {FRONTEND_DIR}")
    print(f"  API root   = http://127.0.0.1:5000/api")
    print(f"  UI         = http://127.0.0.1:5000/")
    print("=" * 64)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
