---
status: partial
phase: 19-wire-ui-03-retention-filter
source: [19-01-SUMMARY.md, 19-02-SUMMARY.md, 19-03-SUMMARY.md]
started: 2026-03-28T01:29:00Z
updated: 2026-03-28T16:30:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

number: 2
name: Entities tab — retention filter Combobox
expected: |
  In the Entities toolbar, locate an "All statuses" dropdown next to the "All types" dropdown.
  Click it — 4 options appear: Pinned, Normal, Stale, Archived.
  Select "Archived" — archived entities appear in the table.
  Select "Pinned" additionally (multi-select) — both Pinned and Archived entities are visible.
  Deselect all — returns to default view (all except archived). Entity count updates correctly.
awaiting: user response

## Tests

### 1. Entities tab — default view
expected: Run `recall ui` and open http://localhost:8765. Navigate to the Entities tab. The entity table loads with Name, Type, Status, and Scope columns. Status badges show dynamic colors (green for Normal, amber for Pinned, red for Stale, gray for Archived) — NOT all hardcoded "Normal". Archived entities are NOT visible in the default view.
result: blocked
blocked_by: other
reason: "I can't see anything in ui, and the indexer for sure is active right now — LadybugDB WAL UNREACHABLE_CODE on all DB reads while indexer holds the database"

### 2. Entities tab — retention filter Combobox
expected: In the Entities toolbar, locate an "All statuses" dropdown next to the "All types" dropdown. Click it — 4 options appear: Pinned, Normal, Stale, Archived. Select "Archived" — archived entities appear in the table. Select "Pinned" additionally (multi-select) — both Pinned and Archived entities are visible. Deselect all — returns to default view (all except archived). Entity count updates correctly as filters change.
result: [pending]

### 3. Graph tab — node border rings
expected: Navigate to the Graph tab. Entity nodes render with colored border rings based on retention status: Pinned nodes have an amber ring (#fbbf24), Stale nodes have a red ring (#f87171), Archived nodes have a gray ring (#94a3b8), Normal nodes have no visible ring. The entity-type fill colors are preserved (rings are a second visual signal on top of fill color).
result: [pending]

### 4. Graph tab — retention legend
expected: On the Graph tab, a "Retention" legend section appears (stacked below or alongside the entity-type legend). It shows 4 entries — Pinned, Stale, Archived, Normal — each with a hollow circle ring swatch in the corresponding color.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 1

## Gaps

[none yet]
