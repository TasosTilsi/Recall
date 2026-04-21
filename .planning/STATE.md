---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 31-01-PLAN.md
last_updated: "2026-04-21T09:31:58.021Z"
last_activity: 2026-04-21
progress:
  total_phases: 9
  completed_phases: 6
  total_plans: 20
  completed_plans: 14
  percent: 20
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14 for v3.0 milestone)

**Core value:** A comprehensive engineering knowledge graph built from git history — every decision, bug fix, and pattern made searchable and interconnected with bidirectional backlinks.
**Current focus:** Phase 31 — ui-adaptation

## Current Position

Phase: 31 (ui-adaptation) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-04-21

Progress: [__________] 20% (8/20 plans complete)

## v3.0 Summary

Major architectural pivot:

- **Remove**: hooks, queue, retention, graphiti-core, LadybugDB, global graph
- **Replace**: SQLite + backlinks + FTS5 as knowledge graph backbone
- **Simplify**: single LLM provider (no fallbacks), 6-command CLI, clean module layout
- **Add**: two Claude skills, Claude plugin install path, semantic search via sqlite-vec (optional)

## Accumulated Context

### Decisions

- [25-01]: importlib.import_module() used instead of try/except ImportFrom in ui_server — AST verification requires zero ImportFrom nodes from deleted modules regardless of nesting
- [25-01]: graph_service stubbed to None in app.py — Phase 31 will wire DatabaseManager; clean stub beats try/except swallowing init error
- [v3.0 planning]: Drop graphiti-core + LadybugDB entirely — bi-temporal model unnecessary when git provides temporal dimension; entity resolution complexity not justified for git history use case
- [v3.0 planning]: SQLite chosen over ChromaDB — structured queries + FTS5 + backlinks are primary access patterns; chromadb is vector-first and wrong fit
- [v3.0 planning]: No fallback chains in LLM config — single configured provider; simpler code, explicit failure
- [v3.0 planning]: Python stays (not TypeScript rewrite) — 500+ commit history, UI already TypeScript; backend rewrite in TS has no functional gain
- [v3.0 planning]: Plugin installs skills + MCP server — not CLI (user manages Python env separately); Claude plugin = skill wiring + MCP registration in ~/.claude/settings.json
- [v3.0 planning]: `recall sync` auto-inits silently if no DB — zero friction first-use; no prompt required
- [v3.0 planning]: Dual install paths — `pipx install recall-kg` for CLI users; `claude plugin install <repo>` for Claude users
- [26-01]: Legacy src/config/ package removed — Python cannot have both src/config.py and src/config/ directory; old package was v2.0 only; new src/config.py is v3.0 canonical config loader
- [26-01]: DatabaseManager is synchronous (sqlite3) — no async at DB layer; CLI and indexer drive the event loop above this layer
- [26-01]: embeddings table conditionally created based on config.embeddings presence — zero overhead when semantic search not configured
- [Phase 28-git-extractor-indexer]: CommitRecord.diff populated eagerly at walk time — simplifies downstream code
- [Phase 28-git-extractor-indexer]: Per-commit diff truncated to 800 chars in prompt, global diff to 4000 chars in fetch_diff
- [28-02]: commit_sha set to batch[0].sha for all entities — batch-level attribution deterministic for DB upserts
- [28-02]: Subprocess errors (CalledProcessError, TimeoutExpired) return [] — caller handles retry/skip logic
- [28-02]: Missing 'entities' key in valid JSON returns [] — defensive against unexpected LLM output shapes
- [Phase 28]: FK constraint on entities.commit_sha requires stub commits row before inserting entities — _insert_entities does INSERT OR IGNORE on commits first
- [Phase 28]: _commits_after_sha returns all commits when sha not found — structlog warning rather than raising, safe fallback for missing history
- [Phase 29-cli-commands]: Indexer exports run_init/run_sync functions (not GitIndexer class) — init_cmd and sync_cmd call these directly
- [Phase 29-cli-commands]: check_health takes Config argument — health_command loads config first, passes to check_health, reads HealthResult dataclass
- [Phase 29-cli-commands]: _find_git_root() helper duplicated in init_cmd/sync_cmd — walks cwd parents for .git directory
- [Phase 29-cli-commands]: search_cmd implements FTS5/semantic/backlinks directly against SQLite — GraphService not present in v3.0 layout
- [Phase 29-cli-commands]: context_settings allow_interspersed_args=True required on search Typer sub-app for natural arg+option ordering
- [Phase 29-cli-commands]: tomllib (stdlib) for TOML read + tomli-w for write — toml library not installed; added tomli-w to pyproject.toml
- [Phase 30-mcp-server]: Query helpers added to DatabaseManager directly (not separate layer) — tools.py calls db directly
- [Phase 30-mcp-server]: Schema column aliases in get_backlinks() SQL map from_id/to_id/relationship to documented interface names
- [Phase 30-mcp-server]: BFS backlink traversal in Python with visited-set (not recursive CTE) — cycle-safe, testable
- [Phase 30-mcp-server]: serve() import deferred inside mcp CLI command body — prevents FastMCP logging side effects at recall startup time
- [Phase 31]: All UI route handlers synchronous (def not async def) — sqlite3 blocking, no async benefit
- [Phase 31]: create_app() does not call db.init_db() — UI server read-only; init is indexer responsibility

### Pending Todos

(none — fresh milestone start)

### Blockers/Concerns

- Need to decide sqlite-vec version compatibility before IDX/KG implementation
- Plugin install mechanism needs research: how Claude Code plugin install actually works for Python packages

## Session Continuity

Last activity: 2026-04-19 — Phase 28 Plan 02 complete (extract_batch LLM engine implemented)
Stopped at: Completed 31-01-PLAN.md
Resume with: `/gsd:execute-phase 28` for Phase 28 Plan 03 (indexer wiring)
