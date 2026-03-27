"""GitIndexer — main control flow for git history indexing.

Traverses the git commit history of a project, applies quality filters,
fetches diffs, runs two-pass LLM extraction, and persists state for
incremental re-runs.

Usage:
    indexer = GitIndexer(project_root=Path.cwd())
    stats = indexer.run()
    print(stats)
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import git
import structlog
from rich.console import Console

from src.capture.git_capture import fetch_commit_diff
from src.indexer.extraction import extract_commit_knowledge
from src.llm.config import load_config
from src.indexer.quality_gate import should_skip_commit
from src.indexer.state import (
    IndexState,
    add_processed_sha,
    clear_index_state,
    is_sha_processed,
    is_within_cooldown,
    load_state,
    save_state,
)
from src.models import GraphScope

logger = structlog.get_logger()


def _get_recall_instance_for_project(project_root: Path) -> tuple[Any, str]:
    """Get a Recall instance and group_id for project scope.

    Follows the same pattern as Phase 6 code (GraphService._get_recall_instance).

    Args:
        project_root: Root directory of the project

    Returns:
        Tuple of (instance, group_id)
    """
    from src.graph.service import get_service

    service = get_service()
    graphiti = asyncio.run(service._get_recall_instance(GraphScope.PROJECT, project_root))
    group_id = service._get_group_id(GraphScope.PROJECT, project_root)
    return graphiti, group_id


class GitIndexer:
    """Indexes git commit history into the Recall knowledge graph.

    Provides incremental indexing via a SHA cursor stored in
    .recall/index-state.json. A quality gate skips bot commits,
    tiny diffs, version-bump-only commits, and pure merge commits.

    Each qualifying commit is processed through a two-pass LLM extraction
    pipeline (structured Q&A + free-form entity extraction).
    """

    def __init__(self, project_root: Path, scope: Any = None) -> None:
        """Initialize GitIndexer.

        Args:
            project_root: Root directory of the project (contains .git/)
            scope: Unused; reserved for future multi-scope support
        """
        self.project_root = project_root
        self._logger = structlog.get_logger().bind(
            component="GitIndexer",
            project=project_root.name,
        )
        self.console = Console()

    def run(
        self,
        since: str | None = None,
        full: bool = False,
        verbose: bool = False,
        status_callback: Callable[[str], None] | None = None,
    ) -> dict:
        """Index git history and store results in the knowledge graph.

        Runs the full indexing pipeline:
        1. Cooldown check (skips if last run was within 5 minutes)
        2. Load incremental state (processed SHAs + last SHA cursor)
        3. Iterate commits from git history
        4. Apply quality gate to filter unworthy commits
        5. Fetch diff and run two-pass LLM extraction
        6. Save state after each commit for crash recovery

        Args:
            since: Optional SHA or date string to start iteration from.
                   If None, uses last_indexed_sha cursor from state.
            full: If True, clears state and re-indexes all history.
            verbose: If True, emit more detailed log messages.
            status_callback: Optional callable(message) for progress reporting.

        Returns:
            Dict with keys:
              - commits_processed: int
              - commits_skipped: int
              - entities_created: int (placeholder, recall doesn't count)
              - elapsed_seconds: float
              - skipped_reason: str (only present when returning early)
        """
        start_time = time.monotonic()
        cfg = load_config()

        # Cooldown check (skip if recently run, unless full re-index requested)
        if not full and is_within_cooldown(self.project_root):
            self._logger.info("within_cooldown_skipping")
            return {
                "commits_processed": 0,
                "commits_skipped": 0,
                "entities_created": 0,
                "elapsed_seconds": 0.0,
                "skipped_reason": "cooldown",
            }

        # Full re-index: clear state first
        if full:
            self._logger.info("full_reindex_clearing_state")
            clear_index_state(self.project_root)

        # Load state
        state = load_state(self.project_root)

        # Open git repo
        try:
            repo = git.Repo(str(self.project_root), search_parent_directories=True)
        except git.InvalidGitRepositoryError as e:
            self._logger.error("not_a_git_repo", error=str(e))
            return {
                "commits_processed": 0,
                "commits_skipped": 0,
                "entities_created": 0,
                "elapsed_seconds": time.monotonic() - start_time,
                "skipped_reason": "not_a_git_repo",
            }

        # Determine the SHA cursor for incremental iteration
        # Priority: explicit `since` SHA arg > state cursor
        since_sha: str | None = None
        since_date: str | None = None

        if since:
            # Detect if since looks like a date string (contains '-' or '/')
            if any(c in since for c in ('-', '/', ' ')):
                since_date = since
            elif len(since) >= 4:
                # Treat as SHA cursor (stop when we reach this SHA)
                since_sha = since
        elif not full:
            # Use state cursor for incremental runs
            since_sha = state.last_indexed_sha

        # Build iter_commits kwargs
        iter_kwargs: dict = {}
        if since_date:
            iter_kwargs["since"] = since_date

        # Get recall instance and group_id once for the whole run
        try:
            instance, group_id = _get_recall_instance_for_project(self.project_root)
        except Exception as e:
            self._logger.error("recall_init_failed", error=str(e))
            return {
                "commits_processed": 0,
                "commits_skipped": 0,
                "entities_created": 0,
                "elapsed_seconds": time.monotonic() - start_time,
                "skipped_reason": "recall_init_failed",
            }

        commits_processed = 0
        commits_skipped = 0
        entities_created = 0

        try:
            for commit in repo.iter_commits(**iter_kwargs):
                # Stop at the cursor SHA (already indexed)
                if since_sha and commit.hexsha == since_sha:
                    self._logger.debug("reached_cursor_sha", sha=commit.hexsha[:8])
                    break

                # Secondary dedup: skip if already in processed_shas
                if is_sha_processed(state, commit.hexsha):
                    self._logger.debug("sha_already_processed", sha=commit.hexsha[:8])
                    commits_skipped += 1
                    continue

                # Quality gate
                skip, reason = should_skip_commit(commit)
                if skip:
                    self._logger.debug(
                        "commit_skipped_quality_gate",
                        sha=commit.hexsha[:8],
                        reason=reason,
                    )
                    commits_skipped += 1
                    continue

                # Fetch diff
                try:
                    diff_content = fetch_commit_diff(
                        commit_sha=commit.hexsha,
                        repo_path=self.project_root,
                    )
                except Exception as e:
                    self._logger.error(
                        "diff_fetch_failed",
                        sha=commit.hexsha[:8],
                        error=str(e),
                    )
                    commits_skipped += 1
                    continue

                if status_callback:
                    status_callback(f"Processing commit {commit.hexsha[:8]}: {str(commit.message).splitlines()[0][:60]}")

                # Convert commit timestamp to UTC datetime
                reference_time = datetime.fromtimestamp(
                    commit.committed_date, tz=timezone.utc
                )

                # Run two-pass LLM extraction (sync wrapper around async)
                result = {"passes": 0}
                try:
                    result = asyncio.run(
                        extract_commit_knowledge(
                            commit_sha=commit.hexsha,
                            commit_message=str(commit.message).strip(),
                            commit_author=commit.author.name or commit.author.email or "unknown",
                            diff_content=diff_content,
                            instance=instance,
                            group_id=group_id,
                            reference_time=reference_time,
                            capture_mode=cfg.capture_mode,
                        )
                    )
                    if result.get("passes", 0) > 0:
                        entities_created += result["passes"]
                except RuntimeError:
                    # If we're inside an existing event loop, run differently
                    try:
                        loop = asyncio.get_event_loop()
                        result = loop.run_until_complete(
                            extract_commit_knowledge(
                                commit_sha=commit.hexsha,
                                commit_message=str(commit.message).strip(),
                                commit_author=commit.author.name or commit.author.email or "unknown",
                                diff_content=diff_content,
                                instance=instance,
                                group_id=group_id,
                                reference_time=reference_time,
                                capture_mode=cfg.capture_mode,
                            )
                        )
                        if result.get("passes", 0) > 0:
                            entities_created += result["passes"]
                    except Exception as e:
                        self._logger.error(
                            "extraction_failed",
                            sha=commit.hexsha[:8],
                            error=str(e),
                        )

                # Only mark as processed if extraction succeeded.
                # LLM failures (passes=0) leave the commit unprocessed so
                # the next `recall index` run retries it when Ollama is available.
                extraction_ok = result.get("passes", 0) > 0
                if extraction_ok:
                    add_processed_sha(state, commit.hexsha)
                    state.last_indexed_sha = commit.hexsha
                    state.indexed_commits_count += 1
                    save_state(self.project_root, state)

                commits_processed += 1
                self._logger.info(
                    "commit_indexed",
                    sha=commit.hexsha[:8],
                    total=commits_processed,
                    extraction_ok=extraction_ok,
                )

        except Exception as e:
            self._logger.error("iteration_failed", error=str(e))

        # Update last_run_at timestamp
        state.last_run_at = datetime.now(timezone.utc).isoformat()
        save_state(self.project_root, state)

        elapsed = time.monotonic() - start_time
        self._logger.info(
            "indexing_complete",
            commits_processed=commits_processed,
            commits_skipped=commits_skipped,
            entities_created=entities_created,
            elapsed_seconds=round(elapsed, 2),
        )

        return {
            "commits_processed": commits_processed,
            "commits_skipped": commits_skipped,
            "entities_created": entities_created,
            "elapsed_seconds": round(elapsed, 2),
        }

    def reset_full(self) -> None:
        """Reset the full index state and remove git-history-index episodes from graph.

        Clears the SHA cursor and processed-SHA set from disk. Then attempts
        to delete all Episodic nodes tagged with 'git-history-index' from the
        LadybugDB graph. If the graph deletion fails (e.g., unsupported Cypher
        syntax), logs a warning and continues — the SHA state is still cleared
        so re-indexing will proceed (recall deduplication handles overlap).
        """
        self._logger.info("resetting_full_index")

        # Clear the on-disk state file
        clear_index_state(self.project_root)

        # Attempt to delete existing git-history-index episodes from LadybugDB
        try:
            instance, group_id = _get_recall_instance_for_project(self.project_root)

            async def _delete_episodes() -> None:
                driver = instance.driver
                records, _, _ = await driver.execute_query(
                    """
                    MATCH (e:Episodic)
                    WHERE e.group_id = $group_id AND e.source_description CONTAINS 'git-history-index'
                    RETURN e.uuid AS uuid
                    """,
                    group_id=group_id,
                )
                uuids = [r["uuid"] for r in records]
                if uuids:
                    from graphiti_core.nodes import Node
                    await Node.delete_by_uuids(driver, uuids)
                    self._logger.info("deleted_git_history_episodes", count=len(uuids))
                else:
                    self._logger.debug("no_git_history_episodes_to_delete")

            asyncio.run(_delete_episodes())

        except Exception as e:
            self._logger.warning(
                "failed_to_delete_episodes_from_graph",
                error=str(e),
                note="SHA state cleared; re-indexing will proceed normally",
            )
