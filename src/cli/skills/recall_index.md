---
name: recall-index
description: >
  Index the current project's git history into the recall knowledge graph.
  Runs recall sync (or recall init if no DB exists), then reports commits
  processed and entity type breakdown.
trigger: /recall-index
---

# /recall-index — Index Git History into recall

You are indexing the user's git history into the recall knowledge graph.
Work through each step automatically. Show progress; ask for confirmation only if an error occurs.

## Step 1: Check whether a recall DB exists

Run this in your Bash tool:
```bash
recall health 2>&1 | head -5
```

- If `recall health` exits 0 (DB reachable) → proceed to Step 2 with `recall sync`
- If `recall health` exits non-zero or prints "no database" / "not initialized" → proceed to Step 2 with `recall init`

## Step 2: Run indexing

**If no DB exists** — run initial indexing:
```bash
recall init 2>&1
```

**If DB exists** — run incremental sync:
```bash
recall sync 2>&1
```

Capture the full output. Do not truncate it.

## Step 3: Parse and report results

From the command output, extract:
1. **Commits processed** — look for a line matching `commits processed`, `episodes added`, or similar. If not found, state "commit count not reported by recall".
2. **Entity type breakdown** — look for lines listing entity types and counts, e.g.:
   ```
   Decision: 12
   Pattern: 8
   Concept: 5
   Bug: 2
   ```
   If the output does not include a breakdown, run:
   ```bash
   recall list --format json 2>/dev/null | python3 -c "
   import sys, json, collections
   data = json.load(sys.stdin)
   counts = collections.Counter(e.get('entity_type', 'Unknown') for e in data)
   for k, v in sorted(counts.items()): print(f'{k}: {v}')
   " 2>&1
   ```
   Use the output of this fallback as the entity breakdown.

## Step 4: Report to user

Present a summary in this format:

```
recall index complete.

Commits processed: <N>

Entity type breakdown:
  Decision  : <N>
  Pattern   : <N>
  Concept   : <N>
  <type>    : <N>
  ...

Total entities in graph: <sum>
```

If the operation failed, show the error output in full and suggest:
- Check `recall health` for connectivity issues
- Confirm Ollama is running (`ollama list`)
- Re-run `/recall-setup` if config may be missing

## Important

- Do NOT hallucinate counts — only report what the CLI output actually contains
- If `recall init` or `recall sync` takes more than 30 seconds, inform the user it is still running (large repos are normal)
- After a successful index, remind the user: "recall will now inject relevant context automatically at the start of each Claude session."
