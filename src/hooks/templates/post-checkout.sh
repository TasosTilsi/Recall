#!/bin/sh
# RECALL_HOOK_START
# Recall: trigger background index on branch switch to keep knowledge graph current
# $3 = 0 means file checkout (not branch switch) — skip
[ "$RECALL_SKIP" = "1" ] && exit 0
command -v recall >/dev/null 2>&1 || exit 0

# Only trigger on branch switches ($3=1), not file checkouts ($3=0)
[ "$3" = "0" ] && exit 0

recall config get hooks.enabled 2>/dev/null | grep -q "true" || exit 0

# Background index — never block the checkout operation
(recall index >/dev/null 2>&1) &

exit 0
# RECALL_HOOK_END
