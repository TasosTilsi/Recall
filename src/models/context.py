from enum import Enum

class GraphScope(Enum):
    """Identifies which knowledge graph scope to use"""
    GLOBAL = "global"    # User preferences, stored in ~/.recall/global/
    PROJECT = "project"  # Project-specific knowledge, stored in .recall/
