#!/bin/sh
# Recall Knowledge Graph - Pre-commit validation hook
# Scans staged files for secrets and checks repository size

# RECALL_HOOK_START
# Skip if RECALL_SKIP is set
[ "$RECALL_SKIP" = "1" ] && exit 0

# Locate recall binary; derive venv python from same directory
RECALL_BIN=$(command -v recall 2>/dev/null)
[ -z "$RECALL_BIN" ] && exit 0
VENV_PYTHON="$(dirname "$RECALL_BIN")/python"
[ ! -x "$VENV_PYTHON" ] && exit 0

# Check if hooks are enabled (use --get flag; exit 0 if key missing or false)
"$RECALL_BIN" config --get hooks.enabled 2>/dev/null | grep -q "true" || exit 0

# Scan staged files for secrets (blocks commit if secrets found)
"$VENV_PYTHON" -c "
from pathlib import Path
from src.gitops.hooks import scan_staged_secrets
import sys
result = scan_staged_secrets(Path('.'))
if result:
    sys.exit(1)
sys.exit(0)
" 2>&1
SECRETS_EXIT=$?
[ "$SECRETS_EXIT" -ne 0 ] && exit "$SECRETS_EXIT"

# Check repository size (warns but does not block)
"$VENV_PYTHON" -c "
from pathlib import Path
from src.gitops.hooks import check_recall_size
check_recall_size(Path('.'))
" 2>&1

exit 0
# RECALL_HOOK_END
