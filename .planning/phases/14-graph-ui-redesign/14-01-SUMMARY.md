---
phase: 14-graph-ui-redesign
plan: 01
subsystem: config,cli,hooks,security,indexer
tags: [rename, migration, paths, ui-port]
dependency_graph:
  requires: []
  provides: [".recall-paths", "migrate_dot_graphiti_to_recall", "LLMConfig.ui_port-single-field"]
  affects: [all-cli-commands, all-hooks, security-module, indexer-module]
tech_stack:
  added: []
  patterns: ["auto-migration on startup", "backward-compat TOML key aliasing"]
key_files:
  created: []
  modified:
    - src/config/paths.py
    - src/cli/__init__.py
    - src/llm/config.py
    - src/cli/commands/ui.py
    - src/cli/commands/config.py
    - src/cli/commands/init_cmd.py
    - src/cli/commands/note_cmd.py
    - src/retention/manager.py
    - src/gitops/config.py
    - src/gitops/hooks.py
    - src/capture/conversation.py
    - src/capture/git_capture.py
    - src/capture/git_worker.py
    - src/security/allowlist.py
    - src/security/sanitizer.py
    - src/security/audit.py
    - src/models/context.py
    - src/indexer/state.py
    - src/indexer/indexer.py
    - src/hooks/session_start.py
    - src/hooks/session_stop.py
    - src/hooks/inject_context.py
    - src/hooks/capture_entry.py
    - src/storage/graph_manager.py
    - src/llm/provider.py
    - src/llm/queue.py
    - src/llm/__init__.py
    - src/queue/storage.py
    - src/queue/__init__.py
    - src/mcp_server/context.py
    - src/gitops/__init__.py
    - .gitignore
    - tests/test_ui_server.py
    - tests/test_llm_config.py
    - tests/test_security.py
    - tests/test_hooks_phase15.py
decisions:
  - "migrate_dot_graphiti_to_recall() called at CLI startup in main_callback (before load_config); safe no-op on repeat runs"
  - "LLMConfig.ui_api_port removed; single ui_port=8765 replaces split fields; backward compat reads api_port->port in TOML"
  - "load_config() imports CONFIG_PATH from src.config.paths for default path (avoids duplication)"
  - "get_state_path() returns CONFIG_PATH.parent / llm_state.json to avoid hardcoded ~/.recall"
metrics:
  duration_minutes: 9
  tasks_completed: 2
  files_modified: 36
  completed_date: "2026-03-20"
---

# Phase 14 Plan 01: Directory Rename .graphiti -> .recall Summary

Renamed the `.graphiti/` dot directory to `.recall/` across all ~30 Python source files, added auto-migration function in `paths.py`, and simplified `LLMConfig` to a single `ui_port=8765` field removing the split `ui_api_port`/`ui_port` design.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update paths.py with .recall constants and auto-migration | ceba040 | src/config/paths.py, src/cli/__init__.py |
| 2 | Replace .graphiti with .recall in all source files + LLMConfig ui_port cleanup | d8f131b, e44c135 | 34 files |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Additional source files not in plan's file list had .graphiti references**
- **Found during:** Task 2 verification grep
- **Issue:** Plan listed 20 files but 10+ additional files had .graphiti string literals or path constructions: `src/storage/graph_manager.py`, `src/llm/provider.py`, `src/llm/queue.py`, `src/llm/__init__.py`, `src/queue/storage.py`, `src/queue/__init__.py`, `src/mcp_server/context.py`, `src/gitops/__init__.py`, `src/indexer/indexer.py`
- **Fix:** Updated all to use .recall paths (functional code: graph_manager.py version stamp, queue defaults; docstrings/comments in others)
- **Files modified:** 9 additional files beyond plan
- **Commits:** d8f131b

**2. [Rule 1 - Bug] Tests referencing old .graphiti paths failed**
- **Found during:** Post-task test run
- **Issue:** test_ui_server.py, test_llm_config.py, test_security.py, test_hooks_phase15.py all had hardcoded `.graphiti` path assertions that broke after rename
- **Fix:** Updated all test assertions to use .recall; updated TestLLMConfigUI to reflect single ui_port field; added backward-compat test for api_port alias
- **Files modified:** 4 test files
- **Commit:** e44c135

**3. [Rule 1 - Bug] .gitignore was missing .recall/ entry**
- **Found during:** Task 2 — git stash/pop created an untracked .recall/ directory
- **Fix:** Added `.recall/` to .gitignore alongside `.graphiti/`
- **Files modified:** .gitignore
- **Commit:** d8f131b

## Verification Results

1. `grep -rn '".graphiti"' src/ --include="*.py"` — only 2 hits, both in `paths.py` migration function (the source OLD path, intentional)
2. `python3 -c "from src.config.paths import GLOBAL_DB_PATH; print(GLOBAL_DB_PATH)"` — `/home/user/.recall/global/graphiti.lbdb`
3. `python3 -c "from src.llm.config import LLMConfig; c = LLMConfig(); assert c.ui_port == 8765; assert not hasattr(c, 'ui_api_port')"` — passes
4. `python3 -m pytest tests/ -q` — 286 passed, 1 skipped (excluding pre-existing `real_ladybug` import failures)

## Self-Check: PASSED

- SUMMARY.md exists at .planning/phases/14-graph-ui-redesign/14-01-SUMMARY.md
- Commit ceba040 (Task 1) exists
- Commit d8f131b (Task 2) exists
- Commit e44c135 (test fixes) exists
