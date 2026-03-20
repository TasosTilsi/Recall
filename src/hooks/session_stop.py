#!/usr/bin/env python3
"""Stop/PreCompact hook — processes pending captures and generates session summary.

Runs at session end (Stop hook) or before context compaction (PreCompact hook).
Reads pending_tool_captures.jsonl, enqueues capture_tool_use jobs for background
processing, then generates a session summary episode via LLM.

Timeout budgets:
  Stop: 30s total
  PreCompact (--mode precompact): 30s total (same script, same budget)

Fail-open: any exception exits 0 with no stdout output.
"""
import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Optional

# Fix sys.path for subprocess spawn
_HOOK_DIR = Path(__file__).resolve().parent
_PROJECT_PKG_ROOT = _HOOK_DIR.parent.parent
if str(_PROJECT_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_PKG_ROOT))

import structlog

logger = structlog.get_logger()

PENDING_CAPTURES_FILENAME = ".recall/pending_tool_captures.jsonl"
SESSION_SUMMARY_PROMPT = """\
Summarize this development session in 2-3 sentences. Focus on:
- What was built or changed (specific files, features, fixes)
- Key decisions made and why
- What to continue next session

Session tool activity:
{content}

Summary (2-3 sentences):"""


def _read_session_id(project_root: Path) -> Optional[str]:
    session_file = project_root / ".recall" / ".current_session_id"
    if session_file.exists():
        return session_file.read_text().strip() or None
    return None


def _drain_pending_captures(project_root: Path) -> list[dict]:
    """Read and clear pending_tool_captures.jsonl. Returns parsed entries."""
    pending_file = project_root / PENDING_CAPTURES_FILENAME
    if not pending_file.exists():
        return []

    entries = []
    try:
        lines = pending_file.read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("invalid_capture_entry", line=line[:100])

        # Clear the file after reading (truncate, don't delete)
        pending_file.write_text("", encoding="utf-8")
    except Exception as e:
        logger.warning("drain_pending_captures_error", error=str(e))

    return entries


def _enqueue_captures(entries: list[dict], project_root: Path, session_id: Optional[str]) -> None:
    """Enqueue each capture entry as a capture_tool_use job for BackgroundWorker."""
    if not entries:
        return

    try:
        from src.queue.storage import JobQueue
        queue = JobQueue()

        for entry in entries:
            queue.enqueue(
                job_type="capture_tool_use",
                payload={
                    "content": f"Tool: {entry.get('tool_name','')}\nArgs: {entry.get('key_args','')}\nOutput: {entry.get('output_snippet','')}",
                    "session_id": session_id or "",
                    "cwd": entry.get("cwd", str(project_root)),
                    "timestamp": entry.get("timestamp", ""),
                },
                parallel=True,
            )

        logger.info("captures_enqueued", count=len(entries), session_id=str(session_id)[:8] if session_id else "none")
    except Exception as e:
        logger.warning("enqueue_captures_error", error=str(e))


def _generate_session_summary(
    entries: list[dict],
    project_root: Path,
    session_id: Optional[str],
) -> None:
    """Generate and store a session_summary episode via LLM summarization.

    Uses src.llm.chat() which is SYNCHRONOUS (not a coroutine).
    chat() accepts messages: list[dict] and returns a response dict.
    Access text via response["message"]["content"].
    """
    if not entries:
        logger.debug("no_entries_for_summary")
        return

    try:
        # Import path verified: src/llm/__init__.py exports both names
        from src.llm import chat, LLMUnavailableError
        from src.graph.service import get_service
        from src.models import GraphScope
        from src.security import sanitize_content

        # Build content from entries (truncate to avoid LLM context limits)
        content_lines = []
        for e in entries[:30]:  # cap at 30 most recent entries
            line = f"- {e.get('tool_name','')}: {e.get('key_args','')}"
            content_lines.append(line)

        content_str = "\n".join(content_lines)
        # sanitize_content returns SanitizationResult; access .sanitized_content for the string
        sanitized_content = sanitize_content(content_str).sanitized_content

        prompt_text = SESSION_SUMMARY_PROMPT.format(content=sanitized_content[:3000])

        # LLM call for session summary (up to 30s budget — Stop hook).
        # chat() is synchronous — call directly, NOT via asyncio.run().
        # Pass as messages list per the chat() signature.
        try:
            response = chat([{"role": "user", "content": prompt_text}])
            summary_text = response["message"]["content"]
        except LLMUnavailableError:
            logger.warning("llm_unavailable_for_session_summary")
            return

        if not summary_text or not summary_text.strip():
            return

        # Store as session_summary episode in graph
        import asyncio
        service = get_service()
        asyncio.run(service.add(
            content=sanitize_content(summary_text.strip()).sanitized_content,
            scope=GraphScope.PROJECT,
            project_root=project_root,
            tags=([session_id] if session_id else []),
            source="session_summary",
        ))
        logger.info("session_summary_stored", session_id=str(session_id)[:8] if session_id else "none")

    except Exception as e:
        logger.warning("session_summary_error", error=str(e), tb=traceback.format_exc())


def main() -> None:
    """Main hook logic. Reads from stdin. Writes nothing to stdout."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--mode", default="stop", choices=["stop", "precompact"])
    args, _ = parser.parse_known_args()

    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}

        cwd_str = hook_input.get("cwd", "")
        project_root = Path(cwd_str).resolve() if cwd_str else Path.cwd()
        session_id = _read_session_id(project_root)

        # Step 1: Drain pending captures from jsonl file
        entries = _drain_pending_captures(project_root)

        # Step 2: Enqueue captures for BackgroundWorker (async processing)
        _enqueue_captures(entries, project_root, session_id)

        # Step 3: Generate session summary (both Stop and PreCompact modes)
        _generate_session_summary(entries, project_root, session_id)

    except Exception:
        logger.warning("session_stop_hook_error",
                       tb=traceback.format_exc())


if __name__ == "__main__":
    main()
