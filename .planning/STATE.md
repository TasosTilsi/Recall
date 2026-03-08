---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Advanced Features
status: completed
stopped_at: Completed 10-04-PLAN.md
last_updated: "2026-03-08T00:28:24.947Z"
last_activity: "2026-03-06 — 09-05 human-approved: stale/pin/unpin live-verified, 272 tests passing"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 9
  completed_plans: 9
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01 after v1.1 milestone start)

**Core value:** Context continuity without repetition — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.
**Current focus:** Milestone v1.1 Advanced Features — Phase 10: Capture Modes (Phase 9 complete)

## Current Position

Phase: 9 of 12 (Smart Retention) — COMPLETE
Plan: 05 complete (5/5 plans done) — human approved
Status: Phase 9 complete, ready for Phase 10
Last activity: 2026-03-06 — 09-05 human-approved: stale/pin/unpin live-verified, 272 tests passing

Progress: [███░░░░░░░] 25% (v1.1 milestone — 1/4 phases complete, 5/5 plans in Phase 9)

## Performance Metrics

**Velocity (v1.0 reference):**
- Total plans completed: 62 (v1.0)
- Average duration: ~12 min/plan
- Total execution time: ~27 days

**By Phase (v1.0 summary):**

| Phase | Plans | Status |
|-------|-------|--------|
| 01–08.9 (all v1.0 phases) | 62/62 | Complete |
| 09. Smart Retention | 5/5 | Complete (human approved 2026-03-06) |
| 10. Capture Modes | 0/TBD | Not started |
| 11. Graph UI | 0/TBD | Not started |
| 12. Multi-Provider LLM | 0/TBD | Not started |

*Updated after each plan completion*

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 09-smart-retention P01 | 3 min | 2 tasks | 5 files |
| Phase 09-smart-retention P02 | 22 | 3 tasks | 4 files |
| Phase 09-smart-retention P03 | 2 | 2 tasks | 2 files |
| Phase 09-smart-retention P04 | 3 | 2 tasks | 2 files |
| Phase 09-smart-retention P05 | ~8 (incl. verify) | 3 tasks | 6 files |
| Phase 10-configurable-capture-modes P01 | 8 | 1 tasks | 2 files |
| Phase 10-configurable-capture-modes P02 | 8 | 2 tasks | 2 files |
| Phase 10-configurable-capture-modes P03 | 10 | 2 tasks | 4 files |
| Phase 10-configurable-capture-modes P04 | 3 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Key v1.1 architectural decisions from research:

- [v1.1 research]: SQLite sidecar (`~/.graphiti/retention.db`) for retention metadata — graphiti-core EntityNode has no TTL fields
- [v1.1 research]: APScheduler 3.x (pinned `<4.0`) for in-process TTL sweeps — v4 API is a complete rewrite
- [v1.1 research]: Docker Kuzu Explorer (`kuzudb/explorer`) for graph UI — zero custom UI code, read-only volume mount
- [v1.1 research]: openai SDK 2.x with `base_url` overrides for multi-provider — covers OpenAI, Groq, compatible endpoints; rejects LiteLLM
- [v1.1 research]: Sanitize-then-filter invariant for capture modes — security gate unconditional regardless of mode
- [v1.1 research]: Phase 12 deferred last — highest regression risk (client.py decomposition touches every graph operation)
- [Phase 09-smart-retention]: stdlib sqlite3 only for RetentionManager — no additional dependencies
- [Phase 09-smart-retention]: retention_days minimum 30 enforced in load_config() with structlog warning, default 90
- [Phase 09-smart-retention]: Lazy imports of get_retention_manager inside method bodies to avoid circular import from src.graph.service to src.retention
- [Phase 09-smart-retention]: uuid field added to list_entities() and get_entity() result dicts — required for archive filter via e.get('uuid')
- [Phase 09-smart-retention]: Reactivation fast path in add(): skip EntityNode.get_by_group_ids() when archive_state is empty (most add() calls are a no-op)
- [Phase 09-smart-retention]: stale_command capped at 25 rows by default with summary line when more exist
- [Phase 09-smart-retention]: compact --expire branch returns early before existing dedup logic — zero risk to dedup path
- [Phase 09-smart-retention]: Use get_service()._get_group_id() in pin.py to guarantee scope_key matches retention sidecar values
- [Phase 09-smart-retention]: graphiti_stale MCP tool uses --format json --all for full parseable stale list without display cap
- [Phase 09-smart-retention]: Patch test targets at src.cli.commands.X.get_service not src.graph.get_service — modules bind import at load time
- [Phase 09-smart-retention]: Auto-fix compact.py: except typer.Exit: raise before except Exception — typer.Exit extends RuntimeError
- [Phase 09-smart-retention]: list_stale() capping is CLI responsibility — stale_command had erroneous show_all kwarg removed
- [Phase 09-smart-retention]: graphiti-core exposes .driver (public) not ._driver (private) — use graphiti.driver in service.py
- [Phase 10-configurable-capture-modes]: Wave 0 TDD: test scaffold written first, NARROW/BROAD prompts added to summarizer.py, 4 CLI tests remain RED for Plan 10-03
- [Phase 10-configurable-capture-modes]: capture_mode default is 'decisions-only' — narrower scope is the safe default; users opt into broader capture
- [Phase 10-configurable-capture-modes]: BATCH_SUMMARIZATION_PROMPT alias points to BROAD prompt for backward compatibility — preserves pre-Phase-10 behavior
- [Phase 10-configurable-capture-modes]: Security gate (sanitize_content) runs unconditionally before any capture_mode prompt selection — locked Phase 2 invariant
- [Phase 10-configurable-capture-modes]: allowed_values enforcement happens after _parse_value() and before _set_nested_value() in --set handler — clean separation of type parsing and domain validation
- [Phase 10-configurable-capture-modes]: load_config() called once per process_pending_commits() invocation — acceptable disk I/O, no caching needed
- [Phase 10-configurable-capture-modes]: FREE_FORM_EXTRACTION_PROMPT alias retained pointing to BROAD prompt for backward compatibility; capture_mode='decisions-only' default; load_config() called once at GitIndexer.run() start to minimize disk reads

### Pending Todos

1. **Distribution/polish phase** — PATH detection in `graphiti mcp install`, codebase refactor sweep, Claude plugin configuration
   → `.planning/todos/pending/2026-02-23-create-distribution-polish-phase-for-plugin-path-and-refactor.md`

### Blockers/Concerns

- **Phase 12 pre-check required**: Verify graphiti-core 0.28.1 internal openai version pin (`pip show graphiti-core` + inspect METADATA) before writing Phase 12 plan — pin conflict could block openai SDK 2.x addition
- **Phase 11 pre-check required**: Verify `kuzudb/explorer` Docker image version compatible with Kuzu 0.11.3 schema during Phase 11 plan creation
- ~~**Phase 9 pre-check required**: Confirm installed graphiti-core version matches `==0.28.1` pin~~ — Phase 9 complete

## Session Continuity

Last session: 2026-03-08T00:28:24.942Z
Stopped at: Completed 10-04-PLAN.md
Resume file: None
