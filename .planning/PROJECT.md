# Graphiti Knowledge Graph

## What This Is

A local knowledge graph system with persistent graph storage, defense-in-depth secret filtering, automatic context capture from git commits and conversations, local-first git history indexing, a full MCP server for Claude Code integration, smart knowledge retention, configurable capture modes, and a browser-based graph visualization UI. It maintains personal preferences globally and project knowledge locally — automatically, without manual effort.

## Core Value

**Context continuity without repetition** — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.

## Current Milestone: v2.0 Rebuild

**Goal:** Replace KuzuDB (archived Oct 2025) with a maintained embedded backend (LadybugDB default, Neo4j opt-in). Add 4-hook Claude Code memory system with Option C context injection and incremental git indexing. Keep graphiti-core's graph engine — entity resolution, typed edges, bi-temporal model are the ceiling for the product's value. Execution order: 12 → 13 → 15 → 14.

**Target features:**
- DB backend swap (Phase 12): LadybugDB (embedded, no container) default + Neo4j (Docker Compose) opt-in — removes all 3 Kuzu workarounds
- Multi-provider LLM (Phase 13): OpenAI, Groq, any OpenAI-compatible endpoint via `[provider]` in `llm.toml`
- Local memory system (Phase 15): 4 Claude Code hook scripts (pure Python), Option C context injection, incremental git indexing — executed before Phase 14
- Graph UI redesign (Phase 14): shadcn/ui dual-view table + graph (replaces react-force-graph-2d) — executes after Phase 15

## Requirements

### Validated

<!-- All v1.0 + v1.1 shipped capabilities — validated through testing and human verification -->

- ✓ MCP server with stdio transport + 11 tools (graphiti_add, search, list, show, delete, summarize, compact, capture, health, config, index) — v1.0
- ✓ Kuzu persistent graph database replacing in-memory storage — v1.0
- ✓ Dual-scope graphs: global (`~/.graphiti/global/`) and per-project (`.graphiti/`) — v1.0
- ✓ Defense-in-depth security: file exclusions (.env*, *secret*, *.key), high-entropy detection, pre-commit hook — v1.0
- ✓ Entity-level sanitization: AWS keys, GitHub tokens, JWTs stripped with `[REDACTED:type]` placeholders — v1.0
- ✓ Pre-commit validation hook: secrets + size checks, blocks commits with secrets, warns on large files — v1.0
- ✓ Hybrid cloud/local Ollama LLM: cloud-first with quota tracking, graceful fallback hierarchy — v1.0
- ✓ Local Ollama models: gemma2:9b (quality), llama3.2:3b (speed), nomic-embed-text (embeddings, always local) — v1.0
- ✓ CLI-first architecture: `graphiti`/`gk` entrypoints, 16+ commands, JSON output mode — v1.0
- ✓ Full CLI: add, search, list, show, delete, summarize, compact, config, health, hooks, index, queue, capture — v1.0
- ✓ Automatic git post-commit hook: captures commit context non-blocking (<100ms hook overhead) — v1.0
- ✓ Conversation capture hook: Claude Code Stop hook fires async, non-blocking — v1.0
- ✓ Async background queue: SQLiteAckQueue with retry, dead-letter, bounded capacity, BackgroundWorker — v1.0
- ✓ Local-first git history indexing: on-demand `graphiti index` rebuilds graph from git log/diffs — v1.0
- ✓ Git-safe by design: `.graphiti/` fully gitignored — no knowledge committed, no merge conflicts — v1.0
- ✓ Semantic search: OllamaEmbedder + graph vector similarity, TOON-encoded MCP responses — v1.0
- ✓ Context injection on session start: stale-index detection, top-K node trimming under 8K tokens — v1.0
- ✓ Smart knowledge retention: TTL-based 90-day expiry + reinforcement scoring + `graphiti stale/compact --expire/pin/unpin` — v1.1
- ✓ Configurable capture modes: `decisions-only` / `decisions-and-patterns` via `[capture] mode` in `llm.toml`; unconditional security gate — v1.1
- ✓ Graph UI: `graphiti ui` at `http://localhost:8765` — FastAPI + Next.js static export, ForceGraph2D, scope toggle, read-only mount — v1.1
- ✓ Graph UI retention wiring: access_count, last_accessed_at, pinned, archived in sidebar + canvas filters; ui.port config key — v1.1

### Active

<!-- v2.0 targets -->

