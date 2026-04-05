---
phase: 21
slug: knowledge-quality-uplift
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python) + npx tsx (TypeScript) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `pytest tests/test_extraction_phase21.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q && cd ui && npx tsx src/lib/parseCodeBlockMeta.test.ts` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_extraction_phase21.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q && cd ui && npx tsx src/lib/parseCodeBlockMeta.test.ts`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| Plan 21-01 Task 1 | 21-01 | 1 | SC-1/SC-2/SC-3/SC-4 (extraction prompt + code blocks) | unit | `pytest tests/test_extraction_phase21.py -x -q` | ✅ exists | ✅ green |
| Plan 21-02 Task 1 | 21-02 | 2 | SC-5 (UI entity cards) | unit | `cd ui && npx tsx src/lib/parseCodeBlockMeta.test.ts` | ✅ exists | ✅ green |
| Plan 21-03 Task 1 | 21-03 | 3 | SC-1/SC-2/SC-3/SC-4/SC-5 (full test suite) | integration | `pytest tests/test_extraction_phase21.py -x -q` | ✅ exists | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — all referenced tests exist. Verified 2026-04-04: 10 Python tests pass, 8 TypeScript tests pass.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Entity cards display structured context in UI | SC-5 | Visual inspection | Covered by 21-VERIFICATION.md human-verify checkpoint |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — all tests exist and pass per 21-VERIFICATION.md (status: passed, 5/5 verified)
