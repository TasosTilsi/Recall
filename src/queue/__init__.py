"""Background job queue package.

This package provides a persistent, SQLite-backed job queue for async processing
of CLI commands. Jobs can be queued during Claude Code hooks (silent mode) or
interactively (with feedback), then processed by background workers in the MCP server.

Key features:
- SQLite persistence: Jobs survive process restarts
- FIFO ordering: Oldest jobs processed first
- Parallel batching: Consecutive parallel jobs run concurrently
- Sequential barriers: Non-parallel jobs processed alone
- Dead letter queue: Failed jobs preserved for inspection
- Hook context detection: Auto-silent mode for hooks/CI/CD

Typical usage:
    from src.queue import enqueue, get_status, start_worker

    # Enqueue job with context-aware feedback
    job_id = enqueue("add_knowledge", payload, parallel=True)

    # Get queue status for health monitoring
    status = get_status()

    # Start worker on MCP boot (conditional startup if backlog exists)
    start_worker()

Public API:
    - enqueue(): Add job to queue with context-aware feedback
    - get_status(): Get queue statistics and health level
    - process_queue(): CLI fallback for manual processing
    - start_worker(): Start background worker (conditional on backlog)
    - stop_worker(): Stop background worker gracefully
    - get_queue(): Get singleton JobQueue instance
    - get_worker(): Get singleton BackgroundWorker instance
    - reset(): Reset singletons (for testing)
"""

from pathlib import Path
from typing import Optional

import structlog

from src.queue.models import (
    QueuedJob,
    JobStatus,
    QueueStats,
    DeadLetterJob,
)
from src.queue.detector import is_hook_context
from src.queue.storage import JobQueue
from src.queue.worker import BackgroundWorker

logger = structlog.get_logger()

# Module-level singletons
_queue: Optional[JobQueue] = None
_worker: Optional[BackgroundWorker] = None


def get_queue(db_path: Optional[Path] = None, max_size: int = 100) -> JobQueue:
    """Get singleton JobQueue instance.

    Creates queue on first call, reuses thereafter. Lazy initialization
    pattern matches src/llm/__init__.py get_client().

    Args:
        db_path: Path to queue directory. Only used on first call.
            Default: ~/.recall/job_queue
        max_size: Soft capacity limit. Only used on first call.
            Default: 100 jobs

    Returns:
        Singleton JobQueue instance
    """
    global _queue
    if _queue is None:
        _queue = JobQueue(db_path=db_path, max_size=max_size)
    return _queue


def get_worker() -> BackgroundWorker:
    """Get singleton BackgroundWorker instance.

    Creates worker on first call, reuses thereafter. Worker is initialized
    with singleton queue and default settings.

    Returns:
        Singleton BackgroundWorker instance
    """
    global _worker
    if _worker is None:
        _worker = BackgroundWorker(get_queue(), max_workers=4)
    return _worker


def enqueue(
    job_type: str,
    payload: dict,
    parallel: bool = False,
    silent: Optional[bool] = None
) -> str:
    """Enqueue job with context-aware feedback.

    Adds job to queue and provides appropriate feedback based on context:
    - Hook/CI/CD context (auto-detected): Silent mode, debug log only
    - Interactive CLI with --async flag: One-liner confirmation
    - Auto-detected hook with silent=None: Use is_hook_context() detection

    Args:
        job_type: Job category (e.g., "add_knowledge", "capture_commit")
        payload: CLI command and arguments as dict
        parallel: Whether job can run in parallel batch. Default: False
        silent: Override feedback mode. None=auto-detect, True=silent, False=verbose

    Returns:
        Job ID (UUID4 string) for tracking

    Examples:
        >>> # Hook context - auto-detected silent mode
        >>> job_id = enqueue("add_knowledge", {"command": "add", "args": ["hello"]})

        >>> # Interactive with explicit --async flag
        >>> job_id = enqueue("add_knowledge", payload, silent=False)
        Job queued: abc-123-def

        >>> # Explicit silent mode override
        >>> job_id = enqueue("add_knowledge", payload, silent=True)
    """
    # Enqueue job
    queue = get_queue()
    job_id = queue.enqueue(job_type, payload, parallel)

    # Determine feedback mode
    if silent is None:
        silent = is_hook_context()

    # Provide context-aware feedback
    if silent:
        # Silent mode - only structured debug log
        logger.debug(
            "job_queued_silent",
            job_id=job_id,
            job_type=job_type,
            parallel=parallel
        )
    else:
        # Interactive mode - user feedback
        logger.info(
            "job_queued",
            job_id=job_id,
            job_type=job_type,
            parallel=parallel
        )

    # Check if worker is running - if so, job will be picked up automatically
    worker = get_worker()
    if not worker.is_running():
        logger.debug(
            "worker_not_running",
            message="Worker not running - job will be processed when worker starts"
        )

    return job_id


