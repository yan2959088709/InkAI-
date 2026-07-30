# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Web server (primary interface)
python server.py                    # Starts on http://127.0.0.1:5000

# New pipeline CLI (recommended workflow)
python run_init_novel.py --genre xianxia --title "九霄道行" --protagonist "林朝歌"
python run_outline_demo.py --novel-id <id>
python run_chapter_demo.py --novel-id <id> --start-chapter 1 --end-chapter 10

# Validation
python run_validate_canon.py --novel-id <id>
python run_validate_volume.py --novel-id <id> --volume 1
python run_full_novel_audit.py --novel-id <id>
```

There is no test suite. Verify changes by starting the server and exercising the web UI, or by running the CLI pipeline on a test novel.

## Architecture

**New pipeline** (recommended): independent CLI scripts that read from and write to disk. State is stored as JSON under `data/novels/<novel_id>/`.

### Core files

- **`server.py`** - Flask API + web server. Serves the frontend SPA and exposes the REST API. All client interaction flows through here.
- **`base_agent.py`** - Abstract base class for all agents. Provides `call_llm()` (3 retries with exponential backoff, raises `RuntimeError` on final failure) and `parse_json_response()`. Includes prompt cache hit diagnostics (DeepSeek `prompt_cache_hit_tokens` / OpenAI `cached_tokens`).
- **`config.py`** - Multi-provider config (dashscope / deepseek / openai) via `PROVIDER_PRESETS`. Embedding/rerank have independent API keys (`INKAI_EMBEDDING_API_KEY`) to avoid cross-provider key reuse failures. Module-level `os.makedirs` runs at import time.
- **`agents/chapter_card_writer.py`** - `ChapterCardWriter`: writes individual chapter text from ChapterCard. Validates word count (±20%, hard cap +30%), protagonist presence (≥2 mentions), must_appear coverage (hard fail for characters/objects). System prompt is static (enables LLM prompt caching); dynamic content (banned_endings, target_word_count) goes in user prompt.
- **`core/outline_planner.py`** - `OutlinePlanner`: generates blueprints and volume chapter cards via LLM. Accepts optional `GenrePack` for genre-aware planning.
- **`core/dynamic_knowledge_manager.py`** - DKM: tracks cross-chapter state (foreshadowing, character appearances, currently-held objects, locations). Call `load_state()` after instantiation; `save_state()` after each chapter.
- **`core/cross_chapter_dedup.py`** - Scans prior chapters for high-frequency phrase fingerprints, injects into banned list for next chapter.

### Agents (`agents/`, 33 files)

| Group | Count | Purpose |
|-------|-------|---------|
| Creation | 10 | Tag selection, character creator, storyline generator, chapter writer (legacy + new ChapterCardWriter), volume validator, etc. |
| Continuation | 4 | Novel continuation agent, continuation storyline/chapter/improver |
| Assessment | 6 | Per-dimension consistency auditors (character, plot, world, style, reader experience, long-term) |
| Improvement | 6 | Targeted fixers - one per assessment dimension |
| Base | 2 | base_continuation_assessor, base_continuation_improver |
| Other | 5 | character_improver, novel_storyline_improver, chapter_summary_generator, enhanced_character_analyzer, etc. |

Agent input/output contracts are defined in each agent's `process()` method. No formal schema enforcement - agents pass `Dict[str, Any]` and rely on LLM JSON parsing.

### Frontend

Single-page Bootstrap 5 + Chart.js app at `frontend/index.html` + `frontend/app.js` + `frontend/styles.css`. Hash-based routing. All API calls go through `Util.req()` which prepends `/api`.

### Data model

Each novel lives at `data/novels/<novel_id>/`:

| File | Content |
|------|---------|
| `metadata.json` | Title, status, timestamps |
| `characters.json` | Main character + supporting cast |
| `storyline.json` | Three-act structure, world setting |
| `outline/blueprint.json` | Whole-novel blueprint (name_whitelist, global_foreshadow_ledger) |
| `outline/volume_<N>_chapters.json` | Volume chapter cards |
| `chapters_demo/chapter_<N>.txt` | Chapter prose |
| `chapters_demo/chapter_<N>.meta.json` | Chapter metadata + validation |
| `dynamic_state/state.json` | DKM state (foreshadowing, character holds, locations) |
| `annotations.json` | Reader annotations |
| `validation/volume_<N>_report.json` | Volume validation report |

### LLM provider

Multi-provider via OpenAI-compatible client. Configured by `INKAI_PROVIDER` env var (dashscope / deepseek / openai, default dashscope). Embedding/rerank use independent keys (`INKAI_EMBEDDING_API_KEY`) since not all providers offer embedding.

### Rate limiting

`core/api_rate_limiter.py` enforces max 2 concurrent LLM calls with 1-second minimum intervals.

### Key limitations

- **No concurrency control for shared state**: `data_manager.py` writes JSON files without file locking. Concurrent chapter generation could corrupt novel data.
- **No input validation on some API endpoints**: `server.py` passes raw request payloads to agents without schema validation.
- **Module-level side effects**: `config.py` creates directories on import. Importing in a read-only environment will fail.
- **Legacy pipeline retained**: `inkai_workflow_optimized.py` (140KB monolith) is frozen but kept for rollback safety. New pipeline is the only recommended path.
