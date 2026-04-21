---
phase: 32-claude-plugin-skills
plan: "01"
subsystem: cli
tags: [install, mcp, plugin-manifest, cli]
dependency_graph:
  requires: []
  provides: [claude-plugin.json, recall-install-command]
  affects: [src/cli/__init__.py]
tech_stack:
  added: []
  patterns: [typer-command, structlog, idempotent-json-merge]
key_files:
  created:
    - claude-plugin.json
    - src/cli/commands/install_cmd.py
    - tests/test_install_cmd.py
  modified:
    - src/cli/__init__.py
decisions:
  - "install_mcp_global uses idempotent read/merge/write pattern — same approach as src/hooks/installer.py"
  - "ensure_recall_dir returns bool (True=created, False=already existed) to drive console output"
  - "install command never writes config.toml — that is the recall-setup skill's responsibility"
metrics:
  duration_seconds: 113
  completed: "2026-04-21T20:18:02Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 32 Plan 01: Claude Plugin Manifest and Install Command Summary

Claude plugin manifest (`claude-plugin.json`) and `recall install` CLI command that registers the MCP server in `~/.claude/settings.json` idempotently and creates `~/.recall/` if missing.

## What Was Built

- **`claude-plugin.json`** at repo root — static JSON manifest declaring the MCP server entry and two skills (`recall-setup`, `recall-index`)
- **`src/cli/commands/install_cmd.py`** — two helpers (`install_mcp_global`, `ensure_recall_dir`) and a typer command wired into the CLI
- **`src/cli/__init__.py`** updated — `install` registered as the 7th command (setup-time, distinct from the six operational commands)
- **`tests/test_install_cmd.py`** — 6 unit tests covering all TDD behaviors

## Tasks

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Create claude-plugin.json manifest | Done | 6d7ab8e |
| 2 | Implement recall install command (TDD) | Done | 0c41ac7 (RED), 575b9f2 (GREEN) |

## Verification Results

1. `python3 -c "import json; d=json.load(open('claude-plugin.json')); assert 'mcpServers' in d; print('manifest OK')"` — PASSED
2. `python -m pytest tests/test_install_cmd.py -x -q` — 6/6 PASSED
3. `recall install --help` — shows help text without error

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all behaviors are fully implemented and tested.

## Self-Check: PASSED

- `claude-plugin.json` exists and is valid JSON with mcpServers + 2 skills
- `src/cli/commands/install_cmd.py` exists with `install_mcp_global`, `ensure_recall_dir`, `install_command`
- `tests/test_install_cmd.py` exists with 6 passing tests
- Commits 6d7ab8e, 0c41ac7, 575b9f2 present in git log
