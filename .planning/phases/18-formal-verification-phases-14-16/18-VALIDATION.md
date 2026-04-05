---
phase: 18
slug: formal-verification-phases-14-16
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 18 — Validation Strategy

> Formal verification phase — compliant by definition per D-03. Deliverable was VERIFICATION.md artifact creation, not production code.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + scripts/verify_phase_14.py |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `python3 scripts/verify_phase_14.py --skip-live` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 scripts/verify_phase_14.py --skip-live`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| Plan 18-01 Task 1 | 18-01 | 1 | UI-01, UI-02, UI-04 | verification script | `python3 scripts/verify_phase_14.py --skip-live` | ✅ exists | ✅ green |
| Plan 18-02 Task 1 | 18-02 | 1 | CLI-01, CLI-02, CLI-03 | verification script | `python3 scripts/verify_phase_16.py --skip-live` | ✅ exists | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — compliance verified by 18-VERIFICATION.md (status: passed).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|

*No manual-only verifications — all automated via verification scripts or doc-verified via 18-VERIFICATION.md.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — formal verification phase, compliance verified by 18-VERIFICATION.md (status: passed)
