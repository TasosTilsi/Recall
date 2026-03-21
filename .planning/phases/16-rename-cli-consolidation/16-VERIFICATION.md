---
phase: 16-rename-cli-consolidation
verified: 2026-03-21T00:00:00Z
status: passed
score: 3/3 must-haves verified
human_verification: []
---

# Phase 16: Rename & CLI Consolidation Verification Report

**Phase Goal:** Users interact with the tool as `recall` (alias `rc`) through a clean 10-command public surface — internal plumbing is hidden, the entrypoint communicates what the tool actually does (local developer memory), and every command is maintainable without ripple effects across 18 entrypoints.
**Verified:** 2026-03-21T00:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `recall --help` shows exactly 10 commands: init, search, list, delete, pin, unpin, health, config, ui, note — no plumbing commands | VERIFIED | verify_phase_16.py Tests 3–5 PASS: all 10 public commands registered in __init__.py, removed commands absent from imports; Tests 14–15 PASS (live): recall --help output confirmed with 10 commands, no removed commands visible |
| 2 | `recall search` auto-syncs git history before returning results | VERIFIED | verify_phase_16.py Test 9 PASS: _auto_sync() defined and called in search.py; test_cli_rename.py::test_auto_sync_called_before_search PASS; test_auto_sync_fails_silently PASS; test_auto_sync_skips_when_no_project_root PASS |
| 3 | recall/rc entrypoints work; graphiti/gk removed; all internal references updated | VERIFIED | verify_phase_16.py Tests 1–2 PASS: pyproject.toml has recall/rc only, graphiti/gk absent; Tests 10–12 PASS: all 11 removed command files deleted, session_start.py uses GitIndexer directly, manager.py uses _RECALL_CLI; Tests 13–15 PASS (live): recall --help exits 0 and shows 'recall' |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Provides | Status | Evidence |
|----------|----------|--------|---------|
| `src/cli/__init__.py` | Typer app name "recall", 10 public commands + hidden index | VERIFIED | app.info.name == "recall"; all 10 commands registered; index hidden=True — Tests 2–4 PASS |
| `pyproject.toml` | recall/rc scripts section; graphiti/gk absent | VERIFIED | `recall = "src.cli:cli_entry"` and `rc = "src.cli:cli_entry"` present; graphiti/gk absent — Test 1 PASS |
| `src/cli/commands/note_cmd.py` | Manual memory add (replaces `add`); writes to .recall/pending_tool_captures.jsonl | VERIFIED | File exists; pending_tool_captures.jsonl reference present — Test 6 PASS; test_note_command_appends_to_jsonl PASS |
| `src/cli/commands/init_cmd.py` | hooks + git index + config, no interactive prompts | VERIFIED | File exists; no typer.prompt() or input() calls — Test 7 PASS |
| `src/cli/commands/list_cmd.py` | --stale, --compact, --queue flags | VERIFIED | All 3 flags present in source — Test 8 PASS; tests for --stale, --compact, --queue all PASS |
| `src/cli/commands/search.py` | _auto_sync() + search_command integration | VERIFIED | _auto_sync defined and called — Test 9 PASS; test_auto_sync_called_before_search PASS |
| `src/hooks/session_start.py` | Calls GitIndexer directly (no recall binary subprocess) | VERIFIED | GitIndexer in source; no _GRAPHITI_CLI subprocess — Test 11 PASS |
| `src/hooks/manager.py` | Uses _RECALL_CLI | VERIFIED | _RECALL_CLI present; _GRAPHITI_CLI absent — Test 12 PASS |
| `scripts/verify_phase_16.py` | 16 automated checks for CLI-01/02/03 | VERIFIED | Script exists; 14/14 static+sub-checks pass with --skip-live; 17/17 pass with live binary |
| `tests/test_cli_rename.py` | 16 pytest tests via Typer CliRunner | VERIFIED | 16/16 tests pass (including fix for test_note_command_appends_to_jsonl path) |

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `pyproject.toml` | `src.cli:cli_entry` | `recall = "src.cli:cli_entry"` and `rc = "src.cli:cli_entry"` | WIRED | Both entrypoints point to same cli_entry function — Test 1 PASS |
| `src/cli/__init__.py` | 10 public commands | `app.command(name="...")` / `app.add_typer(...)` | WIRED | All 10 commands registered by name — Test 3 PASS |
| `src/cli/__init__.py` | `src/cli/commands/index.py` | `app.command(name="index", hidden=True)` | WIRED | index registered with hidden=True — Test 4 PASS |
| `search.py` | `GitIndexer` (via _auto_sync) | `_auto_sync() -> GitIndexer(project_root).run(full=False)` | WIRED | _auto_sync defined and called in search_command — Test 9 PASS |
| `session_start.py` | `GitIndexer` directly | `GitIndexer(project_root=root).run(full=False)` | WIRED | Direct Python call; no binary subprocess — Test 11 PASS |
| `manager.py` | `_RECALL_CLI` constant | Used in subprocess calls instead of _GRAPHITI_CLI | WIRED | _RECALL_CLI present; _GRAPHITI_CLI absent — Test 12 PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| CLI-01 | 16-01, 16-03 | recall + rc entrypoints; graphiti/gk removed; all internal references updated | SATISFIED | pyproject.toml verified (Test 1 PASS); app name "recall" (Test 2 PASS); removed command files deleted (Test 10 PASS); session_start.py uses GitIndexer directly (Test 11 PASS); manager.py uses _RECALL_CLI (Test 12 PASS); live: recall --help exits 0 (Test 13 PASS); pytest 16/16 PASS |
| CLI-02 | 16-01, 16-02 | recall --help shows exactly 10 commands; plumbing hidden | SATISFIED | All 10 public commands registered (Test 3 PASS); index hidden=True (Test 4 PASS); no removed imports (Test 5 PASS); note_cmd/init_cmd/list flags present (Tests 6–8 PASS); live: 10 commands listed (Test 14 PASS), removed commands hidden (Test 15 PASS); pytest 16/16 PASS |
| CLI-03 | 16-02 | recall search auto-syncs git before results | SATISFIED | _auto_sync() defined and called in search.py (Test 9 PASS); test_auto_sync_called_before_search PASS; test_auto_sync_fails_silently PASS; test_auto_sync_skips_when_no_project_root PASS |

