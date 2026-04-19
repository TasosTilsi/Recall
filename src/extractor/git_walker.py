"""Git traversal utilities for the extractor package.

Provides:
- CommitRecord: dataclass representing a single git commit
- walk_commits(repo_root): return commits oldest-first, excluding merge commits
- batch_commits(commits, batch_size): split a list into batches
- fetch_diff(commit, repo): retrieve and truncate commit diff text
"""
from __future__ import annotations

import dataclasses
from datetime import datetime
from pathlib import Path

import git
import structlog

logger = structlog.get_logger(__name__)

_DIFF_MAX_CHARS = 4000


@dataclasses.dataclass
class CommitRecord:
    """A single git commit distilled for extraction."""

    sha: str
    short_sha: str
    author: str
    date: datetime
    message: str
    diff: str


def fetch_diff(commit: git.Commit, repo: git.Repo) -> str:
    """Return the diff text for *commit*, truncated to 4000 characters.

    Falls back to an empty string on any GitCommandError so callers never crash
    on unusual commits (e.g. initial commit with no parents, binary-only changes).
    """
    try:
        if commit.parents:
            diff_text = repo.git.diff(commit.parents[0].hexsha, commit.hexsha)
        else:
            # Initial commit — show stat summary instead
            diff_text = repo.git.show(commit.hexsha, "--stat")
    except git.GitCommandError:
        return ""

    return diff_text[:_DIFF_MAX_CHARS]


def walk_commits(repo_root: Path) -> list[CommitRecord]:
    """Return all non-merge commits from *repo_root* ordered oldest-first.

    Args:
        repo_root: Path to any directory inside the git repository.

    Returns:
        A list of :class:`CommitRecord` objects sorted oldest → newest.
    """
    repo = git.Repo(repo_root, search_parent_directories=True)

    records: list[CommitRecord] = []
    for commit in repo.iter_commits(rev="HEAD", reverse=True):
        if commit.message.strip().startswith("Merge "):
            continue

        diff = fetch_diff(commit, repo)

        records.append(
            CommitRecord(
                sha=commit.hexsha,
                short_sha=commit.hexsha[:7],
                author=commit.author.name,
                date=commit.authored_datetime,
                message=commit.message.strip(),
                diff=diff,
            )
        )

    logger.info("git_walker.walk_commits finished", count=len(records))
    return records


def batch_commits(
    commits: list[CommitRecord],
    batch_size: int = 10,
) -> list[list[CommitRecord]]:
    """Split *commits* into batches of at most *batch_size*.

    Args:
        commits: Flat list of CommitRecord objects.
        batch_size: Maximum number of commits per batch (default 10).

    Returns:
        A list of batches; the last batch may be smaller than *batch_size*.
        Returns an empty list when *commits* is empty.
    """
    if not commits:
        return []
    return [commits[i : i + batch_size] for i in range(0, len(commits), batch_size)]
