#!/usr/bin/env python3
"""SessionStart hook — generates session UUID and runs incremental git sync.

Runs when Claude Code opens a new session. Writes session UUID to
.graphiti/.current_session_id for use by other hooks. Calls GitIndexer
directly for incremental git sync (no subprocess — more robust in hook context).

Fail-open: any exception produces no stdout output and exits 0.
"""
import json
import sys
import traceback
import uuid
from pathlib import Path

# Fix sys.path for subprocess spawn (CWD undefined when Claude Code calls hooks)
_HOOK_DIR = Path(__file__).resolve().parent
_PROJECT_PKG_ROOT = _HOOK_DIR.parent.parent  # src/ -> project root
if str(_PROJECT_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_PKG_ROOT))

import structlog

logger = structlog.get_logger()


def _write_session_id(project_root: Path) -> str:
    """Generate UUID v4 and write to .graphiti/.current_session_id. Overwrites if exists."""
    session_id = str(uuid.uuid4())
    session_file = project_root / ".graphiti" / ".current_session_id"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id)
    logger.debug("session_id_written", session_id=session_id, path=str(session_file))
    return session_id


def _run_sync(project_root: Path) -> None:
    """Run incremental git index directly via GitIndexer. Partial progress preserved by state file."""
    try:
        # Fix sys.path for import (CWD undefined when Claude Code calls hooks)
        # _PROJECT_PKG_ROOT is already inserted at module load time above
        from src.indexer import GitIndexer
        GitIndexer(project_root=project_root).run(full=False)
    except Exception as e:
        logger.warning("session_start_sync_error", error=str(e))


def main() -> None:
    """Main hook logic. Reads hook input from stdin. Writes nothing to stdout."""
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}

        # Determine project root from cwd field or fallback to process CWD
        cwd_str = hook_input.get("cwd", "")
        project_root = Path(cwd_str).resolve() if cwd_str else Path.cwd()

        # Write session UUID (overwrite any previous session file)
        _write_session_id(project_root)

        # Run incremental git sync with hard timeout
        _run_sync(project_root)

    except Exception:
        # Fail-open: log to stderr only, never crash Claude Code session
        logger.warning("session_start_hook_error", tb=traceback.format_exc())


if __name__ == "__main__":
    main()
