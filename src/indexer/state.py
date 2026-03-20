"""JSON state management for SHA cursor, processed set, and cooldown tracking.

Manages the index-state.json file stored in .recall/ to track which commits
have been indexed, the last indexed SHA for incremental runs, and cooldown
timing to prevent excessive re-runs.
"""

import dataclasses
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_FILE_NAME = "index-state.json"


@dataclass
class IndexState:
    """State for the git history indexer.

    Tracks which commits have been processed, the last indexed SHA for
    incremental cursor-based iteration, and timing for cooldown enforcement.
    """

    version: str = "1.0"
    last_indexed_sha: str | None = None
    processed_shas: list[str] = field(default_factory=list)
    last_run_at: str | None = None
    indexed_commits_count: int = 0


def _state_file_path(project_root: Path) -> Path:
    """Return the absolute path to the state file."""
    return project_root / ".recall" / STATE_FILE_NAME


def load_state(project_root: Path) -> IndexState:
    """Load IndexState from .recall/index-state.json.

    Returns a fresh IndexState if the file does not exist or is malformed.

    Args:
        project_root: Root directory of the project (contains .recall/)

    Returns:
        IndexState populated from disk, or a fresh default instance
    """
    state_path = _state_file_path(project_root)
    if not state_path.exists():
        return IndexState()

    try:
        raw = state_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return IndexState(
            version=data.get("version", "1.0"),
            last_indexed_sha=data.get("last_indexed_sha"),
            processed_shas=data.get("processed_shas", []),
            last_run_at=data.get("last_run_at"),
            indexed_commits_count=data.get("indexed_commits_count", 0),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        # Malformed state file — return fresh state
        return IndexState()


def save_state(project_root: Path, state: IndexState) -> None:
    """Atomically write IndexState to .recall/index-state.json.

    Uses a temporary file and Path.replace() for atomicity so that
    a crash mid-write does not corrupt the state file.

    Args:
        project_root: Root directory of the project (contains .recall/)
        state: IndexState to persist
    """
    state_path = _state_file_path(project_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = state_path.with_suffix(".json.tmp")
    data = dataclasses.asdict(state)
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_path.replace(state_path)


def is_within_cooldown(project_root: Path, cooldown_minutes: int = 5) -> bool:
    """Check whether the last run was within the cooldown window.

    Args:
        project_root: Root directory of the project (contains .recall/)
        cooldown_minutes: Cooldown window in minutes (default 5)

    Returns:
        True if the last run was within cooldown_minutes ago, False otherwise
    """
    state = load_state(project_root)
    if state.last_run_at is None:
        return False

    try:
        last_run = datetime.fromisoformat(state.last_run_at)
        elapsed = datetime.now(timezone.utc) - last_run
        return elapsed < timedelta(minutes=cooldown_minutes)
    except (ValueError, TypeError):
        return False


def is_sha_processed(state: IndexState, sha: str) -> bool:
    """Check whether a commit SHA has already been processed.

    Compares against the stored short SHAs (first 8 characters).

    Args:
        state: Current IndexState
        sha: Full or short commit SHA

    Returns:
        True if the SHA (or its 8-char prefix) is in processed_shas
    """
    return sha[:8] in state.processed_shas


def add_processed_sha(state: IndexState, sha: str) -> None:
    """Record a commit SHA as processed.

    Stores only the first 8 characters of the SHA for compactness.
    Caps the list at 10,000 entries by trimming the oldest entries
    to prevent unbounded growth on large repositories.

    Args:
        state: IndexState to mutate
        sha: Full commit SHA to record
    """
    state.processed_shas.append(sha[:8])
    # Trim front if over capacity
    max_entries = 10_000
    if len(state.processed_shas) > max_entries:
        state.processed_shas = state.processed_shas[-max_entries:]


def clear_index_state(project_root: Path) -> None:
    """Delete the index state file, resetting all cursor and processed-SHA tracking.

    Used by --full flag to force a complete re-index from the beginning.

    Args:
        project_root: Root directory of the project (contains .recall/)
    """
    state_path = _state_file_path(project_root)
    state_path.unlink(missing_ok=True)
