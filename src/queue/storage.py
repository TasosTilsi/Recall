"""SQLite-backed persistent job queue with dead letter support.

This module provides the JobQueue class that manages job persistence, retrieval,
acknowledgment, and dead letter handling. It extends the pattern from src/llm/queue.py
with custom schema for job metadata and parallel/sequential batching logic.

Key features:
- SQLite persistence via persistqueue.SQLiteAckQueue
- FIFO ordering with batch retrieval
- Parallel job batching (consecutive parallel jobs processed together)
- Sequential job barriers (non-parallel jobs processed alone)
- Dead letter table for failed jobs
- Soft capacity limit (warnings at threshold, never reject)
"""

import json
import sqlite3
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Union

import structlog
from persistqueue import SQLiteAckQueue

from src.queue.models import QueuedJob, JobStatus, QueueStats, DeadLetterJob

logger = structlog.get_logger()


class JobQueue:
    """Persistent job queue with SQLite backing and dead letter support.

    Uses persistqueue.SQLiteAckQueue for the main job queue and a separate
    SQLite table for dead letter jobs. Provides FIFO ordering with intelligent
    batching: parallel jobs can be processed concurrently, sequential jobs act
    as barriers.

    Thread-safety: Main queue (SQLiteAckQueue) is thread-safe. Dead letter
    operations use a separate connection per call to avoid thread issues.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None, max_size: int = 100):
        """Initialize job queue.

        Args:
            db_path: Path to queue directory. Defaults to ~/.recall/job_queue
            max_size: Soft capacity limit. Jobs always accepted, warnings logged
                     when threshold exceeded. Default: 100 jobs.
        """
        # Ensure db_path is a Path object
        if db_path is None:
            self._db_path = Path.home() / ".recall" / "job_queue"
        elif isinstance(db_path, str):
            self._db_path = Path(db_path)
        else:
            self._db_path = db_path

        self._db_path.mkdir(parents=True, exist_ok=True)

        # Initialize main job queue with auto-commit
        self._queue = SQLiteAckQueue(str(self._db_path), auto_commit=True)

        self._max_size = max_size
        self._logger = structlog.get_logger()

        # Initialize dead letter table (separate SQLite connection)
        self._dead_letter_db = self._db_path / "dead_letter.db"
        self._init_dead_letter_table()

    def _init_dead_letter_table(self):
        """Initialize dead letter jobs table with WAL mode for concurrency."""
        conn = sqlite3.connect(str(self._dead_letter_db))
        try:
            # Enable WAL mode for better read concurrency
            conn.execute("PRAGMA journal_mode=WAL")

            # Create dead letter table if not exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    parallel INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    failed_at REAL NOT NULL,
                    final_error TEXT NOT NULL,
                    retry_count INTEGER NOT NULL
                )
            """)

            # Create index on failed_at for chronological queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_failed_at
                ON dead_letter_jobs(failed_at)
            """)

            conn.commit()
        finally:
            conn.close()

    def enqueue(self, job_type: str, payload: dict, parallel: bool = False) -> str:
        """Add job to queue.

        Jobs are always accepted regardless of queue size (soft limit).
        Warnings logged when approaching or exceeding capacity.

        Args:
            job_type: Job category (e.g., "add_knowledge", "capture_commit")
            payload: CLI command and arguments as dict
            parallel: Whether job can run in parallel batch. Default: False (sequential)

        Returns:
            Job ID (UUID4 string) for tracking

        Examples:
            >>> queue = JobQueue()
            >>> job_id = queue.enqueue("add_knowledge", {"cmd": "add", "args": ["hello"]}, parallel=True)
            >>> print(f"Queued: {job_id}")
        """
        # Check queue size and log warnings if approaching capacity
        current_size = self.get_pending_count()
        if current_size >= self._max_size:
            self._logger.warning(
                "queue_at_capacity",
                current_size=current_size,
                max_size=self._max_size,
                message="Queue at/over soft limit - job accepted but backpressure detected"
            )
        elif current_size >= self._max_size * 0.8:
            self._logger.warning(
                "queue_approaching_capacity",
                current_size=current_size,
                max_size=self._max_size,
                threshold_pct=80,
                message="Queue at 80% capacity"
            )

        # Create queued job with UUID and current timestamp
        job_id = str(uuid.uuid4())
        job = QueuedJob(
            id=job_id,
            job_type=job_type,
            payload=payload,
            parallel=parallel,
            created_at=time.time(),
            status=JobStatus.PENDING,
            attempts=0,
            last_error=None
        )

        # Serialize and enqueue
        self._queue.put(asdict(job))

        # Log structured event
        self._logger.info(
            "job_enqueued",
            job_id=job_id,
            job_type=job_type,
            parallel=parallel,
            queue_size=current_size + 1
        )

        return job_id

    def get_batch(self, max_items: int = 10) -> list[dict]:
        """Get batch of jobs for processing.

        Implements intelligent batching logic:
        - If first job is sequential (parallel=False): return only that job (barrier)
        - If first job is parallel (parallel=True): collect consecutive parallel jobs
          up to max_items. Stop when sequential job encountered (nack it back).

        This ensures sequential jobs are never processed concurrently and act as
        synchronization barriers.

        Args:
            max_items: Maximum number of parallel jobs to batch. Default: 10

        Returns:
            List of job dicts. Empty list if queue is empty.

        Examples:
            >>> # Queue has: [parallel1, parallel2, sequential1, parallel3]
            >>> batch = queue.get_batch(max_items=10)
            >>> # Returns: [parallel1, parallel2]
            >>> # sequential1 stays in queue as barrier
        """
        # Get first item (non-blocking)
        try:
            first_item = self._queue.get(block=False)
        except Exception:
            # Queue empty
            return []

        # Initialize batch with first item
        batch = [first_item]

        # If first job is sequential, return only it (barrier)
        if not first_item.get('parallel', False):
            return batch

        # First job is parallel - collect consecutive parallel jobs
        while len(batch) < max_items:
            try:
                item = self._queue.get(block=False)
            except Exception:
                # Queue empty - no more items
                break

            if item.get('parallel', False):
                # Parallel job - add to batch
                batch.append(item)
            else:
                # Sequential job encountered - nack it back, stop collecting
                self._queue.nack(item)
                break

        return batch

    def ack(self, item: dict) -> None:
        """Acknowledge successful job completion.

        Permanently removes job from queue.

        Args:
            item: Job dict returned from get_batch()
        """
        self._queue.ack(item)

    def nack(self, item: dict) -> None:
        """Requeue job for retry after failure.

        Increments attempt counter and returns job to queue.

        Args:
            item: Job dict returned from get_batch()
        """
        # Increment attempts counter
        item['attempts'] = item.get('attempts', 0) + 1

        # Return to queue
        self._queue.nack(item)

    def move_to_dead_letter(self, item: dict, error: str) -> None:
        """Move failed job to dead letter queue.

        Job is permanently removed from main queue and inserted into
        dead_letter_jobs table for inspection and potential manual retry.

        Args:
            item: Job dict that exhausted all retries
            error: Final error message from last attempt
        """
        job_id = item['id']

        # Insert into dead letter table
        conn = sqlite3.connect(str(self._dead_letter_db))
        try:
            conn.execute("""
                INSERT INTO dead_letter_jobs
                (id, job_type, payload, parallel, created_at, failed_at, final_error, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                item['job_type'],
                json.dumps(item['payload']),
                1 if item.get('parallel', False) else 0,
                item['created_at'],
                time.time(),
                error,
                item.get('attempts', 0)
            ))
            conn.commit()
        finally:
            conn.close()

        # Acknowledge item to remove from main queue
        self._queue.ack(item)

        # Log dead letter move
        self._logger.error(
            "job_moved_to_dead_letter",
            job_id=job_id,
            job_type=item['job_type'],
            attempts=item.get('attempts', 0),
            error=error
        )

    def get_dead_letter_jobs(self) -> list[DeadLetterJob]:
        """Retrieve all jobs in dead letter queue.

        Returns:
            List of DeadLetterJob instances, ordered by failed_at (oldest first)
        """
        conn = sqlite3.connect(str(self._dead_letter_db))
        try:
            cursor = conn.execute("""
                SELECT id, job_type, payload, parallel, created_at,
                       failed_at, final_error, retry_count
                FROM dead_letter_jobs
                ORDER BY failed_at ASC
            """)

            jobs = []
            for row in cursor.fetchall():
                job = DeadLetterJob(
                    id=row[0],
                    job_type=row[1],
                    payload=json.loads(row[2]),
                    parallel=bool(row[3]),
                    created_at=row[4],
                    failed_at=row[5],
                    final_error=row[6],
                    retry_count=row[7]
                )
                jobs.append(job)

            return jobs
        finally:
            conn.close()

    def retry_dead_letter(self, job_id: str) -> bool:
        """Move dead letter job back to main queue for retry.

        Args:
            job_id: ID of dead letter job to retry

        Returns:
            True if job found and requeued, False if not found
        """
        conn = sqlite3.connect(str(self._dead_letter_db))
        try:
            # Find job in dead letter table
            cursor = conn.execute("""
                SELECT id, job_type, payload, parallel, created_at
                FROM dead_letter_jobs
                WHERE id = ?
            """, (job_id,))

            row = cursor.fetchone()
            if not row:
                return False

            # Recreate job with reset attempts
            job_id_found = row[0]
            job_type = row[1]
            payload = json.loads(row[2])
            parallel = bool(row[3])
            original_created_at = row[4]

            # Delete from dead letter
            conn.execute("DELETE FROM dead_letter_jobs WHERE id = ?", (job_id_found,))
            conn.commit()

            # Enqueue back to main queue with reset attempts
            # Preserve original created_at for ordering
            job = QueuedJob(
                id=job_id_found,
                job_type=job_type,
                payload=payload,
                parallel=parallel,
                created_at=original_created_at,
                status=JobStatus.PENDING,
                attempts=0,
                last_error=None
            )
            self._queue.put(asdict(job))

            self._logger.info(
                "dead_letter_job_retried",
                job_id=job_id_found,
                job_type=job_type
            )

            return True

        finally:
            conn.close()

    def get_stats(self) -> QueueStats:
        """Get queue statistics.

        Returns:
            QueueStats instance with current metrics
        """
        # Query main queue pending count
        pending = self.get_pending_count()

        # Query dead letter count
        conn = sqlite3.connect(str(self._dead_letter_db))
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM dead_letter_jobs")
            dead_letter = cursor.fetchone()[0]
        finally:
            conn.close()

        # Create stats (processing and failed are transient, 0 at rest)
        return QueueStats(
            pending=pending,
            processing=0,
            failed=0,
            dead_letter=dead_letter,
            max_size=self._max_size
        )

    def get_pending_count(self) -> int:
        """Get count of pending jobs in main queue.

        Returns:
            Number of jobs awaiting processing
        """
        return self._queue.qsize()
