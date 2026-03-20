"""Conversation capture from Claude Code transcripts.

Reads Claude Code JSONL transcript files, tracks last_captured_turn per session
to avoid re-processing, extracts text from turns, and summarizes via LLM.

Supports both auto mode (incremental, from Stop hook) and manual mode (full
transcript, from CLI).

Key features:
- JSONL transcript parsing with error handling
- Per-session turn tracking via metadata file
- Atomic metadata file writes (write-to-temp, rename)
- Graceful fallback on missing transcripts
- Integration with summarize_and_store pipeline

Usage:
    # Auto mode (from Stop hook)
    entity = await capture_conversation(
        transcript_path=Path("~/.claude/transcript.jsonl"),
        session_id="abc123",
        auto=True
    )

    # Manual mode (from CLI)
    entity = await capture_manual(transcript_path=Path("path/to/transcript.jsonl"))
"""

import json
import os
from pathlib import Path
from typing import Optional

import structlog

from src.capture.summarizer import summarize_and_store
from src.llm.config import load_config
from src.models import GraphScope

logger = structlog.get_logger()

# Metadata file stores last_captured_turn per session_id
METADATA_FILE = Path.home() / ".recall" / "capture_metadata.json"


def _load_metadata() -> dict:
    """Load capture metadata from METADATA_FILE.

    Returns empty dict if file doesn't exist or is malformed.
    Metadata structure: {"session_id": last_captured_turn_index, ...}

    Returns:
        Metadata dict mapping session_id to last turn index
    """
    if not METADATA_FILE.exists():
        return {}

    try:
        content = METADATA_FILE.read_text()
        metadata = json.loads(content)
        return metadata if isinstance(metadata, dict) else {}
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("failed_to_load_metadata", path=str(METADATA_FILE), error=str(e))
        return {}


def _save_metadata(metadata: dict) -> None:
    """Save metadata to METADATA_FILE atomically.

    Uses atomic write pattern: write to .tmp, rename to final.
    Ensures parent directory exists.

    Args:
        metadata: Metadata dict to save
    """
    # Ensure parent directory exists
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp file, rename
    temp_file = METADATA_FILE.with_suffix('.tmp')
    try:
        temp_file.write_text(json.dumps(metadata, indent=2))
        temp_file.rename(METADATA_FILE)
    except Exception as e:
        logger.error("failed_to_save_metadata", path=str(METADATA_FILE), error=str(e))
        # Clean up temp file on error
        temp_file.unlink(missing_ok=True)
        raise


def _get_last_captured_turn(session_id: str) -> int:
    """Get the last captured turn index for a session.

    Returns 0 if session not tracked (first capture for this session).

    Args:
        session_id: Session identifier

    Returns:
        Last captured turn index (0 if new session)
    """
    metadata = _load_metadata()
    return metadata.get(session_id, 0)


def _set_last_captured_turn(session_id: str, turn_index: int) -> None:
    """Update the last captured turn for a session.

    Args:
        session_id: Session identifier
        turn_index: Turn index to record
    """
    metadata = _load_metadata()
    metadata[session_id] = turn_index
    _save_metadata(metadata)


def read_transcript(transcript_path: Path, since_turn: int = 0) -> list[dict]:
    """Read Claude Code JSONL transcript file.

    Each line is a JSON object representing a conversation turn.
    Parses lines, skips turns with index <= since_turn.

    Handles errors gracefully:
    - FileNotFoundError: Log warning, return empty list
    - Malformed JSON lines: Skip with warning, continue parsing

    Args:
        transcript_path: Path to JSONL transcript file
        since_turn: Only include turns with index > since_turn. Default: 0 (all turns)

    Returns:
        List of turn dicts (each with at least 'index' key)

    Example:
        >>> turns = read_transcript(Path("~/.claude/transcript.jsonl"), since_turn=5)
        >>> # Returns only turns 6, 7, 8, ... (skips 0-5)
    """
    if not transcript_path.exists():
        logger.warning("transcript_file_not_found", path=str(transcript_path))
        return []

    turns = []
    try:
        with transcript_path.open('r') as f:
            for line_num, line in enumerate(f, start=1):
                if not line.strip():
                    continue

                try:
                    turn = json.loads(line)

                    # Extract turn index (may be in different fields)
                    turn_index = turn.get('index', turn.get('turn', line_num - 1))

                    # Skip if at or before since_turn
                    if turn_index <= since_turn:
                        continue

                    # Ensure index field exists for downstream processing
                    if 'index' not in turn:
                        turn['index'] = turn_index

                    turns.append(turn)

                except json.JSONDecodeError as e:
                    logger.warning(
                        "malformed_json_line_skipped",
                        path=str(transcript_path),
                        line_num=line_num,
                        error=str(e)
                    )
                    continue

    except Exception as e:
        logger.error("failed_to_read_transcript", path=str(transcript_path), error=str(e))
        return []

    logger.debug(
        "transcript_read_complete",
        path=str(transcript_path),
        turn_count=len(turns),
        since_turn=since_turn
    )

    return turns


