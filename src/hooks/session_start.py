#!/usr/bin/env python3
"""SessionStart hook — generates session UUID and fires incremental git sync.

Runs when Claude Code opens a new session. Writes session UUID to
.recall/.current_session_id for use by other hooks, then spawns a
detached child process to run GitIndexer and returns immediately.

The child survives the hook process exiting (daemon=False) and runs
to completion on its own timetable. A lock file prevents concurrent
indexer spawns when multiple sessions open in quick succession.

Fail-open: any exception produces no stdout output and exits 0.
"""
import json
import multiprocessing
import os
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

# Lock file written in .recall/ for the duration of an active indexer child.
# Any subsequent session start that finds a live PID here skips spawning.
_INDEXER_LOCK_NAME = ".indexer_running"


def _write_session_id(project_root: Path) -> str:
    """Generate UUID v4 and write to .recall/.current_session_id. Overwrites if exists."""
    session_id = str(uuid.uuid4())
    session_file = project_root / ".recall" / ".current_session_id"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    session_file.write_text(session_id)
    logger.debug("session_id_written", session_id=session_id, path=str(session_file))
    return session_id


def _run_sync(project_root: Path) -> None:
    """Run incremental git index via GitIndexer.

    This function runs entirely inside a detached child process — the hook
    process has already returned to Claude Code before any meaningful work
    starts here.  Per-commit state files in .recall/ preserve partial
    progress across runs so killing or crashing mid-way is safe.

    A lock file records this child's PID for the duration of the run so that
    concurrent session starts can detect a live indexer and skip.
    """
    lock_file = project_root / ".recall" / _INDEXER_LOCK_NAME
    try:
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(str(os.getpid()))
        from src.indexer import GitIndexer
        GitIndexer(project_root=project_root).run(full=False)
    except Exception as e:
        print(f"[session_start] sync error: {e}", file=sys.stderr)
    finally:
        try:
            lock_file.unlink(missing_ok=True)
        except Exception:
            pass


def _indexer_already_running(project_root: Path) -> bool:
    """Return True if a previous session's indexer child is still alive."""
    lock_file = project_root / ".recall" / _INDEXER_LOCK_NAME
    if not lock_file.exists():
        return False
    try:
        pid = int(lock_file.read_text().strip())
        # kill(pid, 0) does not send a signal — it only checks if the process exists.
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        # Stale lock: process is dead or lock is corrupt — clean up and allow a new spawn.
        lock_file.unlink(missing_ok=True)
        return False


def _spawn_detached_sync(project_root: Path) -> None:
    """Spawn GitIndexer as a detached child and return immediately.

    daemon=False means the child is NOT killed when the hook process exits.
    The OS reaps the child when it finishes naturally.  The hook returns in
    <100 ms regardless of how long indexing takes.

    If a live indexer is already running (lock file + live PID), this is
    a no-op — the existing child will handle any new commits.
    """
    if _indexer_already_running(project_root):
        logger.debug("session_start_indexer_already_running")
        return

    proc = multiprocessing.Process(
        target=_run_sync,
        args=(project_root,),
        daemon=False,  # Must survive the hook process exiting
    )
    proc.start()
    # Deliberately no join() — return immediately and let the child run freely.


def main() -> None:
    """Main hook logic. Reads hook input from stdin. Writes nothing to stdout."""
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}

        # Determine project root from cwd field or fallback to process CWD
        cwd_str = hook_input.get("cwd", "")
        project_root = Path(cwd_str).resolve() if cwd_str else Path.cwd()

        # Write session UUID — happens in the hook process, always fast.
        _write_session_id(project_root)

        # Fire-and-forget: spawn indexer child and return immediately.
        # The child runs to completion on its own timetable.
        _spawn_detached_sync(project_root)

    except Exception:
        # Fail-open: log to stderr only, never crash Claude Code session
        logger.warning("session_start_hook_error", tb=traceback.format_exc())


if __name__ == "__main__":
    main()
