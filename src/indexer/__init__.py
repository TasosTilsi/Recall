"""Incremental git history indexer for recall v3.0.

Provides run_init and run_sync as the public entry points for full and
incremental indexing of git history into the SQLite knowledge graph.
"""
from src.indexer.indexer import run_init, run_sync

__all__ = ["run_init", "run_sync"]
