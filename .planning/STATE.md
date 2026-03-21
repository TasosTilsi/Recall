---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Rebuild
status: completed
stopped_at: Completed 18-02-PLAN.md
last_updated: "2026-03-21T21:04:46.134Z"
last_activity: 2026-03-17 — Phase 12 DB Migration complete; KuzuDB replaced with LadybugDB; human smoke test approved
progress:
  total_phases: 8
  completed_phases: 7
  total_plans: 28
  completed_plans: 28
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-09 after v1.1 milestone complete)

**Core value:** Context continuity without repetition — Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while sensitive data stays out of git through strict security filtering.
**Current focus:** Milestone v2.0 Rebuild — Phase 12 complete; next: `/gsd:plan-phase 13`

## Current Position

Phase: Phase 12 DB Migration — Complete (2026-03-17)
Status: Phase 12 DB Migration complete (human approved). Next action: `/gsd:plan-phase 13`
Last activity: 2026-03-17 — Phase 12 DB Migration complete; KuzuDB replaced with LadybugDB; human smoke test approved

Progress: [██░░░░░░░░] 25% (v2.0 milestone — 1/4 phases complete)

## v2.0 Phase Summary

| Phase | Goal | Requirements | Status |
|-------|------|--------------|--------|
| 12. DB Migration | Replace KuzuDB with LadybugDB (embedded default) + Neo4j opt-in; remove all 3 Kuzu workarounds | DB-01, DB-02 | Complete (2026-03-17) |
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
| Phase 12-db-migration P02 | 7 | 2 tasks | 5 files |
| Phase 12-db-migration P04 | 7 | 2 tasks | 6 files |
| Phase 12-db-migration P05 | 6 | 2 tasks | 7 files |
| Phase 13-multi-provider-llm P01 | 3 | 2 tasks | 4 files |
| Phase 13-multi-provider-llm P02 | 3 | 2 tasks | 3 files |
| Phase 13-multi-provider-llm P03 | continuation | 2 tasks | 3 files |
| Phase 15-local-memory-system PP01 | 3 | 2 tasks | 5 files |
| Phase 15-local-memory-system P02 | 10 | 2 tasks | 2 files |
| Phase 15-local-memory-system P04 | 5 | 2 tasks | 4 files |
| Phase 15-local-memory-system P05 | 15 | 2 tasks | 2 files |
| Phase 16-rename-cli-consolidation P02 | 12 | 2 tasks | 2 files |
| Phase 16-rename-cli-consolidation P01 | 4 | 2 tasks | 5 files |
| Phase 16-rename-cli-consolidation P03 | 8 | 2 tasks | 14 files |
| Phase 16-rename-cli-consolidation P04 | 9 | 1 tasks | 3 files |
| Phase 14-graph-ui-redesign P02 | 3 | 2 tasks | 2 files |
| Phase 14-graph-ui-redesign P01 | 9 | 2 tasks | 36 files |
| Phase 14-graph-ui-redesign P06 | 15 | 2 tasks | 7 files |
| Phase 14-graph-ui-redesign PP05 | 15 | 2 tasks | 4 files |
| Phase 17-fix-stale-binary-references P02 | 2 | 2 tasks | 2 files |
| Phase 17-fix-stale-binary-references P01 | 5 | 2 tasks | 5 files |
| Phase 18-formal-verification-phases-14-16 P01 | 3 | 2 tasks | 3 files |
| Phase 18-formal-verification-phases-14-16 P02 | 4 | 1 tasks | 2 files |

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
- [Phase 12-db-migration]: Embed SCHEMA_QUERIES locally in ladybug_driver.py — graphiti_core.driver.kuzu_driver has top-level import kuzu which fails post-uninstall; GraphProvider imported from driver.driver instead
- [Phase 12-db-migration]: LadybugDriver.provider = GraphProvider.KUZU — LadybugDB Cypher dialect identical to Kuzu fork; no enum patching needed
- [Phase 12-db-migration]: config sub-app pattern: convert 'config' to Typer sub-app preserving graphiti config (view) and graphiti config init (generate)
- [Phase 12-db-migration]: fail-fast with sys.exit(1) for Neo4j unreachable: named URI message guides user to docker compose command
- [Phase 12-db-migration]: schema version stamp at ~/.graphiti/version.json: detects first v2.0 run; clears retention.db and queue on upgrade
- [Phase 12-db-migration]: install_hooks() install_git param preserved as no-op: backward compatible, callers passing install_git=True won't break
- [Phase 12-db-migration]: get_hook_status() git_hook_installed hardcoded to False: post-commit hook removed; v2.0 invariant
- [Phase 13-multi-provider-llm]: URL-based SDK auto-detection (no explicit type field in TOML) — locked from CONTEXT.md prior session
- [Phase 13-multi-provider-llm]: [cloud]/[local] sections silently ignored when [llm] present — avoids noisy deprecation warnings during migration
- [Phase 13-multi-provider-llm]: llm_embed_api_key defaults to primary_api_key at parse time — simpler for callers, single source of truth
- [Phase 13-multi-provider-llm]: Lazy imports inside make_llm_client/make_embedder — OpenAIGenericClient/OpenAIEmbedder imported only when provider mode active
- [Phase 13-multi-provider-llm]: GraphService calls load_config() once in __init__() and passes result to make_llm_client()/make_embedder() factories
- [Phase 13-multi-provider-llm]: Startup validation skips health/config subcommands; they handle provider interaction themselves
- [Phase 13-multi-provider-llm]: Fallback tier shown as 'configured' not pinged at health time — avoids extra Ollama ping in provider mode
- [Phase 13-multi-provider-llm]: Ollama cloud/local rows suppressed entirely when llm_mode='provider' — mutually exclusive health display
- [Phase 15-01]: sync_command uses full=False to enforce incremental-only semantics (no --full flag exposed)
- [Phase 15-01]: install_global_hooks() uses clean overwrite for graphiti entries; sys.executable for Python interpreter path
- [Phase 15-02]: session_start.py uses sys.executable to locate graphiti CLI (same venv as interpreter)
- [Phase 15-02]: inject_context.py imports get_service() lazily after sys.path fix and uses asyncio.run() inside try/except for standalone subprocess safety
- [Phase 15-04]: memory_app registered via app.add_typer() consistent with hooks_app and queue_app pattern
- [Phase 15-04]: install_global_hooks called unconditionally in install_command after local hooks — no --global-only flag needed
- [Phase 15-05]: Hook paths will change in Phase 16 rename; tests acknowledged as temporary by human reviewer
- [Phase 15-05]: 16 tests written (exceeds plan 13-test minimum) — test_session_start_produces_no_stdout added as extra MEM-01 guard
- [Phase 16-02]: Rename --compact/-c (one-line view) to --one-line/-c to avoid collision with new --compact (archive stale) flag
- [Phase 16-02]: _auto_sync placed after resolve_scope before search spinner — silent, fail-open, bounded by GitIndexer 5-min cooldown (CLI-03)
- [Phase 16-rename-cli-consolidation]: recall/rc entrypoints replace graphiti/gk — same cli_entry function, only pyproject.toml scripts change
- [Phase 16-rename-cli-consolidation]: init and index added to _skip_validation_for — both must work before provider is configured
- [Phase 16-03]: session_start.py calls GitIndexer directly instead of subprocess to recall sync — sync command is deleted, direct call is simpler and eliminates binary name dependency
- [Phase 16-03]: installer.py uninstall_claude_hook detects both graphiti capture and recall note for backward compat during migration
- [Phase 16-04]: GitIndexer lazy-import requires patching src.indexer.GitIndexer not the call-site module
- [Phase 16-04]: TRULY_REMOVED_COMMANDS excludes add/hooks/memory — these words appear in active command descriptions making naive string assertions unreliable
- [Phase 14-graph-ui-redesign]: All 5 new GraphService methods use self._graph_manager (with underscore) and driver.execute_query() — never _get_graphiti()
- [Phase 14-graph-ui-redesign]: get_time_series_counts: Python-level day aggregation from created_at strings, not Cypher date() — LadybugDB date() support unverified
- [Phase 14-graph-ui-redesign]: sys.modules stub for real_ladybug in test file — test isolation without native package requirement
- [Phase 14-01]: migrate_dot_graphiti_to_recall() called at CLI startup in main_callback before load_config; safe no-op on repeat
- [Phase 14-01]: LLMConfig.ui_api_port removed; single ui_port=8765 with backward-compat api_port->port TOML alias
- [Phase 14-06]: DetailPanel breadcrumb state stored as PanelItem[]; fresh open resets to [item]; in-panel navigate appends; ancestor click slices
- [Phase 14-06]: Episodes tab uses fetchDashboard(scope).recent_episodes — no dedicated episodes endpoint needed
- [Phase 14-06]: Entities tab filters out Episodic node type from graph nodes array
- [Phase 14-05]: ActivityHeatmap built as custom SVG grid (no library) — 52-week calendar, blue intensity scale
- [Phase 14-05]: Sigma FA2 physics runs in setTimeout(100ms) after renderer init — non-blocking, non-fatal
- [Phase 17-02]: patch src.llm.config.load_config not src.storage.graph_manager.load_config because load_config is a lazy local import inside _make_driver
- [Phase 17-01]: graphiti_capture (Popen fire-and-forget) deleted — recall_note is the single write tool post-Phase 16
- [Phase 17-01]: Resource URI graphiti://context left unchanged — changing it would break existing Claude Desktop configs
- [Phase 18-01]: verify_phase_14.py follows verify_phase_16.py structure exactly — same Runner class, colored output, argparse flags
- [Phase 18-01]: 14-VERIFICATION.md cites 14-07-SUMMARY.md checkpoint human-verify approved as authoritative evidence for UI visual/interactive checks
- [Phase 18-02]: test_note_command_appends_to_jsonl used .graphiti/ directory but note_cmd.py writes to .recall/ — fixed test path to match actual implementation

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

Last session: 2026-03-21T21:04:46.132Z
Stopped at: Completed 18-02-PLAN.md
Resume with: `/gsd:plan-phase 13`