- [ ] **DB-01**: KuzuDB replaced with LadybugDB (embedded default) — removes all 3 `graph_manager.py` workarounds; zero-container install for most users
- [ ] **DB-02**: Neo4j opt-in via Docker Compose — power path for teams; `docker compose up` brings full stack
- [ ] **PROV-01**: User can set `[provider]` section in `llm.toml` to switch to OpenAI, Groq, or any OpenAI-compatible endpoint without code changes
- [ ] **PROV-02**: Existing Ollama config works unchanged when no `[provider]` section present (backward compatibility guaranteed)
- [ ] **PROV-03**: `graphiti health` shows active provider name and reachability status
- [ ] **PROV-04**: Provider API key validated at startup with clear error if unreachable (not at first use)
- [ ] **MEM-01**: Four Claude Code hooks (SessionStart ≤5s, UserPromptSubmit ≤6s, PostToolUse fire-and-forget, PreCompact ≤30s) fire within their timeout budgets — pure Python scripts calling GraphService directly, no subprocess or bridge overhead beyond Python startup (~200ms)
- [ ] **MEM-02**: PostToolUse captures Write/Edit/Bash/WebFetch tool calls as graph episodes via the async write queue — Ollama entity extraction runs in background, tool execution never blocked
- [ ] **MEM-03**: UserPromptSubmit injects context using Option C format (`<session_context>` block: `<continuity>` + `<relevant_history>`) via BM25+semantic+graph hybrid retrieval, ≤4000 token budget, temporally-current facts only (superseded facts never injected)
- [ ] **MEM-04**: SessionStart triggers `graphiti sync` (incremental git indexing since last synced commit hash) — skips gracefully if no git repo present
- [ ] **MEM-05**: Hooks installed via `graphiti hooks install` — additive only, no changes to existing `~/.graphiti/` data or config
- [ ] **UI-01**: User can view entities in a dual-view layout (table view + graph view) — replaces react-force-graph-2d
- [ ] **UI-02**: User can toggle between project and global scope in the redesigned UI
- [ ] **UI-03**: User can filter entities by retention status (pinned/archived/stale) in the redesigned UI
- [ ] **UI-04**: UI reads entity data via driver-agnostic API (no direct Kuzu reads) — works with any v2.0 backend
- [ ] **PERF-01**: Git history indexing completes in under 2 minutes for a 30-commit repo — `claude -p` batch extraction replaces per-commit Ollama LLM calls
- [ ] **PERF-02**: Session summary generation completes in under 10 seconds — `ClaudeCliLLMClient` replaces Ollama for session_stop.py summarizer
- [ ] **PERF-03**: Context injection on UserPromptSubmit completes in under 0.5 seconds at 1000+ nodes — FTS-first Layer 1 retrieval replaces full vector search for keyword-matching prompts

### Out of Scope

- Real-time collaboration — async git-based sharing; collaboration via shared git
- Multi-user authentication — personal tool; team sharing through git
- GraphQL API — MCP protocol is the standard
- Distributed deployment — local-only personal dev tool
- Mobile apps — Desktop/CLI only
- Cloud-native architecture — local-first always; runs on dev machine
- LiteLLM abstraction layer — openai SDK `base_url` overrides cover all needed providers with less complexity

## Context

**Shipped v1.0 (2026-03-01):** 18 phases, 62 plans. ~44,453 lines Python. 247 commits.
**Shipped v1.1 (2026-03-09):** 4 phases (9–11.1), 14 plans. 92 additional commits. Added ~14,585 lines Python + 341 lines TypeScript (Graph UI).
Tech stack: Python 3.12, Kuzu 0.11.3 (to be replaced), graphiti-core 0.28.1, FastMCP, Typer, Rich, detect-secrets, GitPython, Next.js 16, react-force-graph-2d.
LLM: Cloud Ollama (chat-only) + local Ollama (gemma2:9b, llama3.2:3b, nomic-embed-text).

**v2.0 pre-checks required at planning kickoff:**
- LadybugDB spike: confirm it slots into graphiti-core's Kuzu provider path without new workarounds
- FalkorDB Lite graphiti-core #1240: merged yet? If so, evaluate as alternative default
- What from v1.1 proved genuinely useful in daily practice vs theoretically useful?

**Known tech debt:**
- `process_queue()` returns `(0, 0)` placeholder counts (documented deferral)
- `local_auto_start` config field deferred with TODO in `src/llm/client.py`
- Stale docstring in `src/hooks/installer.py:479` ("journal validation" → should be "secrets scanning")
- `src/indexer/indexer.py` calls `service._get_graphiti()` private method — fragile coupling, works correctly
- `GraphSelector` dead export in `src/storage/` — never imported externally
- VALIDATION.md nyquist_compliant frontmatter never updated to `true` after Wave 0 tests passed (stale)

**API key note:** Cloud Ollama API key lacks embed endpoint access. `_is_cloud_available("embed")` always returns False. Cloud used for chat/generate only; embeddings always local.

## Constraints

