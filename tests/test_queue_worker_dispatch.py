"""Tests for BackgroundWorker job-type dispatch.

Verifies that _replay_command() correctly dispatches capture_git_commits jobs
to _handle_capture_git_commits() instead of the generic CLI subprocess path.

Bug context (Phase 8.3 gap closure):
    git_worker.enqueue_git_processing() creates jobs with:
        job_type="capture_git_commits", payload={"pending_file": "/path/..."}
    Previously _replay_command() read payload.get('command', '') → "" which
    caused subprocess failure and moved every git capture job to dead letter.

Fix: _replay_command() now checks job_type first and dispatches to
_handle_capture_git_commits() which calls process_pending_commits() directly.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from src.queue.storage import JobQueue
from src.queue.worker import BackgroundWorker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(job_type: str, payload: dict, job_id: str = "test-job-001") -> dict:
    """Build a minimal job dict matching what JobQueue.get_batch() returns."""
    return {
        "id": job_id,
        "job_type": job_type,
        "payload": payload,
        "parallel": False,
        "attempts": 0,
        "created_at": 0.0,
        "status": "pending",
        "last_error": None,
    }


@pytest.fixture
def worker(tmp_path):
    """BackgroundWorker with isolated tmp queue."""
    queue = JobQueue(db_path=tmp_path / "queue")
    return BackgroundWorker(queue)


# ---------------------------------------------------------------------------
# Class 1: dispatch routing
# ---------------------------------------------------------------------------

class TestCaptureGitCommitsDispatch:
    """_replay_command() routes capture_git_commits to _handle_capture_git_commits."""

    def test_dispatch_calls_handler_not_subprocess(self, worker):
        """capture_git_commits jobs call the handler, never subprocess.run."""
        job = _make_job(
            job_type="capture_git_commits",
            payload={"pending_file": "/tmp/fake_pending"},
        )

        with patch.object(worker, "_handle_capture_git_commits", return_value=True) as mock_handler, \
             patch("subprocess.run") as mock_subprocess:
            worker._replay_command(job)

        mock_handler.assert_called_once_with(job)
        mock_subprocess.assert_not_called()

    def test_handler_failure_raises_runtime_error(self, worker):
        """Handler returning False causes RuntimeError (job will retry)."""
        job = _make_job(
            job_type="capture_git_commits",
            payload={},  # Missing pending_file → handler returns False
        )

        with patch.object(worker, "_handle_capture_git_commits", return_value=False):
            with pytest.raises(RuntimeError, match="capture_git_commits handler failed"):
                worker._replay_command(job)

    def test_generic_job_uses_subprocess(self, worker):
        """Non-capture job types still go through subprocess.run."""
        job = _make_job(
            job_type="add_knowledge",
            payload={"command": "add", "args": ["hello"], "kwargs": {}},
        )

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_subprocess, \
             patch.object(worker, "_handle_capture_git_commits") as mock_handler:
            worker._replay_command(job)

        mock_subprocess.assert_called_once()
        mock_handler.assert_not_called()
        # Verify the subprocess was called with the right command structure
        call_args = mock_subprocess.call_args[0][0]
        assert Path(call_args[0]).name == "graphiti"
        assert call_args[1] == "add"


# ---------------------------------------------------------------------------
# Class 2: _handle_capture_git_commits unit tests
# ---------------------------------------------------------------------------

class TestHandleCaptureGitCommits:
    """Unit tests for _handle_capture_git_commits() method."""

    def test_missing_pending_file_key_returns_false(self, worker):
        """Payload without 'pending_file' returns False (malformed job)."""
        job = _make_job(
            job_type="capture_git_commits",
            payload={},  # No pending_file key
        )
        result = worker._handle_capture_git_commits(job)
        assert result is False

    def test_empty_pending_file_value_returns_false(self, worker):
        """Payload with pending_file=None or '' returns False."""
        job = _make_job(
            job_type="capture_git_commits",
            payload={"pending_file": ""},
        )
        result = worker._handle_capture_git_commits(job)
        assert result is False

    def test_valid_pending_file_calls_process_pending_commits(self, worker, tmp_path):
        """Valid pending_file triggers asyncio.run(process_pending_commits(...))."""
        pending_file = tmp_path / "pending_commits"
        # Write a fake commit hash so process_pending_commits has something to read
        pending_file.write_text("abc1234567890\n")

        job = _make_job(
            job_type="capture_git_commits",
            payload={"pending_file": str(pending_file)},
        )

        # Patch process_pending_commits to avoid real LLM/git calls
        with patch(
            "src.capture.git_worker.process_pending_commits",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_ppc:
            result = worker._handle_capture_git_commits(job)

        assert result is True
        mock_ppc.assert_called_once()
        # Verify it was called with the correct pending_file Path
        call_kwargs = mock_ppc.call_args.kwargs
        assert "pending_file" in call_kwargs
        assert str(call_kwargs["pending_file"]) == str(pending_file)

    def test_nonexistent_pending_file_still_returns_true(self, worker):
        """process_pending_commits handles missing file gracefully (returns []).

        The handler should return True because process_pending_commits() does not
        raise on a missing file — it returns an empty list. The handler's job is
        only to dispatch; it should not pre-validate file existence.
        """
        job = _make_job(
            job_type="capture_git_commits",
            payload={"pending_file": "/tmp/definitely_does_not_exist_8a3b2c"},
        )

        with patch(
            "src.capture.git_worker.process_pending_commits",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_ppc:
            result = worker._handle_capture_git_commits(job)

        assert result is True
        mock_ppc.assert_called_once()


# ---------------------------------------------------------------------------
# Class 3: Integration smoke test (queue → worker → process_pending_commits)
# ---------------------------------------------------------------------------

class TestFlow3Integration:
    """End-to-end smoke test for Flow 3: enqueue → worker → process_pending_commits.

    Uses a real JobQueue and BackgroundWorker. Patches process_pending_commits
    to avoid LLM/Kuzu dependencies.
    """

    def test_enqueued_capture_job_does_not_land_in_dead_letter(self, tmp_path):
        """Enqueued capture_git_commits job is processed, not dead-lettered.

        This is the regression test for the Phase 8.3 bug:
        Before fix: job_type='capture_git_commits' → _replay_command reads
                    payload.get('command', '') → '' → subprocess(['graphiti', ''])
                    → non-zero exit → RuntimeError → 3 retries → dead letter.
        After fix:  dispatches to _handle_capture_git_commits → asyncio.run(
                    process_pending_commits()) → success → ack → dead_letter=0.
        """
        # Create a pending commits file with one fake hash
        pending_file = tmp_path / "pending_commits"
        pending_file.write_text("deadbeef01234567\n")

        queue = JobQueue(db_path=tmp_path / "queue")
        worker = BackgroundWorker(queue, max_workers=1)

        # Enqueue the job exactly as git_worker.enqueue_git_processing() does
        queue.enqueue(
            job_type="capture_git_commits",
            payload={"pending_file": str(pending_file)},
            parallel=False,
        )

        assert queue.get_pending_count() == 1

        # Patch process_pending_commits to avoid real git/LLM calls
        with patch(
            "src.capture.git_worker.process_pending_commits",
            new_callable=AsyncMock,
            return_value=[],
        ):
            # Process the single job (one iteration of the worker loop)
            batch = queue.get_batch(max_items=1)
            assert len(batch) == 1
            worker._execute_with_retry(batch[0])

        # Job should be acknowledged (pending=0) and NOT in dead letter
        assert queue.get_pending_count() == 0
        stats = queue.get_stats()
        assert stats.dead_letter == 0, (
            f"Job landed in dead letter queue. "
            f"dead_letter={stats.dead_letter}. "
            "Dispatch fix may not be applied correctly."
        )