def get_status() -> dict:
    """Get queue status with health level.

    Returns statistics plus health level based on capacity:
    - "ok": pending < 80% capacity
    - "warning": pending >= 80% capacity
    - "error": pending >= 100% capacity

    Same pattern as `graphiti health` command (per user decision).

    Returns:
        Dict with keys:
        - pending: Number of pending jobs
        - processing: Number of jobs being processed (always 0 at rest)
        - failed: Number of failed jobs (always 0 at rest)
        - dead_letter: Number of jobs in dead letter queue
        - max_size: Soft capacity limit
        - capacity_pct: Percentage of capacity used
        - worker_running: Whether background worker is running
        - health: Health level ("ok", "warning", "error")
    """
    queue = get_queue()
    stats = queue.get_stats()
    worker = get_worker()

    # Calculate health level
    if stats.capacity_pct >= 100:
        health = "error"
    elif stats.capacity_pct >= 80:
        health = "warning"
    else:
        health = "ok"

    # Return status dict
    return {
        "pending": stats.pending,
        "processing": stats.processing,
        "failed": stats.failed,
        "dead_letter": stats.dead_letter,
        "max_size": stats.max_size,
        "capacity_pct": stats.capacity_pct,
        "worker_running": worker.is_running(),
        "health": health
    }


def process_queue() -> tuple[int, int]:
    """Process queue manually (CLI fallback).

    Starts worker if not running and processes all pending jobs.
    Waits until the queue is empty AND the worker thread has fully
    finished its current job before returning.

    The previous implementation only waited for qsize()==0, but
    SQLiteAckQueue.qsize() returns 0 as soon as jobs are dequeued
    into "unacked" (in-flight) state — before they are actually
    processed. This caused the worker to be stopped mid-job, which
    meant process_pending_commits() was never called and the
    pending_commits file was never cleared.

    Fix: after qsize() drops to 0, call worker.stop(timeout=120) which
    joins the worker thread. The thread completes its current job before
    the stop event causes it to exit, so join() returns only after all
    in-flight work is done.

    Returns:
        Tuple of (success_count, failure_count) — placeholder counts
        (full tracking deferred, consistent with original implementation)
    """
    import time

    worker = get_worker()

    if not worker.is_running():
        worker.start()
        logger.info("worker_started_for_manual_processing")

    queue = get_queue()

    # Wait for all "ready" jobs to be picked up by the worker.
    # Once qsize()==0, all jobs are either in-flight or done.
    while queue.get_pending_count() > 0:
        time.sleep(0.5)

    # Stop the worker and JOIN the thread. worker.stop() signals the
    # stop event and then calls thread.join(timeout). The worker thread
    # only checks the stop event between jobs — it completes any
    # in-flight job before exiting. This ensures in-flight work finishes.
    worker.stop(timeout=120.0)

    logger.info("manual_processing_complete")

    return (0, 0)


def start_worker() -> None:
    """Start background worker conditionally.

    Starts worker if backlog exists (threshold=1 per research recommendation).
    Intended to be called on MCP server boot.

    Conditional eager startup pattern: Only start if jobs are waiting.
    Worker overhead is minimal, better to process proactively than accumulate
    backlog.
    """
    queue = get_queue()
    worker = get_worker()

    # Check if backlog exists
    pending_count = queue.get_pending_count()

    if pending_count > 0 and not worker.is_running():
        logger.info(
            "starting_worker_for_backlog",
            pending_count=pending_count,
            threshold=1
        )
        worker.start()
    elif worker.is_running():
        logger.debug("worker_already_running")
    else:
        logger.debug("no_backlog_worker_not_started", pending_count=0)


def stop_worker() -> None:
    """Stop background worker gracefully.

    Signals worker to stop and waits for clean shutdown. Worker completes
    current job before stopping.
    """
    worker = get_worker()
    if worker.is_running():
        logger.info("stopping_worker")
        worker.stop()
    else:
        logger.debug("worker_not_running_nothing_to_stop")


def reset() -> None:
    """Reset singleton instances.

    For testing only. Resets queue and worker singletons to None,
    forcing fresh initialization on next access.

    Same pattern as src/llm/reset_client().
    """
    global _queue, _worker

    # Stop worker if running
    if _worker and _worker.is_running():
        _worker.stop()

    _queue = None
    _worker = None


__all__ = [
    # Data models
    "QueuedJob",
    "JobStatus",
    "QueueStats",
    "DeadLetterJob",
    # Public API
    "enqueue",
    "get_status",
    "process_queue",
    "start_worker",
    "stop_worker",
    # Singletons
    "get_queue",
    "get_worker",
    # Testing
    "reset",
    # Utilities
    "is_hook_context",
]
