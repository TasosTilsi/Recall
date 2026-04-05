---
phase: 15
slug: local-memory-system
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` / `pyproject.toml [tool.pytest]` |
| **Quick run command** | `pytest tests/test_hooks_phase15.py tests/test_global_hooks_installer.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_hooks_phase15.py tests/test_global_hooks_installer.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| sync-cmd | 15-01 | 0 | MEM-04 | CLI smoke | `recall sync --help` exits 0 | `src/cli/commands/sync.py` | ✅ green |
| global-install | 15-01 | 0 | MEM-05 | Unit | `pytest tests/test_global_hooks_installer.py -x -q` | ✅ exists | ✅ green |
| session-start | 15-02 | 1 | MEM-01, MEM-04 | Integration | `pytest tests/test_hooks_phase15.py -k session_start -x -q` | ✅ exists | ✅ green |
| inject-context | 15-02 | 1 | MEM-01, MEM-03 | Integration | `pytest tests/test_hooks_phase15.py -k inject_context -x -q` | ✅ exists | ✅ green |
| capture-entry | 15-03 | 2 | MEM-01, MEM-02 | Integration | `pytest tests/test_hooks_phase15.py -k capture_entry -x -q` | ✅ exists | ✅ green |
| session-stop | 15-03 | 2 | MEM-01 | Integration | `pytest tests/test_hooks_phase15.py -k session_stop -x -q` | ✅ exists | ✅ green |
| wiring | 15-04 | 3 | MEM-05 | CLI smoke | `recall hooks install --dry-run` exits 0 | ✅ exists | ✅ green |
| e2e | 15-05 | 4 | MEM-01–05 | E2E manual | Human verifies context appears in new Claude session | — | ✅ green |

*Note: All Phase 15 hook tests are in `tests/test_hooks_phase15.py` (flat file, 16 tests). Installer tests are in `tests/test_global_hooks_installer.py`.*

---

## Timeout Budget Tests (MEM-01)

Each hook must fire within its budget. Verify with timing wrappers:

| Hook | Budget | Test Method |
|------|--------|-------------|
| SessionStart | ≤5s | `time python src/hooks/session_start.py` in a test repo |
| UserPromptSubmit | ≤6s | `time python src/hooks/inject_context.py '{...}'` |
| PostToolUse | fire-and-forget | Verify returns in <200ms; background processing verified via jsonl file |
| PreCompact | ≤30s | `time python src/hooks/session_stop.py` (same script, different trigger) |

---

## Requirements Coverage

| Requirement | Description | Covered By |
|-------------|-------------|------------|
| MEM-01 | All hooks fire within timeout budgets | `test_hooks_phase15.py` timeout tests |
| MEM-02 | PostToolUse captures tool calls via async queue | `test_hooks_phase15.py` capture entry tests + jsonl file check |
| MEM-03 | UserPromptSubmit injects Option C format | `test_hooks_phase15.py` inject context output format check |
| MEM-04 | SessionStart triggers graphiti sync | `test_hooks_phase15.py` session start tests + `recall sync` command exists |
| MEM-05 | Hooks installed via `recall hooks install` (global) | `test_global_hooks_installer.py` + `~/.claude/settings.json` check |

---

## Wave 0 Requirements

- [x] `tests/test_hooks_phase15.py` — all Phase 15 hook tests (session_start, inject_context, capture_entry, session_stop) — 16 tests pass
- [x] `tests/test_global_hooks_installer.py` — installer tests (global hooks install to ~/.claude/settings.json) — passes

*Wave 0 stubs were never created as a subdirectory; all coverage consolidated into flat test files above.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Context appears in new session | MEM-03 | Requires live Claude Code session | Start new Claude Code session; verify `<session_context>` block injected at first prompt |
| Git sync populates graph | MEM-04 | Requires live git repo + Ollama | Run `recall sync` in a git repo; verify new episodes added via `recall search` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — all tests exist and pass (16 + installer tests pass)
