---
phase: 17
slug: fix-stale-binary-references
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 17 — Validation Strategy

> Gap-closure phase — compliant by definition per D-03. No automated tests required; compliance verified by VERIFICATION.md artifact.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_backend_config.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_backend_config.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| Plan 17-01 Task 1 | 17-01 | 1 | MEM-02 | doc/config | `pytest tests/test_backend_config.py -x -q` | ✅ exists | ✅ green |
| Plan 17-02 Task 1 | 17-02 | 1 | MEM-03 | doc/config | `pytest tests/test_backend_config.py -x -q` | ✅ exists | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — compliance verified by 17-VERIFICATION.md (status: passed, 6/6 truths verified).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*No manual-only verifications — all automated or doc-verified via 17-VERIFICATION.md.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — gap-closure phase, compliance verified by 17-VERIFICATION.md (status: passed)
