#!/bin/sh
# === Recall Capture Hook ===
# Auto-installed by recall - captures commit hashes for background processing
# To remove: recall hooks uninstall

# RECALL_HOOK_START
# Append current commit hash to pending file
# Tries multiple ways to locate recall: venv, PATH, direct location
COMMIT_HASH=$(git rev-parse HEAD)
PENDING_FILE="${HOME}/.recall/pending_commits"

# Ensure directory exists
mkdir -p "$(dirname "$PENDING_FILE")"

# Atomic append (O_APPEND semantics for small writes)
echo "$COMMIT_HASH" >> "$PENDING_FILE"
# RECALL_HOOK_END

exit 0
