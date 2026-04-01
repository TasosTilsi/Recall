---
phase: 20-fast-indexing-claude-cli-batch-fts
plan: "04"
subsystem: hooks
tags: [session-stop, claude-cli, llm, performance]
dependency_graph:
  requires: ["20-01"]
  provides: ["PERF-04"]
  affects: ["src/hooks/session_stop.py"]
tech_stack:
  added: []
  patterns: ["lazy-import fallback", "claude-cli-preference", "asyncio.run subprocess"]
key_files:
  created: []
  modified:
    - src/hooks/session_stop.py
decisions:
  - "Lazy import of claude_cli_client inside _generate_session_summary — avoids import errors on edge cases where module may not exist"
  - "asyncio.run(_claude_p(prompt_text)) is safe in _generate_session_summary because main() is synchronous with no outer event loop"
  - "summary_text = None sentinel pattern enables clean fallback without nested try/except"
metrics:
  duration: 4
  completed: "2026-04-01"
  tasks_completed: 1
  files_modified: 1
---

# Phase 20 Plan 04: Wire Claude CLI to session_stop Summary

**One-liner:** Session summary generation now prefers `claude -p` (~5s) over Ollama (~45s) with transparent lazy-import fallback.

## What Was Built

Modified `_generate_session_summary` in `src/hooks/session_stop.py` to try the claude CLI before the existing Ollama path.

The change:
1. After building `prompt_text`, initializes `summary_text = None`
2. Lazily imports `claude_cli_available` and `_claude_p` from `src.llm.claude_cli_client`
3. If `claude_cli_available()` returns True, calls `asyncio.run(_claude_p(prompt_text))` for ~5s summary
4. Any exception in the claude path is caught and logged at DEBUG level, leaving `summary_text = None`
5. If `summary_text is None`, runs original Ollama path inside ThreadPoolExecutor with FutureTimeoutError and LLMUnavailableError handling

The existing guard (`if not summary_text or not summary_text.strip(): return`) and the graph store call (`asyncio.run(service.add(...))`) remain entirely unchanged.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add claude CLI path to _generate_session_summary | f50290e | src/hooks/session_stop.py |

## Verification Results

```
all checks OK
import OK
```

- `claude_cli_available` present in `_generate_session_summary` source
- `_claude_p` call present
- `ThreadPoolExecutor` Ollama fallback preserved
- `summary_text = None` initialization pattern present
- `from src.hooks.session_stop import main, _generate_session_summary` exits 0

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - the claude CLI path is fully wired and the Ollama fallback is complete.

## Self-Check: PASSED

- `src/hooks/session_stop.py` — FOUND
- Commit f50290e — FOUND
