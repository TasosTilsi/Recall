"""Background worker thread for processing queued jobs.

This module provides the BackgroundWorker class that runs as a background thread,
continuously processing jobs from the SQLite queue until signaled to stop.

Key features:
- Event-based lifecycle: Start/stop via threading.Event for graceful shutdown
- Parallel batching: ThreadPoolExecutor processes parallel jobs concurrently
- Sequential barriers: Non-parallel jobs processed alone
- Exponential backoff retry: 10s, 20s, 40s delays between attempts
- Dead letter handling: Jobs exhausted after 3 retries move to dead letter table
- CLI-first architecture: Worker replays CLI commands via subprocess

Thread safety: Worker runs in its own thread with ThreadPoolExecutor for parallel
batches. JobQueue handles its own thread safety via persistqueue.
"""

import asyncio
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Thread, Event
from typing import Optional

import structlog

# Use the graphiti binary from the same venv as the running interpreter
_GRAPHITI_CLI = str(Path(sys.executable).parent / "graphiti")

from src.queue.storage import JobQueue

logger = structlog.get_logger()


class BackgroundWorker:
    """Background worker thread for processing queue jobs.

    Runs continuously in a separate thread until signaled to stop via Event.
    Processes jobs from the queue with intelligent batching: sequential jobs
    act as barriers (processed alone), parallel jobs batch together for
    concurrent execution.

    Attributes:
        _queue: JobQueue instance for retrieving jobs
        _stop_event: Event for signaling worker to stop
        _thread: Worker thread (None if not running)
        _executor: ThreadPoolExecutor for parallel batches (created in worker thread)
        _max_workers: Max concurrent workers for parallel batches
        _max_retries: Maximum retry attempts before dead letter (default: 3)
        _base_backoff: Base delay in seconds for exponential backoff (default: 10)
        _logger: Structured logger
    """

    def __init__(self, job_queue: JobQueue, max_workers: int = 4):
        """Initialize background worker.

        Args:
            job_queue: JobQueue instance to process jobs from
            max_workers: Maximum concurrent workers for parallel batch processing.
                Default: 4 (optimal for I/O-bound CLI replay per research)
        """
        self._queue = job_queue
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = max_workers
        self._max_retries = 3  # User decision: 3 retries before dead letter
        self._base_backoff = 10  # User decision: 10s, 20s, 40s backoff
        self._logger = structlog.get_logger()

    def start(self) -> None:
        """Start worker thread.

        Creates and starts background thread if not already running. Non-daemon
        thread ensures graceful shutdown without losing in-progress jobs.
        """
        if self._thread is None or not self._thread.is_alive():
            # Reset stop event in case this is a restart
            self._stop_event.clear()

            # Create non-daemon thread (prevents job loss on exit)
            self._thread = Thread(target=self._run, daemon=False)
            self._thread.start()

            self._logger.info("background_worker_started")

    def stop(self, timeout: float = 30.0) -> None:
        """Stop worker thread gracefully.

        Signals worker to stop and waits for clean shutdown. Worker completes
        current job before stopping.

        Args:
            timeout: Maximum seconds to wait for shutdown. Default: 30s
        """
        if self._thread and self._thread.is_alive():
            self._logger.info("background_worker_stopping")

            # Signal stop
            self._stop_event.set()

            # Wait for thread to finish
            self._thread.join(timeout)

            if self._thread.is_alive():
                self._logger.warning(
                    "background_worker_timeout",
                    timeout_seconds=timeout,
                    message="Worker thread did not stop within timeout"
                )
            else:
                self._logger.info("background_worker_stopped")

            # Reset thread reference
            self._thread = None

    def is_running(self) -> bool:
        """Check if worker thread is running.

        Returns:
            True if worker thread is alive, False otherwise
        """
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        """Main worker loop (runs in background thread).

        Creates ThreadPoolExecutor for parallel batches and processes jobs
        until stop signal received. Uses Event.wait() for responsive shutdown
        without busy-waiting.
        """
        # Create thread pool for parallel batch processing
        self._executor = ThreadPoolExecutor(max_workers=self._max_workers)

        try:
            while not self._stop_event.is_set():
                # Get batch of jobs (parallel batch or single sequential)
                batch = self._queue.get_batch(max_items=self._max_workers)

                if not batch:
                    # Queue empty - wait briefly or until stopped
                    # Responsive shutdown: wake on stop signal or after 1s
                    self._stop_event.wait(timeout=1.0)
                    continue

                # Process batch based on parallelism
                if len(batch) == 1 and not batch[0].get('parallel', False):
                    # Sequential job - process alone (barrier)
                    self._process_single_job(batch[0])
                else:
                    # Parallel jobs - batch process concurrently
                    self._process_parallel_batch(batch)

        finally:
            # Cleanup thread pool on exit
            if self._executor:
                self._executor.shutdown(wait=True)
            self._logger.info("background_worker_shutdown_complete")

    def _process_single_job(self, item: dict) -> None:
        """Process single sequential job.

        Args:
            item: Job dict from queue
        """
        self._execute_with_retry(item)

    def _process_parallel_batch(self, items: list[dict]) -> None:
        """Process batch of parallel jobs concurrently.

        Uses ThreadPoolExecutor to run jobs in parallel. Individual job failures
        are isolated - one failure doesn't affect others (per user decision).

        Args:
            items: List of job dicts to process concurrently
        """
        # Submit all jobs to executor
        futures = {self._executor.submit(self._execute_with_retry, item): item
                   for item in items}

        # Wait for all to complete (failures handled in _execute_with_retry)
        for future in as_completed(futures):
            try:
                future.result()  # Raises exception if job raised
            except Exception as e:
                # Exception already logged in _execute_with_retry
                # Full isolation: continue processing other jobs
                pass

    def _execute_with_retry(self, item: dict) -> None:
        """Execute job with exponential backoff retry.

        Retries failed jobs with delays of 10s, 20s, 40s (exponential backoff).
        After max retries (3), moves job to dead letter queue.

        Args:
            item: Job dict from queue
        """
        job_id = item['id']
        attempts = item.get('attempts', 0)

        # Check if already exhausted retries
        if attempts >= self._max_retries:
            # Job was requeued too many times - move to dead letter immediately
            error = f"Job exhausted after {attempts} attempts"
            self._queue.move_to_dead_letter(item, error)
            return

        try:
            # Execute job by replaying CLI command
            self._replay_command(item)

            # Success - acknowledge and remove from queue
            self._queue.ack(item)

            self._logger.info(
                "job_completed",
                job_id=job_id,
                job_type=item['job_type'],
                attempts=attempts + 1
            )

        except Exception as e:
            error_msg = str(e)

            # Increment attempt counter for retry logic
            next_attempt = attempts + 1

            if next_attempt < self._max_retries:
                # Retry with exponential backoff
                delay = self._base_backoff * (2 ** attempts)  # 10, 20, 40

                self._logger.warning(
                    "job_failed_retrying",
                    job_id=job_id,
                    job_type=item['job_type'],
                    attempt=next_attempt,
                    max_retries=self._max_retries,
                    delay_seconds=delay,
                    error=error_msg
                )

                # Sleep with responsive shutdown (wake on stop signal)
                self._stop_event.wait(timeout=delay)

                # Requeue for retry
                self._queue.nack(item)

            else:
                # Max retries exceeded - move to dead letter
                self._logger.error(
                    "job_exhausted_dead_letter",
                    job_id=job_id,
                    job_type=item['job_type'],
                    attempts=next_attempt,
                    error=error_msg
                )

                self._queue.move_to_dead_letter(item, error_msg)

    def _replay_command(self, item: dict) -> None:
        """Replay CLI command from job payload.

        Reconstructs CLI command from payload and executes via subprocess.
        This is the CLI-first architecture: worker replays commands, CLI remains
        single source of truth (per user decision).

        For job types that do not use the generic CLI-replay format (i.e., they
        have a structured payload rather than a 'command' key), dispatch to a
        dedicated handler before falling through to the generic path.

        Args:
            item: Job dict with payload containing command and args

        Raises:
            RuntimeError: If command execution fails (non-zero exit code)
        """
        # Dispatch by job type for structured payloads (not generic CLI replay)
        job_type = item.get('job_type', '')
        if job_type == 'capture_tool_use':
            self._handle_capture_tool_use(item)
            return
        if job_type == 'capture_git_commits':
            success = self._handle_capture_git_commits(item)
            if not success:
                raise RuntimeError(
                    f"capture_git_commits handler failed for job {item['id']}: "
                    "payload missing 'pending_file' key"
                )
            return

        payload = item['payload']

        # Extract command and arguments from payload
        # Expected format: {"command": "add", "args": ["content"], "kwargs": {"scope": "project"}}
        command = payload.get('command', '')
        args = payload.get('args', [])
        kwargs = payload.get('kwargs', {})

        # Construct CLI command: [graphiti_venv_path, command, *args, *flags]
        cli_command = [_GRAPHITI_CLI, command] + args + self._kwargs_to_flags(kwargs)

        # Execute command via subprocess
        result = subprocess.run(
            cli_command,
            capture_output=True,
            text=True
        )

        # Check result
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed with exit code {result.returncode}: {result.stderr}"
            )

        # Log success
        self._logger.info(
            "command_replayed",
            job_id=item['id'],
            command=command,
            args=args,
            kwargs=kwargs
        )

    def _handle_capture_git_commits(self, item: dict) -> bool:
        """Handle capture_git_commits job type.

        This job type is enqueued by src/capture/git_worker.enqueue_git_processing()
        with payload={"pending_file": "/path/to/pending_commits"}. It does NOT use
        the generic CLI-replay format (no 'command' key), so it must be dispatched
        directly to process_pending_commits().

        Calling process_pending_commits() directly (rather than via subprocess) avoids
        the PATH dependency of the generic replay path and is safe because
        process_pending_commits() is pure Python with no global state mutations.

        Args:
            item: Job dict; payload must contain 'pending_file' key

        Returns:
            True if handler dispatched successfully, False if payload is malformed
        """
        payload = item.get('payload', {})
        pending_file_str = payload.get('pending_file')

        if not pending_file_str:
            self._logger.error(
                "capture_git_commits_missing_pending_file",
                job_id=item['id'],
                payload=payload
            )
            return False

        from pathlib import Path
        from src.capture.git_worker import process_pending_commits

        pending_file = Path(pending_file_str)

        self._logger.info(
            "capture_git_commits_dispatching",
            job_id=item['id'],
            pending_file=str(pending_file)
        )

        asyncio.run(process_pending_commits(pending_file=pending_file))

        self._logger.info(
            "capture_git_commits_complete",
            job_id=item['id'],
            pending_file=str(pending_file)
        )
        return True

    def _handle_capture_tool_use(self, item: dict) -> None:
        """Handle capture_tool_use job — store tool capture as graph episode via service.add().

        Payload format: {"content": "...", "session_id": "...", "cwd": "/abs/path", "timestamp": "..."}
        Calls service.add() directly (not via CLI subprocess) — content is pre-sanitized by capture_entry.py.
        Re-raises exceptions so BackgroundWorker's retry/dead-letter logic handles failures.
        """
        import asyncio
        from pathlib import Path

        payload = item.get('payload', {})
        content = payload.get('content', '').strip()
        session_id = payload.get('session_id', '')
        cwd_str = payload.get('cwd', '')

        if not content:
            self._logger.warning("capture_tool_use_empty_content", job_id=item['id'])
            return

        try:
            from src.graph.service import get_service
            from src.models import GraphScope
            from src.security import sanitize_content

            project_root = Path(cwd_str).resolve() if cwd_str else Path.home()
            # sanitize_content returns SanitizationResult; access .sanitized_content for the string
            sanitized = sanitize_content(content).sanitized_content

            if not sanitized.strip():
                self._logger.warning("capture_tool_use_sanitized_to_empty", job_id=item['id'])
                return

            service = get_service()
            asyncio.run(service.add(
                content=sanitized,
                scope=GraphScope.PROJECT,
                project_root=project_root,
                tags=([session_id] if session_id else []),
                source="tool_capture",
            ))

            self._logger.info(
                "capture_tool_use_stored",
                job_id=item['id'],
                session_id=session_id[:8] if session_id else "none",
            )
        except Exception as e:
            # Re-raise so BackgroundWorker's retry logic handles it
            raise RuntimeError(f"capture_tool_use handler failed: {e}") from e

    @staticmethod
    def _kwargs_to_flags(kwargs: dict) -> list[str]:
        """Convert kwargs dict to CLI flags.

        Converts dictionary to list of CLI flags:
        - {"scope": "project", "force": True} -> ["--scope", "project", "--force"]
        - Boolean True: flag only (no value)
        - Boolean False: skip flag
        - Other values: --key value pair

        Args:
            kwargs: Dictionary of keyword arguments

        Returns:
            List of CLI flag strings

        Examples:
            >>> BackgroundWorker._kwargs_to_flags({"scope": "project"})
            ["--scope", "project"]
            >>> BackgroundWorker._kwargs_to_flags({"force": True})
            ["--force"]
            >>> BackgroundWorker._kwargs_to_flags({"verbose": False})
            []
        """
        flags = []
        for key, value in kwargs.items():
            if value is True:
                # Boolean True - flag only
                flags.append(f"--{key}")
            elif value is False:
                # Boolean False - skip
                continue
            else:
                # Other value - flag with value
                flags.append(f"--{key}")
                flags.append(str(value))

        return flags
