---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Rebuild
status: "Roadmap created. 4 phases, 15 requirements, 100% coverage. Next action: `/gsd:plan-phase 12`"
stopped_at: Completed 12-db-migration/12-03-PLAN.md
last_updated: "2026-03-17T16:38:42.907Z"
last_activity: "2026-03-09 — v2.0 roadmap created (4 phases: 12 DB Migration, 13 Multi-Provider LLM, 14 Graph UI Redesign, 15 Local Memory System)"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 5
  completed_plans: 2
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-09 after v1.1 milestone complete)

**Core value:** Context continuity without repetition — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.
**Current focus:** Milestone v2.0 Rebuild — roadmap created, next: `/gsd:plan-phase 12`

## Current Position

Phase: Not started (roadmap defined, ready to plan Phase 12)
Status: Roadmap created. 4 phases, 15 requirements, 100% coverage. Next action: `/gsd:plan-phase 12`
Last activity: 2026-03-09 — v2.0 roadmap created (4 phases: 12 DB Migration, 13 Multi-Provider LLM, 14 Graph UI Redesign, 15 Local Memory System)

Progress: [░░░░░░░░░░] 0% (v2.0 milestone — 0/4 phases started)

## v2.0 Phase Summary

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 12. DB Migration | Replace KuzuDB with LadybugDB (embedded default) + Neo4j opt-in; remove all 3 Kuzu workarounds | DB-01, DB-02 | Not started |
| 13. Multi-Provider LLM | Switch LLM providers via `llm.toml` `[provider]` section; backward compatible with Ollama | PROV-01, PROV-02, PROV-03, PROV-04 | Not started |
| 14. Graph UI Redesign | shadcn/ui dual-view table + graph replacing react-force-graph-2d; driver-agnostic reads | UI-01, UI-02, UI-03, UI-04 | Not started |
| 15. Local Memory System | All 6 Claude Code hooks, Ollama summarization, 3-layer progressive disclosure MCP, SessionStart injection | MEM-01, MEM-02, MEM-03, MEM-04, MEM-05 | Not started |

## Performance Metrics

**Velocity (v1.1 reference):**
- Total plans completed: 14 (v1.1)
- Average duration: ~9 min/plan
- Total execution time: 8 days

**By Phase (v1.1 summary):**

| Phase | Plans | Status |
|-------|-------|--------|
| 09. Smart Retention | 5/5 | Complete (human approved 2026-03-06) |
| 10. Configurable Capture Modes | 4/4 | Complete (2026-03-08) |
| 11. Graph UI | 5/5 | Complete (2026-03-08) |
| 11.1. Gap Closure — Graph UI Retention Wiring | commits-only | Complete (2026-03-09) |

**v2.0 (in progress):**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| — | — | — | — |

*Updated after each plan completion*
| Phase 12-db-migration P01 | 5 | 2 tasks | 4 files |
| Phase 12-db-migration P03 | 2 | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Key v2.0 architectural decisions from research:

- [v2.0 research]: LadybugDB (`real-ladybug>=0.15.1`) is primary embedded path — community KuzuDB fork with near-identical API, lowest migration effort
- [v2.0 research]: Vendor `LadybugDriver` locally (~280 lines) if graphiti-core PR #1296 not yet merged — replace with official driver when released
- [v2.0 research]: Neo4j via Docker Compose is opt-in power path — `graphiti-core[neo4j]` already ships a first-class driver
- [v2.0 research]: Phase 12 plan MUST start with spike — install LadybugDB, verify 3 workarounds still needed, check PR #1296 status before writing plan tasks
- [v2.0 research]: Three `service.py` direct `import kuzu` calls (`list_edges_readonly`, `list_entities_readonly`, `get_entity_by_uuid_readonly`) must be rewritten to `driver.execute_query()` in Phase 12
- [v2.0 research]: `_create_fts_indices()` in `graph_manager.py` hardcoded to `GraphProvider.KUZU` — first change: delete method and all call sites
- [v2.0 research]: Integration tests against real (non-mocked) backend required in Phase 12 — mock-based tests provide zero migration coverage
- [v2.0 research]: openai SDK `base_url` overrides for multi-provider (Phase 13) — decision locked from v1.1 research; no LiteLLM
- [v2.0 research]: Phase 14 (Graph UI) must follow Phase 12 — UI reads via `service.py` methods being rewritten in Phase 12
- [v2.0 research]: Phase 15 (Local Memory) must follow Phase 12 — entity deduplication quality depends on FTS correctness validated in Phase 12
- [Phase 12-db-migration]: LadybugDriver must be vendored locally (~280 lines): real_ladybug provides only C bindings, no graphiti-compatible driver
- [Phase 12-db-migration]: GraphProvider.LADYBUG absent in graphiti-core 0.28.1: use GraphProvider.KUZU as alias (identical Cypher/FTS dialect)
- [Phase 12-db-migration]: kuzu and real_ladybug are incompatible in same Python process: lazy import real_ladybug in tests until kuzu fully removed in Wave 2
- [Phase 12-db-migration]: Row access changed from positional (row[0]) to dict-keyed (row['uuid']) — execute_query() returns list[dict] keyed by Cypher RETURN aliases
- [Phase 12-db-migration]: read_only=True dropped from readonly methods — not applicable to execute_query() abstraction; LadybugDB/Neo4j handle read isolation at driver level

### Phase 12 Pre-checks Required at Plan Start

1. Check graphiti-core PR #1296 status — merged+released → use official driver; not merged → vendor locally
2. Install `real-ladybug==0.15.1` and empirically verify all 3 KuzuDB workarounds (each may be fixed or still needed)
3. If LadybugDB fails verification (API drift, missing FTS/vector) → pivot to FalkorDB server path (built-in driver in graphiti-core 0.28.1)
4. Do NOT write Phase 12 plan tasks until spike resolves the backend choice

### Roadmap Evolution

- Phase 12 added: DB Migration — LadybugDB default + Neo4j opt-in (must be first; unblocks all other v2.0 phases)
- Phase 13 renumbered: Multi-Provider LLM (was Phase 12 in pre-roadmap STATE.md)
- Phase 14 renumbered: Graph UI Redesign (was Phase 13 in pre-roadmap STATE.md)
- Phase 15 renumbered: Local Memory System (was Phase 14 in pre-roadmap STATE.md)

### Pending Todos

1. **Distribution/polish phase** — PATH detection in `graphiti mcp install`, codebase refactor sweep, Claude plugin configuration
   → `.planning/todos/pending/2026-02-23-create-distribution-polish-phase-for-plugin-path-and-refactor.md`

### Blockers/Concerns

- **Phase 12 spike required before planning**: LadybugDB v0.15.1 may have diverged from Kuzu 0.11.3 API post-v0.12.0 — empirical verification mandatory before writing plan tasks
- **retention.db UUID remapping**: After Phase 12 migration, old pin UUIDs will not match new entity UUIDs — either clear `retention.db` at migration time or implement a UUID remapping pass (decide during Phase 12 planning)

## Session Continuity

Last session: 2026-03-17T16:38:42.905Z
Stopped at: Completed 12-db-migration/12-03-PLAN.md
Resume with: `/gsd:plan-phase 12`