def extract_conversation_text(turns: list[dict]) -> str:
    """Extract meaningful text content from transcript turns.

    For each turn, extracts the "content" or "message" field and joins
    turns into a single text block with turn separators.

    This is the raw text that gets sent to summarization.

    Args:
        turns: List of turn dicts from read_transcript()

    Returns:
        Joined text with turn separators

    Example:
        >>> turns = [
        ...     {"index": 1, "content": "Hello"},
        ...     {"index": 2, "message": "Hi there"}
        ... ]
        >>> text = extract_conversation_text(turns)
        >>> print(text)
        ---
        Turn 1:
        Hello
        ---
        Turn 2:
        Hi there
    """
    text_parts = []

    for turn in turns:
        turn_index = turn.get('index', '?')

        # Extract content from turn (try multiple field names)
        content = turn.get('content') or turn.get('message') or turn.get('text', '')

        if not content:
            continue

        # Add turn separator and content
        text_parts.append(f"---\nTurn {turn_index}:\n{content}")

    return "\n".join(text_parts)


async def capture_conversation(
    transcript_path: Path,
    session_id: str,
    auto: bool = False,
    scope: GraphScope = GraphScope.GLOBAL,
    project_root: Path | None = None,
) -> dict | None:
    """Main conversation capture function.

    Reads Claude Code transcript and summarizes via LLM. Two modes:

    **Auto mode (auto=True)**: Incremental capture from Stop hook
    - Checks last_captured_turn for this session_id
    - Only processes new turns since last capture
    - Updates metadata after successful capture
    - Returns None if no new turns

    **Manual mode (auto=False)**: Full capture from CLI
    - Reads ALL turns (ignores metadata)
    - Does not update metadata tracking
    - Processes entire transcript

    Args:
        transcript_path: Path to Claude Code JSONL transcript
        session_id: Session identifier (used for metadata tracking)
        auto: Auto mode (incremental) vs manual mode (full). Default: False
        scope: GraphScope for storage. Default: GLOBAL
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Stored entity dict from graph, or None if no content to capture

    Example:
        >>> # Auto mode from Stop hook
        >>> entity = await capture_conversation(
        ...     transcript_path=Path("~/.claude/transcript.jsonl"),
        ...     session_id="abc123",
        ...     auto=True
        ... )

        >>> # Manual mode from CLI
        >>> entity = await capture_conversation(
        ...     transcript_path=Path("path/to/transcript.jsonl"),
        ...     session_id="manual",
        ...     auto=False
        ... )
    """
    # Determine starting point based on mode
    if auto:
        last_turn = _get_last_captured_turn(session_id)
        logger.info(
            "auto_capture_conversation_start",
            session_id=session_id,
            last_turn=last_turn
        )
    else:
        last_turn = 0
        logger.info(
            "manual_capture_conversation_start",
            session_id=session_id
        )

    # Read transcript from last position
    turns = read_transcript(transcript_path, since_turn=last_turn)

    if not turns:
        logger.debug(
            "no_new_turns_to_capture",
            session_id=session_id,
            last_turn=last_turn
        )
        return None

    # Extract text from turns
    conversation_text = extract_conversation_text(turns)

    if not conversation_text.strip():
        logger.debug(
            "no_content_extracted_from_turns",
            session_id=session_id,
            turn_count=len(turns)
        )
        return None

    # Build tags for entity
    tags = ["auto-capture", "conversation", session_id[:8]]

    # Summarize and store
    logger.info(
        "summarizing_conversation",
        session_id=session_id,
        turn_count=len(turns),
        content_length=len(conversation_text)
    )

    cfg = load_config()

    entity = await summarize_and_store(
        content_items=[conversation_text],
        source="conversation",
        scope=scope,
        project_root=project_root,
        tags=tags,
        capture_mode=cfg.capture_mode,
    )

    # Update metadata if auto mode and capture succeeded
    if auto and entity:
        # Get highest turn index from captured turns
        max_turn = max(turn.get('index', 0) for turn in turns)
        _set_last_captured_turn(session_id, max_turn)
        logger.info(
            "conversation_capture_complete",
            session_id=session_id,
            turns_captured=len(turns),
            new_last_turn=max_turn
        )

    return entity


async def capture_manual(transcript_path: Path | None = None) -> dict | None:
    """Manual capture entry point for `graphiti capture` CLI.

    If transcript_path not provided, attempts to find it from Claude Code
    environment:
    1. Check CLAUDE_TRANSCRIPT_PATH env var
    2. Check common locations (~/.claude/transcript.jsonl)

    Calls capture_conversation() with auto=False (full transcript processing).

    Args:
        transcript_path: Optional path to transcript. None = auto-detect

    Returns:
        Stored entity dict from graph, or None if no transcript found

    Raises:
        ValueError: If no transcript path provided and auto-detect fails

    Example:
        >>> # Explicit path
        >>> entity = await capture_manual(Path("path/to/transcript.jsonl"))

        >>> # Auto-detect from environment
        >>> entity = await capture_manual()
    """
    # Auto-detect transcript path if not provided
    if transcript_path is None:
        # Check environment variable
        env_path = os.environ.get('CLAUDE_TRANSCRIPT_PATH')
        if env_path:
            transcript_path = Path(env_path).expanduser()
        else:
            # Try common location
            common_path = Path.home() / ".claude" / "transcript.jsonl"
            if common_path.exists():
                transcript_path = common_path
            else:
                raise ValueError(
                    "No transcript path provided and could not auto-detect. "
                    "Provide transcript_path argument or set CLAUDE_TRANSCRIPT_PATH env var."
                )

    logger.info("manual_capture_start", path=str(transcript_path))

    # Use "manual" as session_id for manual captures
    return await capture_conversation(
        transcript_path=transcript_path,
        session_id="manual",
        auto=False,
    )
