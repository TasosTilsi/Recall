---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Engineering Knowledge Graph
status: executing
last_updated: "2026-04-19T22:51:00.000Z"
last_activity: 2026-04-19 — Phase 26 Plan 01 complete
progress:
  total_phases: 9
  completed_phases: 0
  total_plans: 20
  completed_plans: 1
  percent: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14 for v3.0 milestone)

**Core value:** A comprehensive engineering knowledge graph built from git history — every decision, bug fix, and pattern made searchable and interconnected with bidirectional backlinks.
**Current focus:** Phase 25 — teardown

## Current Position

Phase: 25 (teardown) — EXECUTING
Plan: 2 of 2
Status: Executing Phase 25 (Plan 01 complete, Plan 02 pending)
Last activity: 2026-04-15 -- Phase 25 Plan 01 complete

Progress: [_________] 5% (1/20 plans complete)

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

### Pending Todos

(none — fresh milestone start)

### Blockers/Concerns

- Need to decide sqlite-vec version compatibility before IDX/KG implementation
- Plugin install mechanism needs research: how Claude Code plugin install actually works for Python packages

## Session Continuity

Last activity: 2026-04-15 — Phase 25 Plan 01 complete (teardown: legacy modules deleted, skeletons created)
Stopped at: Completed 25-teardown-01-PLAN.md
Resume with: `/gsd:execute-phase 25` for Plan 02 (CLI + MCP server gutting)
