#!/usr/bin/env python3
"""SessionStart hook — generates session UUID and runs incremental git sync.

Runs when Claude Code opens a new session. Writes session UUID to
.graphiti/.current_session_id for use by other hooks. Calls graphiti sync
with a 4.5s hard timeout (leaves 0.5s buffer in 5s SessionStart budget).

Fail-open: any exception produces no stdout output and exits 0.
"""
import json
import subprocess
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

# Use graphiti binary from same venv as running Python interpreter
_GRAPHITI_CLI = str(Path(sys.executable).parent / "graphiti")

SYNC_TIMEOUT_SECONDS = 4.5


def _write_session_id(project_root: Path) -> str:
    """Generate UUID v4 and write to .graphiti/.current_session_id. Overwrites if exists."""
    session_id = str(uuid.uuid4())
    session_file = project_root / ".graphiti" / ".current_session_id"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id)
    logger.debug("session_id_written", session_id=session_id, path=str(session_file))
    return session_id


def _run_sync(project_root: Path) -> None:
    """Call graphiti sync with 4.5s hard timeout. Partial progress preserved by GitIndexer state."""
    try:
        result = subprocess.run(
            [_GRAPHITI_CLI, "sync"],
            cwd=str(project_root),
            timeout=SYNC_TIMEOUT_SECONDS,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning(
                "sync_nonzero_exit",
                returncode=result.returncode,
                stderr=result.stderr[:200],
            )
    except subprocess.TimeoutExpired:
        # Partial progress is preserved by GitIndexer .last_sync_hash state file
        logger.warning("sync_timeout_expired", timeout_s=SYNC_TIMEOUT_SECONDS)
    except FileNotFoundError:
        logger.warning("graphiti_cli_not_found", path=_GRAPHITI_CLI)


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
