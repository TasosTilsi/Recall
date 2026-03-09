# Graphiti Knowledge Graph

## What This Is

A local knowledge graph system with persistent graph storage, defense-in-depth secret filtering, automatic context capture from git commits and conversations, local-first git history indexing, a full MCP server for Claude Code integration, smart knowledge retention, configurable capture modes, and a browser-based graph visualization UI. It maintains personal preferences globally and project knowledge locally — automatically, without manual effort.

## Core Value

**Context continuity without repetition** — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.

## Current Milestone: v2.0 Rebuild

**Goal:** Replace KuzuDB (archived Oct 2025) with a maintained embedded backend (LadybugDB default, Neo4j opt-in). Add full Claude Code hook lifecycle (6 hooks) with session-start context injection and progressive disclosure MCP search. Keep graphiti-core's graph engine — entity resolution, typed edges, bi-temporal model are the ceiling for the product's value.

**Target features:**
- DB backend swap: LadybugDB (embedded, no container) default + Neo4j (Docker Compose) opt-in — removes all 3 Kuzu workarounds
- Multi-provider LLM (Phase 12): OpenAI, Groq, any OpenAI-compatible endpoint via `[provider]` in `llm.toml`
- Graph UI redesign (Phase 13): shadcn/ui dual-view table + graph (replaces react-force-graph-2d)
- Local memory system (Phase 14): 6-hook Claude Code lifecycle, session-start context injection, Ollama summarization, progressive disclosure MCP search

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
- [ ] **MEM-01**: All 6 Claude Code hooks (SessionStart, SessionResume, UserPromptSubmit, PostToolUse, Notification, SessionEnd) fire and return within 100ms (fire-and-forget)
- [ ] **MEM-02**: Tool observations compressed by local Ollama into structured summaries, stored in chosen DB backend
- [ ] **MEM-03**: `graphiti memory search <query>` returns results via 3-layer progressive disclosure MCP tools
- [ ] **MEM-04**: SessionStart hook injects up to 8K tokens of relevant past observations via `additionalContext`
- [ ] **MEM-05**: Memory features are additive — existing installs with no memory data continue working unchanged

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

---
*Last updated: 2026-03-09 after v1.1 milestone complete*
