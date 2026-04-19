"""Tests for src.extractor.git_walker module."""
from pathlib import Path

import pytest

from src.extractor.git_walker import (
    CommitRecord,
    batch_commits,
    fetch_diff,
    walk_commits,
)


REPO_ROOT = Path(__file__).resolve().parents[2]  # project root


class TestCommitRecord:
    def test_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(CommitRecord)

    def test_fields_exist(self):
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(CommitRecord)}
        assert field_names == {"sha", "short_sha", "author", "date", "message", "diff"}


class TestWalkCommits:
    def test_returns_non_empty_list(self):
        commits = walk_commits(REPO_ROOT)
        assert isinstance(commits, list)
        assert len(commits) > 0

    def test_all_records_have_non_empty_sha(self):
        commits = walk_commits(REPO_ROOT)
        for c in commits:
            assert isinstance(c.sha, str)
            assert len(c.sha) == 40, f"Expected 40-char sha, got {len(c.sha)}: {c.sha}"

    def test_all_records_have_non_empty_message(self):
        commits = walk_commits(REPO_ROOT)
        for c in commits:
            assert isinstance(c.message, str)
            assert len(c.message) > 0

    def test_short_sha_is_first_7_chars(self):
        commits = walk_commits(REPO_ROOT)
        for c in commits:
            assert c.short_sha == c.sha[:7]

    def test_no_merge_commits(self):
        commits = walk_commits(REPO_ROOT)
        for c in commits:
            assert not c.message.startswith("Merge "), (
                f"Merge commit should be skipped: {c.message!r}"
            )

    def test_commit_record_types(self):
        from datetime import datetime
        commits = walk_commits(REPO_ROOT)
        first = commits[0]
        assert isinstance(first.sha, str)
        assert isinstance(first.short_sha, str)
        assert isinstance(first.author, str)
        assert isinstance(first.date, datetime)
        assert isinstance(first.message, str)
        assert isinstance(first.diff, str)


class TestBatchCommits:
    def _make_commits(self, n: int) -> list:
        """Create n fake CommitRecord objects for testing."""
        from datetime import datetime
        return [
            CommitRecord(
                sha="a" * 40,
                short_sha="aaaaaaa",
                author="test",
                date=datetime.now(),
                message=f"commit {i}",
                diff="",
            )
            for i in range(n)
        ]

    def test_empty_input_returns_empty(self):
        result = batch_commits([], 10)
        assert result == []

    def test_single_full_batch(self):
        commits = self._make_commits(3)
        result = batch_commits(commits, 10)
        assert len(result) == 1
        assert result[0] == commits

    def test_exact_batch_size(self):
        commits = self._make_commits(10)
        result = batch_commits(commits, 10)
        assert len(result) == 1
        assert len(result[0]) == 10

    def test_splits_correctly(self):
        commits = self._make_commits(3)
        result = batch_commits(commits, 2)
        assert len(result) == 2
        assert result[0] == commits[:2]
        assert result[1] == commits[2:]

    def test_default_batch_size_is_10(self):
        commits = self._make_commits(25)
        result = batch_commits(commits)
        assert len(result) == 3
        assert len(result[0]) == 10
        assert len(result[1]) == 10
        assert len(result[2]) == 5

    def test_preserves_order(self):
        commits = self._make_commits(5)
        result = batch_commits(commits, 2)
        flattened = [c for batch in result for c in batch]
        assert flattened == commits


class TestFetchDiff:
    def test_returns_string(self):
        import git
        repo = git.Repo(REPO_ROOT, search_parent_directories=True)
        commits = list(repo.iter_commits(rev="HEAD", max_count=5))
        if commits:
            diff = fetch_diff(commits[0], repo)
            assert isinstance(diff, str)

    def test_truncated_to_4000_chars(self):
        import git
        repo = git.Repo(REPO_ROOT, search_parent_directories=True)
        commits = list(repo.iter_commits(rev="HEAD", max_count=5))
        for c in commits:
            diff = fetch_diff(c, repo)
            assert len(diff) <= 4000, f"Diff exceeds 4000 chars: {len(diff)}"
