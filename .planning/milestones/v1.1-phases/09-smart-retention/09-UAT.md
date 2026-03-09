---
status: complete
phase: 09-smart-retention
source: 09-01-SUMMARY.md, 09-02-SUMMARY.md, 09-03-SUMMARY.md, 09-04-SUMMARY.md, 09-05-SUMMARY.md
started: 2026-03-09T08:43:59Z
updated: 2026-03-09T08:52:00Z
---

## Current Test

[testing complete]

## Tests

### 1. graphiti stale — no stale nodes
expected: Run `graphiti stale`. Should display "No stale nodes found." and exit cleanly.
result: pass

### 2. graphiti stale — table output (Name/Age/Score columns)
expected: Run `graphiti stale` with stale nodes present. Rich table with Name, Age (days), Score columns, sorted most-stale first. At most 25 rows; summary line if more.
result: pass
note: Verified via verify_phase_09.py — 2 backdated test entities visible in stale output with age_days ≥99

### 3. graphiti stale --verbose (UUID column)
expected: Run `graphiti stale --verbose`. Table includes UUID column alongside Name, Age (days), Score.
result: pass
note: uuid, age_days, score columns all confirmed present in --verbose output

### 4. graphiti pin <uuid> — hides node from stale
expected: Pin a UUID, then run `graphiti stale`. Pinned node absent from results. UUID recorded in retention.db pin_state.
result: pass

### 5. graphiti unpin <uuid> — restores node to stale
expected: Unpin a previously pinned UUID. Node reappears in `graphiti stale`. UUID removed from pin_state in retention.db.
result: pass

### 6. graphiti show — records access in retention.db
expected: After running `graphiti show <entity>`, an access_log entry is written to retention.db with access_count ≥ 1.
result: pass

### 7. graphiti compact --expire — archives stale nodes with confirmation
expected: Shows count of eligible nodes, prompts for confirmation, archives on confirm. archive_state written to retention.db. "Archived N nodes." message shown.
result: pass

### 8. retention_days config — default and minimum enforcement
expected: LLMConfig default retention_days = 90. Setting retention_days < 30 in llm.toml falls back to 30.
result: pass

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
