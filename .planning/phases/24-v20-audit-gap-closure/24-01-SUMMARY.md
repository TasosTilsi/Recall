---
phase: 24-v20-audit-gap-closure
plan: "01"
subsystem: testing
tags: [verify-scripts, binary-rename, stale-refs, docstrings]

requires:
  - phase: 16-rename-cli-consolidation
    provides: "recall/rc entrypoints replacing graphiti/gk; binary renamed to recall"

provides:
  - "verify_phase_10/11/12/13.py updated to use RECALL constant and run_recall() function"
  - "src/mcp_server/install.py line 13 comment corrected to recall/SKILL.md"
  - "src/hooks/manager.py all docstring/comment graphiti product-name refs replaced with recall"

affects: [23-nyquist-compliance-sweep, 24-v20-audit-gap-closure]

tech-stack:
  added: []
  patterns:
    - "verify script pattern: RECALL = str(ROOT / '.venv' / 'bin' / 'recall'); run_recall() wraps subprocess"

key-files:
  created: []
  modified:
    - scripts/verify_phase_10.py
    - scripts/verify_phase_11.py
    - scripts/verify_phase_12.py
    - scripts/verify_phase_13.py
    - src/mcp_server/install.py
    - src/hooks/manager.py

key-decisions:
  - "verify_phase_11.py RETENTION_DB path corrected from .graphiti to .recall (Rule 1 auto-fix)"

patterns-established:
  - "Verify script binary constant: RECALL not GRAPHITI; run_recall() not run_graphiti()"

requirements-completed: []

duration: 8min
completed: 2026-04-05
---

# Phase 24 Plan 01: Fix Stale Binary References in Verify Scripts and Source Files Summary

**GRAPHITI→RECALL constant and run_graphiti()→run_recall() renamed in 4 verify scripts; install.py comment and manager.py docstrings corrected to use recall product name**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-05T21:40:00Z
- **Completed:** 2026-04-05T21:48:00Z
- **Tasks:** 6 (all tasks in a single atomic commit — verify scripts + source files)
- **Files modified:** 6

## Accomplishments

- Fixed GRAPHITI/run_graphiti binary refs in verify_phase_10/11/12/13.py — scripts now reference `recall` CLI instead of the removed `graphiti` binary
- Fixed install.py line 13 comment: `~/.claude/skills/graphiti/SKILL.md` → `~/.claude/skills/recall/SKILL.md`
- Fixed all 8 docstring/comment "graphiti" product-name occurrences in src/hooks/manager.py → "recall"
- All 435 pytest tests pass, 1 skipped, 0 failures — no regressions

## Task Commits

All 6 tasks committed atomically:

1. **Tasks 1-6: All verify script and source file fixes** - `910e333` (fix)

## Files Created/Modified

- `scripts/verify_phase_10.py` - GRAPHITI→RECALL, run_graphiti→run_recall, check_prerequisites, banner strings
- `scripts/verify_phase_11.py` - Same pattern; also fixed stale RETENTION_DB path (.graphiti→.recall)
- `scripts/verify_phase_12.py` - Same pattern; all CLI banner strings updated (health, add, search, list)
- `scripts/verify_phase_13.py` - Same pattern; health command references updated
- `src/mcp_server/install.py` - Line 13 comment corrected; runtime path already used recall
- `src/hooks/manager.py` - 8 docstring/comment product-name occurrences replaced

## Decisions Made

None - followed plan as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale RETENTION_DB path in verify_phase_11.py**
- **Found during:** Task 2 (verify_phase_11.py review)
- **Issue:** `RETENTION_DB = Path.home() / ".graphiti" / "retention.db"` — actual path is `~/.recall/retention.db` per RetentionManager source (Phase 16 rename)
- **Fix:** Changed to `Path.home() / ".recall" / "retention.db"`
- **Files modified:** scripts/verify_phase_11.py
- **Verification:** Matches `src/retention/manager.py` line 50
- **Committed in:** 910e333

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug: stale data path)
**Impact on plan:** Minimal — single line fix for correctness, no scope creep.

## Issues Encountered

None — all fixes were mechanical renames. No logic changes required.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 24-02 (Graph.tsx DetailPanel wiring + VERIFICATION.md updates) can proceed immediately
- All verify script binary references are now correct for `recall` CLI
- Acceptance criteria verified: `grep "bin/graphiti|run_graphiti" scripts/verify_phase_1{0,1,2,3}.py` returns empty

## Self-Check: PASSED

- `scripts/verify_phase_10.py` — FOUND (verified no graphiti refs)
- `scripts/verify_phase_11.py` — FOUND (verified no graphiti refs, RETENTION_DB fixed)
- `scripts/verify_phase_12.py` — FOUND (verified no graphiti refs)
- `scripts/verify_phase_13.py` — FOUND (graphiti_core library import refs remain — correct)
- `src/mcp_server/install.py` — FOUND (line 13 references recall/SKILL.md)
- `src/hooks/manager.py` — FOUND (0 graphiti occurrences)
- Commit 910e333 — FOUND

---
*Phase: 24-v20-audit-gap-closure*
*Completed: 2026-04-05*
