#!/bin/sh
# RECALL_HOOK_START
# Recall: trigger background index after merge to keep knowledge graph current
[ "$RECALL_SKIP" = "1" ] && exit 0
command -v recall >/dev/null 2>&1 || exit 0
recall config get hooks.enabled 2>/dev/null | grep -q "true" || exit 0

# Background index — never block the merge operation
(recall index >/dev/null 2>&1) &

exit 0
# RECALL_HOOK_END
