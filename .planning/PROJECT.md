# Graphiti Knowledge Graph

## What This Is

A production-ready local knowledge graph system with persistent Kuzu storage, defense-in-depth secret filtering, automatic context capture from git commits and conversations, local-first git history indexing, and a full MCP server for Claude Code integration. It maintains personal preferences globally and project knowledge locally — automatically, without manual effort.

## Core Value

**Context continuity without repetition** — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.

## Current Milestone: v1.1 Advanced Features

**Goal:** Extend the working v1.0 system with smart knowledge retention, configurable capture modes, a local graph visualization UI, and multi-provider LLM support.

**Target features:**
- Smart retention — 90-day expiry + reinforcement scoring for frequently-accessed nodes
- Configurable capture modes — decisions-only (default) vs. decisions-and-patterns
- Performance budgets — enforce latency targets (context injection <100ms, search <200ms)
- `graphiti ui` — localhost graph visualization + monitoring dashboard
- Multi-provider LLM — OpenAI, Anthropic, Groq, any OpenAI-compatible endpoint via `llm.toml`

## Requirements

### Validated

<!-- All v1.0 shipped capabilities — validated through testing and human verification -->

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
- ✓ Conversation capture hook: Claude Code hook fires every 5-10 turns, async non-blocking — v1.0
- ✓ Async background queue: SQLiteAckQueue with retry, dead-letter, bounded capacity, BackgroundWorker — v1.0
- ✓ Local-first git history indexing: on-demand `graphiti index` rebuilds Kuzu graph from git log/diffs — v1.0
- ✓ Git-safe by design: `.graphiti/` fully gitignored — no knowledge committed, no merge conflicts — v1.0
- ✓ Semantic search: OllamaEmbedder + Kuzu vector similarity, TOON-encoded MCP responses — v1.0
- ✓ Context injection on session start: stale-index detection, top-K node trimming under 8K tokens — v1.0

### Active

<!-- Next milestone (v1.1 / Phase 9+) targets -->

- [ ] **KG-11**: Smart knowledge retention — unused knowledge expires after 90 days; reinforcement scoring keeps frequently-accessed nodes
- [ ] **KG-15**: Configurable capture modes — decisions-only (default, already shipped implicitly) vs decisions-and-patterns with stricter sanitization
- [ ] **Perf**: Latency budgets — context injection <100ms p95, search <200ms p95, health <50ms p95 (baseline measured, targets not enforced)
- [ ] **UI**: `graphiti ui` — localhost graph visualization: entity nodes + relationship edges, monitoring dashboard for capture stats
- [ ] **Multi-provider LLM**: `[provider]` section in llm.toml — OpenAI, Anthropic, Groq, any OpenAI-compatible endpoint; no code changes to switch

### Out of Scope

- Real-time collaboration — async git-based sharing replaced by local-first indexing; collaboration via shared git
- Web UI (CLI/MCP interfaces sufficient) — deferred to Phase 10
- Multi-user authentication — personal tool; team sharing through git
- Vector database alternatives — Kuzu + embeddings sufficient and working well
- GraphQL API — MCP protocol is the standard; no need for additional API layer
- Distributed deployment — local-only; personal dev tool
- Mobile apps — Desktop/CLI only
- Cloud-native architecture — local-first always; runs on dev machine without cloud dependencies

## Context

**Shipped v1.0 (2026-03-01):** 18 phases, 62 plans. 44,453 lines Python.
Tech stack: Python 3.12, Kuzu 0.11.3, graphiti-core 0.28.1, FastMCP, Typer, Rich, detect-secrets, GitPython.
LLM: Cloud Ollama (cloud, chat-only) + local Ollama (gemma2:9b, llama3.2:3b, nomic-embed-text).

**Architectural pivot (Phase 7.1):** Replaced journal-based git storage with local-first on-demand indexing. `.graphiti/` fully gitignored — no knowledge committed to git, ever. Removes merge conflicts and LFS complexity.

**Known tech debt:**
- `process_queue()` returns `(0, 0)` placeholder counts (documented deferral)
- `local_auto_start` config field deferred with TODO in `src/llm/client.py`
- Stale docstring in `src/hooks/installer.py:479` ("journal validation" → should be "secrets scanning")
- `src/indexer/indexer.py` calls `service._get_graphiti()` private method — fragile coupling, works correctly
- `GraphSelector` dead export in `src/storage/` — never imported externally

**API key note:** Cloud Ollama API key lacks embed endpoint access. `_is_cloud_available("embed")` always returns False. Cloud used for chat/generate only; embeddings always local.

## Constraints

- **Tech Stack**: graphiti-core + Kuzu — chosen for knowledge graph semantics and embedded DB
- **LLM Provider**: Cloud Ollama (chat) primary, local Ollama fallback — cost efficiency
- **Local Models**: gemma2:9b (quality), llama3.2:3b (speed), nomic-embed-text (embeddings) — CPU-optimized
- **Machine**: Intel i7-13620H (16 threads), 32GB RAM, integrated GPU only — CPU-only inference
- **Performance**: Non-blocking capture, async processing — never slow down development workflow
- **Security**: Git-safe by default, strict filtering — project knowledge must be safe for GitHub
- **Storage**: Separate graphs per project + global — isolated, no interference
- **Interface Priority**: CLI first, then hooks and MCP — CLI is foundation, others wrap it
- **Language**: Python 3.12+ — existing codebase language

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-first architecture | Single source of truth; hooks and MCP wrap CLI to avoid logic duplication | ✓ Good |
| Kuzu instead of in-memory | Better persistence, performance, graph query capabilities | ✓ Good |
| Cloud Ollama with local fallback | Free tier for chat; local models when quota exhausted or embed API unsupported | ✓ Good — revealed embed API gap, handled separately |
| Separate global + per-project graphs | Global preferences everywhere, project knowledge isolated and git-scoped | ✓ Good |
| Decisions-only mode by default | Safer for git commits; captures high-level knowledge without code/data leakage | ✓ Good (implicit — Phase 9 makes it explicit) |
| Background async capture | Never blocks dev work; queues locally and processes in background thread | ✓ Good |
| Strict security filtering | File exclusions + entity sanitization ensures git-safe knowledge graphs | ✓ Good |
| Local-first indexing (Phase 7.1) | .graphiti/ gitignored; no journal committed; on-demand git history rebuild eliminates merge conflicts | ✓ Good — cleaner than journal approach |
| gemma2:9b for primary LLM | Best quality/performance on CPU for structured tasks | ✓ Good |
| llama3.2:3b for fast fallback | Quick operations when speed matters more than quality | ✓ Good |
| nomic-embed-text for embeddings | Excellent embedding model, always local | ✓ Good |
| sys.executable for CLI path resolution | Avoids PATH inheritance issues when Claude Code runs MCP subprocesses | ✓ Good — fixed critical MCP bug |
| TOON encoding for MCP responses (3+ items) | Compact wire format for large list responses; JSON for scalars | ✓ Good |
| SQLiteAckQueue with multithreading=True | Thread-safe queue when ollama_chat runs in run_in_executor thread | ✓ Good |
| Smart retention (90 days unused) | Keeps knowledge fresh; reinforced facts persist longer; configurable | — Pending (Phase 9) |

---
*Last updated: 2026-03-01 after v1.1 milestone start*
