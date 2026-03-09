---
phase: 09-smart-retention
verified: 2026-03-06T09:30:00Z
status: passed
score: 7/7 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "graphiti compact --expire archives stale nodes end-to-end — fix: removed show_all=True kwarg from list_stale() call in compact.py line 94 (commit: fix(09-03))"
  gaps_remaining: []
  regressions: []
---

# Phase 9: Smart Retention Verification Report

**Phase Goal:** Smart Retention — automated TTL-based archiving so the graph stays lean without manual cleanup
**Verified:** 2026-03-06T09:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (fix(09-03): remove show_all kwarg from list_stale() in compact --expire path)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | RetentionManager is importable and initializes with correct SQLite schema | VERIFIED | src/retention/manager.py (245 lines), WAL mode at line 82, three-table schema at lines 19-41, all CRUD methods present |
| 2 | LLMConfig exposes retention_days=90 by default; reads from [retention] toml section; rejects values below 30 | VERIFIED | src/llm/config.py line 62: retention_days field, lines 97-133: extraction with minimum-30 enforcement |
| 3 | graphiti stale shows stale nodes (excludes pinned/archived, sorted by score ascending) | VERIFIED | src/cli/commands/stale.py wired to GraphService.list_stale(); all flags implemented; archive post-filter confirmed in service.py |
| 4 | graphiti compact --expire archives stale nodes end-to-end | VERIFIED | compact.py line 94 now calls list_stale(scope, project_root) — no show_all kwarg; archive_nodes wiring at line 107 correct; 15 integration tests pass |
| 5 | graphiti pin / graphiti unpin write to pin_state in retention.db | VERIFIED | src/cli/commands/pin.py wired to RetentionManager.pin_node/unpin_node(); commands registered in src/cli/__init__.py |
| 6 | MCP graphiti_stale tool returns TOON-encoded stale list | VERIFIED | tools.py lines 316-338: graphiti_stale follows _run_graphiti + _parse_json_or_raw pattern; exported in __all__ at line 478 |
| 7 | Retention tracks last_accessed_at and access_count; archived nodes invisible in list/search | VERIFIED | record_access() upserts access_log; get_archive_state_uuids() post-filters in list_entities() (lines 438-440), search() (lines 519-521), and get_entity() (lines 649-654) |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/retention/__init__.py` | Package init exporting RetentionManager, get_retention_manager, reset_retention_manager | VERIFIED | All three exports present |
| `src/retention/manager.py` | RetentionManager with full sidecar CRUD (min 130 lines) | VERIFIED | 245 lines; all methods including clear_archive(); WAL mode; compute_score() static method |
| `src/llm/config.py` | LLMConfig with retention_days field and load_config() extraction | VERIFIED | Field at line 62, extraction at lines 97-133 |
| `src/graph/service.py` | list_stale, archive_nodes, record_access methods; list_entities/search post-filter archived | VERIFIED | All methods present at lines 906, 988, 1014; post-filters at lines 438, 519; reactivation hook at lines 322-333 |
| `src/cli/commands/stale.py` | stale_command with all flags | VERIFIED | All flags: --global, --project, --all, --verbose, --format; 25-row cap with summary line |
| `src/cli/commands/compact.py` | compact_command with --expire branch | VERIFIED | --expire branch at lines 91-110; list_stale(scope, project_root) correct; archive_nodes wired at line 107 |
| `src/cli/commands/pin.py` | pin_command and unpin_command | VERIFIED | Both functions; uuid argument; scope options; wired to get_retention_manager() |
| `src/cli/__init__.py` | stale, pin, unpin commands registered | VERIFIED | Lines 63-64 imports; lines 81, 83, 105 registrations |
| `src/mcp_server/tools.py` | graphiti_stale MCP tool | VERIFIED | Lines 316-338; in __all__ at line 478 |
| `src/cli/commands/show.py` | show_command with _record_entity_access() hook | VERIFIED | _record_entity_access() helper at line 133; called at lines 88 and 130 |
| `tests/test_retention_integration.py` | Integration tests covering all 6 RETN requirements (min 60 lines) | VERIFIED | 314 lines; 15 tests covering RETN-01 through RETN-06; all 15 pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| src/retention/manager.py | ~/.graphiti/retention.db | sqlite3.connect with PRAGMA journal_mode=WAL | VERIFIED | Line 82: conn.execute("PRAGMA journal_mode=WAL") |
| src/llm/config.py | load_config() | config_data.get('retention', {}) | VERIFIED | Line 97: retention = config_data.get("retention", {}) |
| src/graph/service.py list_stale() | RetentionManager.get_archive_state_uuids() + get_pin_state_uuids() | from src.retention import get_retention_manager | VERIFIED | Lines 926, 935, 938 |
| src/graph/service.py archive_nodes() | RetentionManager.archive_node() | retention.archive_node(uuid, scope_key) | VERIFIED | Lines 1004, 1007 |
| src/graph/service.py list_entities() | RetentionManager.get_archive_state_uuids() | post-filter archived_uuids | VERIFIED | Lines 438-440 |
| src/graph/service.py search() | RetentionManager.get_archive_state_uuids() | post-filter archived_uuids | VERIFIED | Lines 519-521 |
| src/graph/service.py add() | RetentionManager.clear_archive() | detect post-episode entity UUID matches | VERIFIED | Lines 322-333 |
| src/cli/commands/stale.py | GraphService.list_stale() | run_graph_operation(get_service().list_stale(...)) | VERIFIED | Line 54: list_stale(scope, project_root) |
| src/cli/commands/compact.py | GraphService.list_stale() + archive_nodes() | run_graph_operation(get_service().list_stale(...)) | VERIFIED | Line 94: list_stale(scope, project_root) — show_all kwarg removed; archive_nodes at line 107 |
| src/cli/commands/pin.py pin_command | RetentionManager.pin_node() | get_retention_manager().pin_node(uuid, scope_key) | VERIFIED | Lines 31-32 |
| src/mcp_server/tools.py graphiti_stale | encode_response() from toon_utils | _parse_json_or_raw(stdout, "stale") | VERIFIED | Line 338 |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RETN-01 | 09-02, 09-03, 09-05 | User can run `graphiti compact --expire` to archive nodes older than retention_days | SATISFIED | compact --expire wired to list_stale() + archive_nodes(); fix confirmed; 15 integration tests pass |
| RETN-02 | 09-02, 09-03, 09-05 | User can run `graphiti stale` to preview stale nodes | SATISFIED | stale command functional end-to-end; 25-row cap; --all, --verbose, --format flags working |
| RETN-03 | 09-01, 09-05 | User can set [retention] retention_days in llm.toml | SATISFIED | LLMConfig.retention_days implemented; minimum 30 enforced; default 90 |
| RETN-04 | 09-04, 09-05 | User can run `graphiti pin <uuid>` to protect a node | SATISFIED | pin_command wired to RetentionManager.pin_node(); registered on CLI app |
| RETN-05 | 09-04, 09-05 | User can run `graphiti unpin <uuid>` to remove protection | SATISFIED | unpin_command wired to RetentionManager.unpin_node(); registered on CLI app |
| RETN-06 | 09-01, 09-02, 09-05 | Retention tracks last_accessed_at and access_count via SQLite sidecar | SATISFIED | record_access() in RetentionManager and GraphService; access_count increments on upsert |

### Anti-Patterns Found

None.

### Re-verification: Gap Resolution

| Gap | Previous Status | Fix Applied | Current Status |
|-----|----------------|-------------|----------------|
| compact.py called list_stale(scope, project_root, show_all=True) — invalid kwarg causing TypeError at runtime | FAILED | Removed show_all=True kwarg; commit fix(09-03) | VERIFIED |

### Gaps Summary

No gaps remain. The single blocker identified in initial verification — the stale `show_all=True` keyword argument in `compact.py` line 94 — has been removed. The call now correctly matches the `GraphService.list_stale(scope, project_root)` signature. All 15 integration tests pass and no regressions were introduced (272 tests pass total).

Phase 9 Smart Retention goal is fully achieved: automated TTL-based archiving is operational, the graph stays lean without manual cleanup, all six RETN requirements are satisfied.

---

_Initial verification: 2026-03-06T09:00:00Z_
_Re-verified: 2026-03-06T09:30:00Z_
_Verifier: Claude (gsd-verifier)_
