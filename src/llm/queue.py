"""Persistent queue for failed LLM requests.

This module provides SQLite-backed queueing for LLM operations that fail.
Failed requests are queued for later retry with bounded size and TTL constraints.
"""

import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Callable, Any

import structlog
from persistqueue import SQLiteAckQueue

from src.llm.config import LLMConfig

logger = structlog.get_logger()


@dataclass
class QueuedRequest:
    """Queued LLM request for later retry.

    Attributes:
        id: Unique request identifier for tracking
        operation: LLM operation type ("chat", "generate", "embed")
        params: Operation parameters (model, messages, etc.)
        timestamp: Unix timestamp when queued
        original_error: Error message from initial failure
    """

    id: str
    operation: str
    params: dict
    timestamp: float
    original_error: str


class LLMRequestQueue:
    """Persistent queue for failed LLM requests.

    Uses SQLite-backed queue for crash-resistance and thread-safety.
    Respects max_size and TTL constraints to prevent unbounded growth.
    """

    def __init__(self, config: LLMConfig, queue_path: Optional[Path] = None):
        """Initialize request queue.

        Args:
            config: LLM configuration with queue settings
            queue_path: Path to queue directory. Defaults to ~/.recall/llm_queue
        """
        self._config = config
        self._queue_path = queue_path or (Path.home() / ".recall" / "llm_queue")
        self._queue_path.mkdir(parents=True, exist_ok=True)

        # Initialize SQLite-backed queue with auto-commit.
        # multithreading=True sets check_same_thread=False so the queue can be
        # accessed from executor threads (ollama_chat is called via run_in_executor).
        self._queue = SQLiteAckQueue(str(self._queue_path), auto_commit=True, multithreading=True)

        self._logger = structlog.get_logger()
        self._max_size = config.queue_max_size
        self._item_ttl_seconds = config.queue_item_ttl_hours * 3600

    def enqueue(self, operation: str, params: dict, error: str) -> str:
        """Add failed request to queue.

        If queue is at max capacity, removes oldest items to make room.

        Args:
            operation: LLM operation type ("chat", "generate", "embed")
            params: Operation parameters dict
            error: Error message from failed operation

        Returns:
            Request ID for tracking
        """
        # Check queue size and prune if needed
        current_size = self.get_pending_count()
        if current_size >= self._max_size:
            # Remove oldest items until under limit
            to_remove = current_size - self._max_size + 1
            self._logger.warning(
                "queue_at_capacity",
                current_size=current_size,
                max_size=self._max_size,
                removing_oldest=to_remove
            )

            # Remove oldest items (process without retry)
            for _ in range(to_remove):
                try:
                    item = self._queue.get(block=False)
                    self._queue.ack(item)  # Remove permanently
                except Exception:
                    break  # Queue empty or error

        # Create queued request
        request_id = str(uuid.uuid4())
        request = QueuedRequest(
            id=request_id,
            operation=operation,
            params=params,
            timestamp=time.time(),
            original_error=error
        )

        # Add to queue
        self._queue.put(asdict(request))

        self._logger.info(
            "request_queued",
            request_id=request_id,
            operation=operation,
            error=error,
            message=f"Request queued for retry. ID: {request_id}"
        )

        return request_id

    def get_pending_count(self) -> int:
        """Get count of pending items in queue.

        Returns:
            Number of items awaiting processing
        """
        return self._queue.qsize()

    def process_one(self, processor_fn: Callable[[str, dict], Any]) -> bool:
        """Process one item from queue.

        Gets oldest item, checks if stale, and attempts processing.
        On success: item removed from queue.
        On failure: item returned to queue (nack).

        Args:
            processor_fn: Function to process item. Signature: fn(operation, params) -> result
                        Should raise exception on failure.

        Returns:
            True if item was processed (or skipped as stale), False if queue empty
        """
        try:
            # Get item without blocking
            item = self._queue.get(block=False)
        except Exception:
            # Queue empty
            return False

        # Check if item is stale (older than TTL)
        item_age = time.time() - item['timestamp']
        if item_age > self._item_ttl_seconds:
            # Stale item - remove without processing
            self._queue.ack(item)
            self._logger.debug(
                "stale_item_skipped",
                request_id=item['id'],
                age_hours=item_age / 3600,
                ttl_hours=self._config.queue_item_ttl_hours
            )
            return True

        # Attempt to process
        try:
            result = processor_fn(item['operation'], item['params'])

            # Success - remove from queue
            self._queue.ack(item)
            self._logger.info(
                "queue_item_processed",
                request_id=item['id'],
                operation=item['operation']
            )
            return True

        except Exception as e:
            # Failure - return to queue
            self._queue.nack(item)
            self._logger.warning(
                "queue_item_failed",
                request_id=item['id'],
                operation=item['operation'],
                error=str(e)
            )
            raise  # Re-raise to signal failure

    def process_all(self, processor_fn: Callable[[str, dict], Any]) -> tuple[int, int]:
        """Process all pending items in queue.

        Each item is attempted exactly once. Failed items remain in the queue
        for future retry but are not re-attempted in this batch.

        Args:
            processor_fn: Function to process items. Same signature as process_one.

        Returns:
            Tuple of (success_count, failure_count)
        """
        success_count = 0
        failure_count = 0

        # Dequeue all items upfront to avoid nack-cycling
        items = []
        items_to_process = self.get_pending_count()
        for _ in range(items_to_process):
            try:
                item = self._queue.get(block=False)
                items.append(item)
            except Exception:
                break

        for item in items:
            # Check if item is stale
            item_age = time.time() - item['timestamp']
            if item_age > self._item_ttl_seconds:
                self._queue.ack(item)
                self._logger.debug(
                    "stale_item_skipped",
                    request_id=item['id'],
                    age_hours=item_age / 3600,
                )
                continue

            try:
                processor_fn(item['operation'], item['params'])
                self._queue.ack(item)
                success_count += 1
                self._logger.info(
                    "queue_item_processed",
                    request_id=item['id'],
                    operation=item['operation'],
                )
            except Exception as e:
                self._queue.nack(item)
                failure_count += 1
                self._logger.warning(
                    "queue_item_failed",
                    request_id=item['id'],
                    operation=item['operation'],
                    error=str(e),
                )

        self._logger.info(
            "queue_batch_processed",
            success=success_count,
            failed=failure_count,
            remaining=self.get_pending_count()
        )

        return (success_count, failure_count)

    def clear_stale(self) -> int:
        """Remove all items older than TTL.

        Returns:
            Number of stale items removed
        """
        removed = 0
        items_to_check = self.get_pending_count()

        for _ in range(items_to_check):
            try:
                item = self._queue.get(block=False)
                item_age = time.time() - item['timestamp']

                if item_age > self._item_ttl_seconds:
                    # Stale - remove
                    self._queue.ack(item)
                    removed += 1
                else:
                    # Not stale - return to queue
                    self._queue.nack(item)

            except Exception:
                # Queue empty or error
                break

        if removed > 0:
            self._logger.info(
                "stale_items_cleared",
                removed=removed,
                ttl_hours=self._config.queue_item_ttl_hours
            )

        return removed

    def get_queue_stats(self) -> dict:
        """Get queue statistics.

        Returns:
            Dict with pending count, max size, and TTL
        """
        return {
            "pending": self.get_pending_count(),
            "max_size": self._max_size,
            "ttl_hours": self._config.queue_item_ttl_hours
        }