- **Tech Stack**: graphiti-core graph engine stays — entity resolution, typed edges, bi-temporal model are non-negotiable; DB backend replaceable
- **LLM Provider**: Cloud Ollama (chat) primary, local Ollama fallback — cost efficiency; v2.0 adds openai-compatible providers
- **Local Models**: gemma2:9b (quality), llama3.2:3b (speed), nomic-embed-text (embeddings) — CPU-optimized
- **Machine**: Intel i7-13620H (16 threads), 32GB RAM, integrated GPU only — CPU-only inference
- **Performance**: Non-blocking capture, async processing — never slow down development workflow
- **Security**: Git-safe by default, strict filtering — sanitize-before-mode-filter invariant is non-negotiable
- **Storage**: Separate graphs per project + global — isolated, no interference
- **Interface Priority**: CLI first, then hooks and MCP — CLI is foundation, others wrap it
- **Language**: Python 3.12+ — existing codebase language

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-first architecture | Single source of truth; hooks and MCP wrap CLI to avoid logic duplication | ✓ Good |
| Kuzu instead of in-memory | Better persistence, performance, graph query capabilities | ⚠️ Revisit — Kuzu archived Oct 2025; replacing in v2.0 |
| Cloud Ollama with local fallback | Free tier for chat; local models when quota exhausted or embed API unsupported | ✓ Good — revealed embed API gap, handled separately |
| Separate global + per-project graphs | Global preferences everywhere, project knowledge isolated and git-scoped | ✓ Good |
| Decisions-only mode by default | Safer captures; high-level knowledge without code/data leakage | ✓ Good — made explicit in v1.1 |
| Background async capture | Never blocks dev work; queues locally and processes in background thread | ✓ Good |
| Strict security filtering | File exclusions + entity sanitization ensures git-safe knowledge graphs | ✓ Good |
| Sanitize-before-mode-filter invariant | Security gate unconditional regardless of capture mode — secrets never captured in any mode | ✓ Good — established in v1.1 |
| Local-first indexing (Phase 7.1) | .graphiti/ gitignored; on-demand git history rebuild eliminates merge conflicts | ✓ Good |
| gemma2:9b for primary LLM | Best quality/performance on CPU for structured tasks | ✓ Good |
| nomic-embed-text for embeddings | Excellent embedding model, always local | ✓ Good |
| sys.executable for CLI path resolution | Avoids PATH inheritance issues when Claude Code runs MCP subprocesses | ✓ Good — fixed critical MCP bug |
| TOON encoding for MCP responses (3+ items) | Compact wire format for large list responses; JSON for scalars | ✓ Good |
| SQLiteAckQueue with multithreading=True | Thread-safe queue when ollama_chat runs in run_in_executor thread | ✓ Good |
| SQLite sidecar for retention metadata | graphiti-core EntityNode has no TTL fields — sidecar avoids schema fork | ✓ Good — v1.1 |
| APScheduler 3.x (pinned <4.0) for retention sweeps | v4 API is a complete rewrite; 3.x stable and sufficient | ✓ Good — v1.1 |
| Graph UI: FastAPI + Next.js static export | Zero external dependencies; pre-built static bundle committed to git | ✓ Good — v1.1 |
| openai SDK base_url overrides for multi-provider | Covers OpenAI/Groq/compatible endpoints; no LiteLLM abstraction needed | ✓ Good — v2.0 approach locked |
| graphiti-core stays for v2.0 | Entity resolution, typed relationship edges, bi-temporal model — these justify the dependency | ✓ Good — confirmed at v2.0 planning |
| Option C context injection format | Narrative continuity + temporal facts (`<continuity>` + `<relevant_history>`); priority: recent session → recent git → older session → older git; ≤4000 token budget | ✓ Locked — v2.0 Phase 15 |
| Hook path: pure Python scripts | Hooks call GraphService directly via Python; no TypeScript layer, no bridge daemon; Python startup ~200ms fits within timeout budgets | ✓ Locked — v2.0 Phase 15 |
| Git indexing: batch incremental | `graphiti init` full history + `graphiti sync` delta on SessionStart; episodes fed oldest-first; gracefully skips non-git dirs | ✓ Locked — v2.0 Phase 15 |
| Phase execution order: 12→13→15→14 | Phase 15 (memory) needs Phase 13 LLM abstraction; Phase 14 (UI) independent of memory, can run after | ✓ Locked — v2.0 planning |
| ClaudeCliLLMClient via `claude -p` subprocess | No `ANTHROPIC_API_KEY` available — `claude -p` uses Claude Code subscription auth; same pattern as claude-mem's `unstable_v2_prompt()`; falls back to Ollama if `claude` not on PATH | ✓ Locked — v2.0 Phase 20 |
| FTS-first 3-layer progressive disclosure | LadybugDB FTS5 indices already exist; Layer 1 (FTS compact, <50ms) → Layer 2 (chronological, no LLM) → Layer 3 (vector for filtered IDs only); adapted from claude-mem | ✓ Locked — v2.0 Phase 20 |
| Batch extraction: 10 commits per `claude -p` call | 10× fewer LLM calls vs per-commit extraction; single call returns entities/relationships for whole batch | ✓ Locked — v2.0 Phase 20 |

---
*Last updated: 2026-04-03 — Phase 21 complete (Knowledge Quality Uplift): enriched BATCH_EXTRACTION_PROMPT with code block entity extraction + 7 semantic relationship verbs; EntityPanel renders structured metadata chips; parseCodeBlockMeta extracted as standalone module with full test coverage*
