"""Git history indexer for bootstrapping LadybugDB knowledge from past commits.

Provides GitIndexer for on-demand git history traversal and knowledge extraction.
Phase 6 post-commit hook handles ongoing real-time capture; this module
handles historical bootstrap (brownfield) and stale re-indexing.
"""
from src.indexer.indexer import GitIndexer
from src.indexer.state import IndexState

__all__ = ["GitIndexer", "IndexState"]
