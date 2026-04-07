# Graphiti Knowledge Graph

## What This Is

A local developer memory system running as `recall` (alias `rc`) — knowledge graph backed by LadybugDB (embedded, zero Docker) or Neo4j (opt-in), multi-provider LLM support, 4 Claude Code hook scripts for automatic context capture and injection, a shadcn/ui dual-view graph UI, and a full MCP server. Maintains personal preferences globally and project knowledge locally through incremental git history indexing — automatically, without manual effort.

## Core Value

**Context continuity without repetition** — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.

## Current State

**v2.0 Shipped 2026-04-07** — 13 phases, 48 plans. All 18 requirements delivered.

CLI: `recall` / `rc` — 9-command public surface (`init`, `search`, `list`, `delete`, `pin`, `unpin`, `health`, `config`, `ui`, `note`).
Backend: LadybugDB embedded (default) or Neo4j via Docker Compose (opt-in via `[backend] type = "neo4j"` in `llm.toml`).
LLM: Ollama (legacy) or any OpenAI-compatible provider via `[llm]` section in `llm.toml`.
Hooks: 4 Claude Code scripts — SessionStart (git sync), UserPromptSubmit (FTS-first context injection), PostToolUse (async queue capture), SessionEnd (session summary via `claude -p`).
UI: `recall ui` — shadcn/ui table + Sigma.js WebGL graph, retention filter, node-click detail panel.

## Requirements

### Validated

<!-- All v1.0 + v1.1 + v2.0 shipped capabilities — validated through testing and human verification -->

- ✓ MCP server with stdio transport + tools (recall_add, search, list, delete, note, health, config, index) — v1.0
- ✓ Dual-scope graphs: global (`~/.recall/global/`) and per-project (`.recall/`) — v1.0
- ✓ Defense-in-depth security: file exclusions (.env*, *secret*, *.key), high-entropy detection — v1.0
- ✓ Entity-level sanitization: AWS keys, GitHub tokens, JWTs stripped with `[REDACTED:type]` placeholders — v1.0
- ✓ Hybrid cloud/local Ollama LLM: cloud-first with quota tracking, graceful fallback hierarchy — v1.0
- ✓ Async background queue: SQLiteAckQueue with retry, dead-letter, bounded capacity, BackgroundWorker — v1.0
- ✓ Local-first git history indexing: incremental (`recall search` auto-syncs) or full (`recall init`) — v1.0
- ✓ Git-safe by design: `.recall/` fully gitignored — no knowledge committed, no merge conflicts — v1.0
- ✓ TOON-encoded MCP responses, semantic search via OllamaEmbedder + graph vector similarity — v1.0
- ✓ Smart knowledge retention: TTL-based 90-day expiry + reinforcement scoring + pin/unpin/archive — v1.1
- ✓ Configurable capture modes: `decisions-only` / `decisions-and-patterns`; unconditional security gate — v1.1
- ✓ **DB-01**: KuzuDB → LadybugDB (embedded default, zero Docker); all 3 Kuzu workarounds removed — v2.0
- ✓ **DB-02**: Neo4j opt-in via Docker Compose (`[backend] type = "neo4j"` in `llm.toml`) — v2.0
- ✓ **PROV-01/02**: `[llm]` section in `llm.toml` switches to any OpenAI-compatible provider; Ollama works unchanged when absent — v2.0
- ✓ **PROV-03/04**: `recall health` shows active provider + reachability; fail-fast startup if provider unreachable — v2.0
- ✓ **MEM-01–05**: 4 Claude Code hooks (SessionStart ≤5s, UserPromptSubmit ≤6s, PostToolUse fire-and-forget, SessionEnd); Option C context injection; incremental git sync; additive install — v2.0
- ✓ **CLI-01/02/03**: Tool invocable as `recall`/`rc`; 9-command surface; `recall search` auto-syncs git — v2.0
- ✓ **UI-01–04**: shadcn/ui dual-view (table + Sigma.js WebGL graph); scope toggle; retention filter; driver-agnostic API — v2.0
- ✓ **PERF-01–03**: `claude -p` batch extraction (<2 min for 30 commits); session summaries <10s; FTS-first context injection <50ms Layer 1 — v2.0

### Active

<!-- Next milestone targets — defined during /gsd:new-milestone -->

(none yet — run `/gsd:new-milestone` to define v3.0 targets)

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
**Shipped v1.1 (2026-03-09):** 4 phases (9–11.1), 14 plans. 92 additional commits. Added ~14,585 lines Python + 341 lines TypeScript.
**Shipped v2.0 (2026-04-07):** 13 phases (12–24), 48 plans. 516 total git commits.
Tech stack: Python 3.12, real-ladybug>=0.15.1 (LadybugDB), graphiti-core 0.28.1, FastMCP, Typer, Rich, detect-secrets, GitPython, React 18, shadcn/ui, Sigma.js (WebGL), Recharts.
LLM: Ollama (gemma2:9b / nomic-embed-text) or any OpenAI-compatible provider via `[llm]` in `llm.toml`.

**Known tech debt (post-v2.0):**
- `process_queue()` returns `(0, 0)` placeholder counts (documented deferral)
- `local_auto_start` config field deferred with TODO in `src/llm/client.py`
- `src/indexer/indexer.py` calls `service._get_graphiti()` private method — fragile coupling, works correctly
- `GraphSelector` dead export in `src/storage/` — never imported externally

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
*Last updated: 2026-04-07 after v2.0 milestone — 13 phases (12–24), 48 plans. KuzuDB → LadybugDB, multi-provider LLM, `recall` CLI, 4-hook memory system, shadcn/ui graph UI, fast indexing via `claude -p`. All 18 requirements delivered.*