All 3 requirements satisfied. No orphaned requirements found for Phase 16.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO/FIXME/placeholder comments, no stub returns, no empty handlers found in any Phase 16 artifact.

### Human Verification

Phase 16 requires **NO human verification** — all checks are automated via `scripts/verify_phase_16.py` and `tests/test_cli_rename.py`. No visual or interactive flows exist in Phase 16 (CLI-only changes with no UI).

### Test Suite Results

- **verify_phase_16.py static (--skip-live):** 14 assertions, 0 failures (`python3 scripts/verify_phase_16.py --skip-live`)
  - 12 named check functions pass; Test 10 has 2 sub-checks (removed files deleted + index.py kept)
  - Output: "All required tests passed. Requirements CLI-01 · CLI-02 · CLI-03 verified."
- **verify_phase_16.py live (with recall binary):** 17 assertions, 0 failures — Tests 13–15 PASS; Test 16 SKIP (auto-sync not documented in --help text, which is acceptable)
- **test_cli_rename.py:** 16/16 passed (`pytest tests/test_cli_rename.py -v`)
  - Note: test_note_command_appends_to_jsonl fixed from `.graphiti/` to `.recall/` path (aligns with note_cmd.py, capture_entry.py, and session_stop.py which all use `.recall/pending_tool_captures.jsonl`)
- **Full suite:** 386 passed, 2 pre-existing failures unrelated to Phase 16 (test_storage.py::TestGraphManagerProject — LadybugDB path issue), 1 skipped (`pytest tests/ -q`)

### Summary

Phase 16 goal is fully achieved. The `recall`/`rc` entrypoints replace `graphiti`/`gk`; `recall --help` exposes exactly 10 public commands (init, search, list, delete, pin, unpin, health, config, ui, note) with all plumbing commands deleted from the codebase. The `recall search` command auto-syncs git history via `_auto_sync()` before returning results, and `session_start.py` calls GitIndexer directly in Python rather than via a subprocess — eliminating binary name dependency in hook scripts.

All verification is automated — no human smoke test is required. The verify_phase_16.py script provides 16 checks covering the entire CLI-01/02/03 requirement surface, and tests/test_cli_rename.py provides 16 Typer CliRunner tests that verify CLI behavior without a live binary. Requirements CLI-01, CLI-02, and CLI-03 are all fully satisfied.

---
_Verified: 2026-03-21T00:00:00Z_
_Verifier: Claude (gsd-executor)_
