---
phase: 15-local-memory-system
plan: "02"
subsystem: session-hooks-read-path
tags: [hooks, session-start, inject-context, option-c, phase15]
dependency_graph:
  requires: [graphiti-sync-command, install_global_hooks]
  provides: [session_start.py, inject_context.py]
  affects: [src/hooks/session_start.py, src/hooks/inject_context.py]
tech_stack:
  added: []
  patterns: [fail-open-hooks, option-c-xml, token-budget-truncation, uuid-session-identity]
key_files:
  created:
    - src/hooks/session_start.py
    - src/hooks/inject_context.py
  modified: []
decisions:
  - "session_start.py uses sys.executable to locate graphiti CLI (same venv as interpreter)"
  - "inject_context.py imports get_service() lazily after sys.path fix — avoids import error on subprocess spawn"
  - "asyncio.run() used directly inside try/except in each fetch helper — safe for standalone subprocess with no running event loop"
  - "Token budget uses len(text)//4 approximation — no tiktoken dependency, conservative for English"
  - "Continuity block always rendered (empty tags when no summary) — XML structure consistent"
metrics:
  duration_seconds: 600
  completed_date: "2026-03-19"
  tasks_completed: 2
  files_changed: 2
---

# Phase 15 Plan 02: session_start and inject_context hooks Summary

Created the two read-path Claude Code hook scripts providing session UUID persistence and Option C XML context injection (BM25+semantic search, 4000-token budget, fail-open).

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create session_start.py SessionStart hook | 44f372e | src/hooks/session_start.py |
| 2 | Create inject_context.py UserPromptSubmit hook | 44f372e | src/hooks/inject_context.py |

## What Was Built

### Task 1: session_start.py

`src/hooks/session_start.py` — SessionStart hook that:
- Reads `{"session_id": ..., "cwd": ...}` JSON from stdin (fails open on empty/malformed)
- Generates UUID v4 and writes to `{project_root}/.graphiti/.current_session_id` (creates dir if missing)
- Calls `graphiti sync` subprocess via `_GRAPHITI_CLI` (same venv as interpreter) with 4.5s `subprocess.TimeoutExpired` guard
- Handles `FileNotFoundError` (graphiti binary not found) gracefully
- Writes NOTHING to stdout — all logging via structlog to stderr
- Main `except Exception` catch-all ensures exit 0 on any failure (fail-open)

### Task 2: inject_context.py

`src/hooks/inject_context.py` — UserPromptSubmit hook that:
- Reads `{"session_id": ..., "prompt": ..., "cwd": ...}` JSON from stdin
- Returns `{"context": ""}` immediately when prompt is empty (fast path)
- Reads session UUID from `.graphiti/.current_session_id` for session-boost ranking
- Calls `service.search(query="session summary", ...)` to fetch continuity (most recent session_summary episode)
- Calls `service.search(query=prompt, ...)` for relevant history (SEARCH_LIMIT=20 results)
- Ranks results by (session_boost, recency) descending
- Builds Option C XML: `<session_context><continuity>...</continuity><relevant_history>...</relevant_history></session_context>`
- Truncates oldest history lines when over 4000-token budget (len(text)//4 approximation)
- Returns `{"context": ""}` on any exception (fail-open via outer except block)
- `print()` is the only stdout channel — structlog goes to stderr

## Verification Results

- `session_start syntax OK` — `ast.parse()` passes with python3
- `inject_context syntax OK` — `ast.parse()` passes with python3
- No `print(` at top-level indent in session_start.py — confirmed by code review
- `import structlog` present in both files
- `def main`, `_write_session_id`, `_run_sync` all present in session_start.py
- `_build_option_c`, `_fetch_continuity`, `_fetch_relevant_history` all present in inject_context.py

## Deviations from Plan

None — plan executed exactly as written. Scripts match the inline code specification from the plan verbatim with only minor formatting adaptations (em-dashes replaced with `->` for ASCII safety, `<=` instead of Unicode).

## Self-Check: PASSED

Files verified to exist:
- src/hooks/session_start.py — FOUND
- src/hooks/inject_context.py — FOUND
