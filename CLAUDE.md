# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start the web server
python start_web.py             # → http://localhost:5000

# Or run the app directly
python app.py                   # Flask on port 5000

# Legacy CLI entry point
python main.py                  # Interactive terminal workflow
```

There is no test suite or linting configuration. Verify changes by starting the server and exercising the web UI manually.

## Architecture

A monolithic Flask + multi-agent pipeline for AI-assisted long-form fiction generation. The system reads intent from a user, then runs a fixed sequence of LLM-powered agents to produce novel chapters.

### Core files

- **`app.py`** (1496 lines) — Flask API + web server. Serves the frontend SPA and exposes the REST API. All client interaction flows through here.
- **`inkai_workflow_optimized.py`** (1649 lines) — The core orchestrator (`InkAIWorkflowOptimized`). A 140KB state machine that sequences agent calls for both the creation pipeline (tags → characters → storyline → chapter) and the continuation pipeline (knowledge base → continuation storyline → continuation chapter → quality assessment).
- **`quick_continuation_executor.py`** (900 lines) — Async continuation engine. Runs the per-chapter generation loop in background threads with progress tracking.
- **`data_manager.py`** (1024 lines) — Persistence layer. All state is stored as JSON files under `data/novels/<uuid>/`. No database.
- **`workflow_context.py`** (417 lines) — Mutable context object passed between workflow steps. Holds novel ID, tags, characters, storyline, and caching state.
- **`base_agent.py`** (351 lines) — Abstract base class for all agents. Provides `call_llm()` (3 retries with exponential backoff, raises on final failure) and `parse_json_response()`. Uses the OpenAI-compatible client pointed at Zhipu AI GLM-4.5-flash.
- **`config.py`** — API keys, model name, quality thresholds, tag library, and file paths. Module-level `os.makedirs` runs at import time.

### Agents (`agents/`, 26 files)

25 specialized agents, each implementing `BaseAgent`:

| Group | Count | Purpose |
|-------|-------|---------|
| Creation | 5 | Tag selection, character creator, storyline generator, chapter writer, quality assessor |
| Continuation | 3 | Novel continuation agent, continuation storyline generator, continuation chapter writer |
| Assessment | 6 | Per-dimension consistency auditors (character, plot, world, style, reader experience, long-term) |
| Improvement | 11 | Targeted fixers — one per dimension, plus chapter improver, storyline improver, character improver |

Agent input/output contracts are defined in each agent's `process()` method. There is no formal schema enforcement — agents pass `Dict[str, Any]` and rely on LLM JSON parsing.

### Frontend

Single-page Bootstrap 5 app at `frontend/index.html` + `frontend/app.js` + `frontend/styles.css`. The JS is a single large file (~313KB) with inline event handlers (no framework). It calls the Flask API and renders responses directly into DOM via `innerHTML`.

### Data model

Each novel lives at `data/novels/<uuid>/`:

| File | Content |
|------|---------|
| `metadata.json` | Title, status, timestamps |
| `tags.json` | Selected genre tags |
| `characters.json` | Main character + supporting cast |
| `storyline.json` | Three-act structure, world setting |
| `chapter_*.json` | Per-chapter metadata and content |
| `chapter_*.txt` | Chapter prose text |
| `*_quality_assessment.json` | Quality audit results |

Knowledge graphs are stored separately at `data/knowledge_graphs/<id>.json`.

### Pipeline flows

**Creation**: User input → TagSelector → CharacterCreator → StorylineGenerator → ChapterWriter → QualityAssessor → save

**Continuation**: NovelContinuationAgent (build knowledge base) → ContinuationStorylineGenerator → ContinuationChapterWriter → assess → improve if below threshold → save → repeat

### LLM provider

Zhipu AI (智谱) GLM-4.5-flash via OpenAI-compatible endpoint. The `base_agent.py` creates an `OpenAI` client pointed at the Zhipu base URL. No streaming support. Max 8192 output tokens per call.

### Key limitations

- **No concurrency control for shared state**: `data_manager.py` writes JSON files without any file locking. Concurrent chapter generation or web requests could corrupt novel data.
- **Monolithic state machine**: `inkai_workflow_optimized.py` is the bottleneck. All workflow logic is hardcoded in one class with no plugin or extension mechanism.
- **No rate limiting at the application level**: Relies entirely on the LLM provider's rate limits.
- **No input validation on API endpoints**: `app.py` passes raw request payloads directly to agents without schema validation or sanitization.
- **Module-level side effects**: `config.py` creates directories on import. Importing the config module in a read-only environment will fail.
- **Embedding service is a stub**: The `core/` modules reference `EmbeddingService` but there is no actual embedding implementation in this version. Background tasks that require embeddings will fail silently.
