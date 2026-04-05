---
phase: 20
slug: fast-indexing-claude-cli-batch-fts
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_claude_cli_client.py tests/test_indexer_batch.py tests/test_hooks_phase20.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_claude_cli_client.py tests/test_indexer_batch.py tests/test_hooks_phase20.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| Plan 20-01 Task 1 | 20-01 | 1 | PERF-02 (ClaudeCliLLMClient) | unit | `pytest tests/test_claude_cli_client.py -x -q` | ✅ exists | ✅ green |
| Plan 20-02 Task 1 | 20-02 | 1 | PERF-01 (batch extraction + semaphore) | unit | `pytest tests/test_indexer_batch.py -x -q` | ✅ exists | ✅ green |
| Plan 20-03 Task 1 | 20-03 | 2 | PERF-05 (FTS-first inject_context) | unit | `pytest tests/test_hooks_phase20.py -x -q` | ✅ exists | ✅ green |
| Plan 20-04 Task 1 | 20-04 | 2 | PERF-03 (session_stop claude CLI) | unit | `pytest tests/test_hooks_phase20.py -x -q` | ✅ exists | ✅ green |
| Plan 20-05 Task 1 | 20-05 | 3 | PERF-01/02/03/04/05 (full test suite) | integration | `pytest tests/test_claude_cli_client.py tests/test_indexer_batch.py tests/test_hooks_phase20.py -x -q` | ✅ exists | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — all referenced tests exist. Verified 2026-04-04: 24 tests pass (8 + 6 + 9 + 1 skipped).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 30-commit indexing under 2 minutes | PERF-01 | Requires real git repo + Claude CLI | Covered by 20-VERIFICATION.md timing proof |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — all tests exist and pass per 20-VERIFICATION.md (status: passed, 5/5 verified)
