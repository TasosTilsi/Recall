---
phase: 30-mcp-server
plan: 30-02
subsystem: cli_mcp
tags: [typer, mcp, cli, smoke-test, stdio]

# Dependency graph
requires:
  - phase: 30-mcp-server/30-01
    provides: src/mcp_server/server.py, src/mcp_server/__init__.py exposing serve()
  - phase: 29-cli-commands
    provides: CLI surface and src/cli/__init__.py Typer app
provides:
  - src/cli/commands/mcp.py — Typer command group with serve() subcommand
  - `recall mcp serve` public CLI entry point
  - tests/test_mcp_server.py — 3 passing smoke tests (stdout, tool count, signatures)
affects: [INST-01, INST-02, SKILL-01, SKILL-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deferred import of serve() inside command body — avoids FastMCP logging side effects at CLI startup"
    - "app.add_typer(mcp_commands.app, name='mcp') for command group registration"
    - "io.StringIO + unittest.mock.patch('sys.stdout') for stdout contamination testing"

key-files:
  created:
    - src/cli/commands/mcp.py
    - tests/test_mcp_server.py
  modified:
    - src/cli/__init__.py

key-decisions:
  - "serve() import deferred inside command body to prevent FastMCP logging.basicConfig side effects at CLI startup time"
  - "mcp group not listed in the six public commands — utility group accessible but not primary surface"

# Metrics
duration: 8min
completed: 2026-04-21
---

# Phase 30 Plan 02: MCP CLI Wiring Summary

**Typer `mcp` command group wired to `recall mcp serve`, bridging CLI to FastMCP stdio server, with 3 smoke tests verifying stdout cleanliness, tool count, and parameter signatures**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-21T09:12:00Z
- **Completed:** 2026-04-21T09:20:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created src/cli/commands/mcp.py with `app = typer.Typer()` and `serve()` command that defers import of `src.mcp_server.serve`
- Registered `mcp_commands.app` in src/cli/__init__.py via `app.add_typer(mcp_commands.app, name="mcp")`
- `recall mcp serve --help` shows description without error; `recall mcp --help` shows the group
- Wrote 3 smoke tests in tests/test_mcp_server.py — all pass without a live database
- MCP protocol smoke verified: initialize message returns valid JSON-RPC result frame

## Task Commits

1. **Task 1: Wire recall mcp serve CLI command group** - `54fd0d8` (feat)
2. **Task 2: Add MCP server smoke tests** - `061901f` (test)

## Files Created/Modified

- `src/cli/commands/mcp.py` — Typer app with `serve()` command; deferred serve() import
- `src/cli/__init__.py` — Added mcp_commands import and app.add_typer(mcp_commands.app, name="mcp")
- `tests/test_mcp_server.py` — 3 smoke tests: stdout clean, 6 tools registered, parameter signatures

## Decisions Made

- serve() import deferred inside command body — prevents `logging.basicConfig(stream=sys.stderr)` from FastMCP running at `recall --help` time
- mcp group added after the six public commands — does not appear prominently in main help but is accessible

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all wiring is functional.

## Self-Check: PASSED

- `src/cli/commands/mcp.py` — FOUND
- `src/cli/__init__.py` — modified with mcp registration — FOUND
- `tests/test_mcp_server.py` — FOUND
- Commit 54fd0d8 — FOUND
- Commit 061901f — FOUND
- All 3 tests pass
- `recall mcp serve --help` works
- MCP protocol smoke: OK
