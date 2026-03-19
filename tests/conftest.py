"""Shared pytest fixtures for graphiti-knowledge-graph tests."""
import pytest


# Phase 15 fixtures

@pytest.fixture
def graphiti_tmp_dir(tmp_path):
    """Temp directory with .graphiti/ subdirectory for hook tests."""
    (tmp_path / ".graphiti").mkdir(parents=True, exist_ok=True)
    return tmp_path
