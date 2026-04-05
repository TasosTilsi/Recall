---
phase: 16
slug: rename-cli-consolidation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 16 — Validation Strategy

> Doc-only/config phase — compliant by definition per D-03. No automated tests required; compliance verified by VERIFICATION.md artifact.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_cli_rename.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_cli_rename.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| Plan 16-01 Task 1 | 16-01 | 1 | CLI-01 | doc/config | `pytest tests/test_cli_rename.py -x -q` | ✅ exists | ✅ green |
| Plan 16-02 Task 1 | 16-02 | 1 | CLI-03 | doc/config | `pytest tests/test_cli_rename.py -x -q` | ✅ exists | ✅ green |
| Plan 16-03 Task 1 | 16-03 | 1 | CLI-01, CLI-02 | doc/config | `pytest tests/test_cli_rename.py -x -q` | ✅ exists | ✅ green |
| Plan 16-04 Task 1 | 16-04 | 1 | CLI-02, CLI-03 | doc/config | `pytest tests/test_cli_rename.py -x -q` | ✅ exists | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — compliance verified by 16-VERIFICATION.md (status: passed, 3/3 truths verified).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `recall --help` shows 10 commands | CLI-02 | Visual inspection | `recall --help` output check — covered by 16-VERIFICATION.md |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — doc-only phase, compliance verified by 16-VERIFICATION.md (status: passed)
