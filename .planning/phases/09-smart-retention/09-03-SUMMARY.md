---
phase: 09-smart-retention
plan: "03"
subsystem: cli
tags: [cli, stale, compact, retention, archiving, typer]
dependency_graph:
  requires: [09-02]
  provides: [stale_command, compact_command_expire]
  affects: [src/cli/commands/stale.py, src/cli/commands/compact.py]
tech_stack:
  added: []
  patterns: [typer-command, rich-spinner, resolve_scope, confirm_action, run_graph_operation]
key_files:
  created:
    - src/cli/commands/stale.py
  modified:
    - src/cli/commands/compact.py
decisions:
  - "stale_command capped at 25 rows by default with summary line when more exist"
  - "compact --expire branch returns early before existing dedup logic — zero risk to dedup path"
metrics:
  duration: "2 min"
  tasks_completed: 2
  files_changed: 2
  completed_date: "2026-03-06"
---

# Phase 9 Plan 03: CLI stale and compact --expire commands Summary

One-liner: stale_command (rich table with Name/Age/Score, capped 25 rows) and compact --expire (count+confirm+archive flow) wired to GraphService.list_stale() and archive_nodes().

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create stale_command | 39b2ec2 | src/cli/commands/stale.py (created) |
| 2 | Extend compact_command with --expire | 75da315 | src/cli/commands/compact.py (modified) |

## stale_command Signature

```python
def stale_command(
    global_scope: Annotated[bool, typer.Option("--global", "-g", ...)] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", ...)] = False,
    all_results: Annotated[bool, typer.Option("--all", ...)] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", ...)] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", ...)] = None,
)
```

Behavior:
- Resolves scope via `resolve_scope(global_scope, project_scope)`
- Wraps `run_graph_operation(get_service().list_stale(...))` in Rich spinner
- Empty result: `print_success("No stale nodes found.")` then `typer.Exit(0)`
- Default cap: 25 rows; `--all` disables cap
- `--format json`: `print_json(display)`; else `print_table(display, columns=...)`
- `--verbose`: columns = `["uuid", "name", "age_days", "score"]`; default = `["name", "age_days", "score"]`
- Summary line when `not all_results and total > cap`: `"Showing 25 of N stale nodes. Run with --all to see all."`

## compact_command New Flag

Added `--expire` as first parameter:

```python
expire: Annotated[bool, typer.Option("--expire", help="Archive nodes older than retention_days (no dedup)")] = False,
```

The `--expire` branch runs BEFORE existing dedup logic:
1. Scan stale nodes with spinner
2. If none: `print_success("No stale nodes to archive.")` + exit
3. Print count of eligible nodes
4. `confirm_action(...)` (bypassed by `--force`)
5. `run_graph_operation(get_service().archive_nodes([n["uuid"] for n in stale], scope, project_root))`
6. `print_success(f"Archived {archived_count} nodes.")`; `return`

Existing dedup path remains intact.

## Deviations from Plan

None - plan executed exactly as written.

The plan's verification command used a 500-char window to find `archive_nodes` in the expire branch. The actual distance is ~700 chars (due to multiline confirmation call). Expanded window to 900 chars confirmed the branch is correctly isolated. No code deviation — only verification window too narrow.

## Self-Check: PASSED

- src/cli/commands/stale.py: FOUND
- src/cli/commands/compact.py: FOUND
- Commit 39b2ec2 (Task 1): FOUND
- Commit 75da315 (Task 2): FOUND
