"""High-level GraphService wrapping graphiti_core's Graphiti class.

This service provides the main API that all CLI commands use for graph operations.
It handles:
- Per-scope recall instance initialization (global vs project)
- Adapter wiring (OllamaLLMClient, OllamaEmbedder, LadybugDriver)
- Async/sync bridging for CLI context
- Content sanitization
- Error handling and logging
"""

import asyncio
import json
import structlog
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodeType, Node

from src.config.paths import GLOBAL_DB_PATH, get_project_db_path
from src.graph.adapters import NoOpCrossEncoder, OllamaEmbedder, OllamaLLMClient, make_llm_client, make_embedder
from src.llm import LLMUnavailableError
from src.llm import chat as ollama_chat
from src.llm.config import load_config
from src.models import GraphScope
from src.security import sanitize_content as secure_content
from src.storage import GraphManager

# Retention manager — optional; functions fall back gracefully when absent
try:
    from src.retention import get_retention_manager
except ImportError:  # pragma: no cover
    get_retention_manager = None  # type: ignore[assignment]

logger = structlog.get_logger(__name__)

# Singleton instance
_service: Optional["GraphService"] = None


def get_service() -> "GraphService":
    """Get or create the singleton GraphService.

    Returns:
        GraphService instance
    """
    global _service
    if _service is None:
        _service = GraphService()
    return _service


def reset_service() -> None:
    """Reset the singleton service. Useful for testing."""
    global _service
    _service = None


def run_graph_operation(coro):
    """Run an async graph operation from sync context.

    This helper allows CLI commands (which are sync) to call async
    GraphService methods cleanly.

    Args:
        coro: Coroutine to run

    Returns:
        Result from the coroutine

    Example:
        result = run_graph_operation(service.add(...))
    """
    return asyncio.run(coro)


class GraphService:
    """High-level service for graph operations.

    Provides the main API used by CLI commands. Handles recall instance initialization
    per scope, adapter wiring, and exposes methods for add, search, list, get,
    delete, summarize, compact, and stats operations.
    """

    def __init__(self, read_only: bool = False):
        """Initialize GraphService with adapters and manager."""
        # Create storage manager
        self._graph_manager = GraphManager(read_only=read_only)

        # Create adapters (reused across all scopes)
        # Phase 13: factory routing — selects correct client based on [llm] config
        config = load_config()
        self._llm_client = make_llm_client(config)
        self._embedder = make_embedder(config)
        self._cross_encoder = self._create_cross_encoder()

        # Cache recall instances per scope
        self._recall_instances: dict[str, Graphiti] = {}

        logger.debug("GraphService initialized")

    def _create_cross_encoder(self):
        """Create cross-encoder based on configuration.

        Reads [reranking] config section and returns the appropriate
        cross-encoder client. Falls back to NoOpCrossEncoder on any error.
        """
        config = load_config()

        if not config.reranking_enabled or config.reranking_backend == "none":
            logger.debug("Reranking disabled, using NoOpCrossEncoder")
            return NoOpCrossEncoder()

        if config.reranking_backend == "bge":
            try:
                from graphiti_core.cross_encoder.bge_reranker_client import BGERerankerClient
                logger.info("Using BGE reranker (BAAI/bge-reranker-v2-m3)")
                return BGERerankerClient()
            except ImportError:
                logger.warning(
                    "BGE reranker unavailable, falling back to NoOpCrossEncoder",
                    hint="Install with: pip install sentence-transformers",
                )
                return NoOpCrossEncoder()

        if config.reranking_backend == "openai":
            try:
                from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
                logger.info("Using OpenAI reranker")
                return OpenAIRerankerClient()
            except Exception as e:
                logger.warning(
                    "OpenAI reranker failed, falling back to NoOpCrossEncoder",
                    error=str(e),
                )
                return NoOpCrossEncoder()

        logger.warning(
            "Unknown reranking backend, using NoOpCrossEncoder",
            backend=config.reranking_backend,
        )
        return NoOpCrossEncoder()

    def _get_cache_key(self, scope: GraphScope, project_root: Optional[Path]) -> str:
        """Get cache key for recall instance.

        Args:
            scope: Graph scope
            project_root: Project root path (for PROJECT scope)

        Returns:
            Cache key string
        """
        if scope == GraphScope.GLOBAL:
            return "global"
        else:
            # Use resolved path string as key
            return f"project:{project_root.resolve()}" if project_root else "project:none"

    async def _get_recall_instance(
        self, scope: GraphScope, project_root: Optional[Path] = None
    ) -> Graphiti:
        """Get or create recall instance for scope.

        On first use for a given scope, calls build_indices_and_constraints()
        to ensure the FTS index and schema exist in the LadybugDB database.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Recall instance configured for the scope

        Raises:
            ValueError: If project_root not provided for PROJECT scope
        """
        cache_key = self._get_cache_key(scope, project_root)

        # Return cached instance if exists
        if cache_key in self._recall_instances:
            logger.debug("Using cached recall instance", cache_key=cache_key)
            return self._recall_instances[cache_key]

        # Create new recall instance
        logger.debug("Creating new recall instance", cache_key=cache_key)

        # Get LadybugDriver for this scope
        driver = self._graph_manager.get_driver(scope, project_root)

        # Create Graphiti with our adapters
        instance = Graphiti(
            graph_driver=driver,
            llm_client=self._llm_client,
            embedder=self._embedder,
            cross_encoder=self._cross_encoder,
        )

        # Build schema, indices, and FTS indexes on first use.
        # This is idempotent — safe to call on an existing database.
        await instance.build_indices_and_constraints()
        logger.debug("Built indices and constraints", cache_key=cache_key)

        # Cache and return
        self._recall_instances[cache_key] = instance
        return instance

    def _get_group_id(self, scope: GraphScope, project_root: Optional[Path]) -> str:
        """Get group ID for scope.

        Args:
            scope: Graph scope
            project_root: Project root path

        Returns:
            Group ID string for use in graphiti_core
        """
        if scope == GraphScope.GLOBAL:
            return "global"
        else:
            return project_root.name if project_root else "unknown_project"

    def _resolve_db_path(self, scope: GraphScope, project_root: Optional[Path]) -> Optional[Path]:
        """Resolve the LadybugDB database path for a given scope without calling _get_recall_instance().

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Path to the LadybugDB database directory, or None if unresolvable
        """
        if scope == GraphScope.GLOBAL:
            return GLOBAL_DB_PATH
        elif project_root:
            return get_project_db_path(project_root)
        return None

    def _get_db_size(self, scope: GraphScope, project_root: Optional[Path], driver) -> int:
        """Calculate database size in bytes.

        Args:
            scope: Graph scope
            project_root: Project root path
            driver: Graph driver instance

        Returns:
            Database size in bytes (0 if calculation fails)
        """
        db_path = None
        try:
            # Try to get database path from driver
            if hasattr(driver, "db") and hasattr(driver.db, "database_path"):
                db_path = str(driver.db.database_path)
        except AttributeError:
            pass

        # Fallback to path configuration if needed
        if db_path is None:
            if scope == GraphScope.GLOBAL:
                db_path = str(GLOBAL_DB_PATH)
            elif project_root:
                db_path = str(get_project_db_path(project_root))

        # Calculate size
        size_bytes = 0
        if db_path:
            try:
                for dirpath, dirnames, filenames in os.walk(db_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        size_bytes += os.path.getsize(fp)
            except OSError as ose:
                logger.warning(
                    "Could not calculate database size", path=db_path, error=str(ose)
                )
                size_bytes = 0

        return size_bytes

    async def add(
        self,
        content: str,
        scope: GraphScope,
        project_root: Optional[Path],
        tags: Optional[list[str]] = None,
        source: str = "cli",
    ) -> dict:
        """Add content to the knowledge graph.

        Args:
            content: Text content to add
            scope: Graph scope (GLOBAL or PROJECT)
            project_root: Project root path (required for PROJECT scope)
            tags: Optional tags for the content
            source: Source description (default: "cli")

        Returns:
            Dict with: name, type, scope, created_at, tags, source, content_length,
                      nodes_created, edges_created

        Raises:
            LLMUnavailableError: If LLM is unavailable for extraction
        """
        logger.info(
            "Adding content to graph",
            scope=scope.value,
            content_length=len(content),
            has_tags=bool(tags),
        )

        # Sanitize content for secrets
        sanitization_result = secure_content(content, project_root=project_root)
        sanitized_content = sanitization_result.sanitized_content

        if sanitization_result.was_modified:
            logger.warning(
                "Content sanitized - secrets detected",
                num_findings=len(sanitization_result.findings),
            )

        # Get recall instance
        instance = await self._get_recall_instance(scope, project_root)
        group_id = self._get_group_id(scope, project_root)

        # Generate episode name
        episode_name = f"cli_add_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Add episode to graph
            await instance.add_episode(
                name=episode_name,
                episode_body=sanitized_content,
                source_description=source,
                reference_time=datetime.now(),
                source=EpisodeType.text,
                group_id=group_id,
            )

            # Reactivation: if any archived entity was matched by this episode, remove it from archive_state
            try:
                from src.retention import get_retention_manager
                scope_key = self._get_group_id(scope, project_root)
                retention = get_retention_manager()
                archived_uuids = retention.get_archive_state_uuids(scope_key)
                if archived_uuids:
                    instance = await self._get_recall_instance(scope, project_root)
                    current_entities = await EntityNode.get_by_group_ids(
                        instance._driver, group_ids=[group_id]
                    )
                    for entity in current_entities:
                        if entity.uuid in archived_uuids:
                            retention.clear_archive(uuid=entity.uuid, scope=scope_key)
                            logger.info(
                                "retention_node_reactivated",
                                uuid=entity.uuid,
                                scope=scope_key,
                            )
            except Exception:
                logger.warning("retention_reactivation_check_failed", method="add")

            # Return success result
            # Note: instance.add_episode doesn't return created nodes/edges count
            # We'd need to query the graph to get accurate counts
            # For now, return placeholder values (will be improved in integration phase)
            return {
                "name": episode_name,
                "type": "episode",
                "scope": scope.value,
                "created_at": datetime.now().isoformat(),
                "tags": tags or [],
                "source": source,
                "content_length": len(sanitized_content),
                "nodes_created": 0,  # TODO: Query graph for actual count
                "edges_created": 0,  # TODO: Query graph for actual count
            }

        except Exception as e:
            logger.error(
                "Failed to add content to graph",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def search(
        self,
        query: str,
        scope: GraphScope,
        project_root: Optional[Path],
        exact: bool = False,
        limit: int = 15,
    ) -> list[dict]:
        """Search the knowledge graph.

        Args:
            query: Search query text
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)
            exact: If True, use exact string matching; if False, use semantic search
            limit: Maximum number of results

        Returns:
            List of result dicts with: name, type, snippet, score, created_at, scope, tags

        Raises:
            LLMUnavailableError: If semantic search fails due to LLM unavailability
        """
        logger.info(
            "Searching graph",
            scope=scope.value,
            query_length=len(query),
            exact=exact,
            limit=limit,
        )

        instance = await self._get_recall_instance(scope, project_root)
        group_id = self._get_group_id(scope, project_root)

        try:
            if exact:
                # TODO: Implement exact search via raw LadybugDB query
                # For now, fall back to semantic search
                logger.warning("Exact search not yet implemented, using semantic search")

            # Semantic search
            results = await instance.search(
                query=query,
                group_ids=[group_id],
                num_results=limit,
            )

            # Convert results to dict format
            result_list = []
            for edge in results:
                result_list.append(
                    {
                        "uuid": getattr(edge, "uuid", None),
                        "source_node_uuid": getattr(edge, "source_node_uuid", None),
                        "target_node_uuid": getattr(edge, "target_node_uuid", None),
                        "name": getattr(edge, "name", None)
                        or getattr(edge, "fact", "Unknown"),
                        "type": "relationship",
                        "snippet": getattr(edge, "fact", "")[:200],  # Truncate to 200 chars
                        "score": 0.0,  # instance.search doesn't return scores
                        "created_at": getattr(edge, "created_at", datetime.now()).isoformat()
                        if hasattr(edge, "created_at")
                        else datetime.now().isoformat(),
                        "scope": scope.value,
                        "tags": [],  # TODO: Extract from edge if available
                    }
                )

            logger.info("Search completed", num_results=len(result_list))

            # Post-filter archived nodes — archived entities are invisible in all outputs
            try:
                from src.retention import get_retention_manager
                scope_key = self._get_group_id(scope, project_root)
                archived_uuids = get_retention_manager().get_archive_state_uuids(scope_key)
                result_list = [
                    r for r in result_list
                    if not (
                        r.get("uuid") in archived_uuids
                        or r.get("source_node_uuid") in archived_uuids
                        or r.get("target_node_uuid") in archived_uuids
                    )
                ]
            except Exception:
                logger.warning("retention_filter_failed", method="search")

            return result_list

        except Exception as e:
            logger.error(
                "Search failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def list_entities(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        limit: Optional[int] = 50,
    ) -> list[dict]:
        """List entities in the knowledge graph.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)
            limit: Maximum number of entities to return

        Returns:
            List of entity dicts with: name, type, created_at, tags, scope, relationship_count
        """
        logger.info("Listing entities", scope=scope.value, limit=limit)

        try:
            # Get recall instance and group_id
            instance = await self._get_recall_instance(scope, project_root)
            group_id = self._get_group_id(scope, project_root)

            # Query entities from graph using EntityNode.get_by_group_ids()
            entities = await EntityNode.get_by_group_ids(
                instance.driver, group_ids=[group_id], limit=limit
            )

            # Convert EntityNode objects to dicts
            result_list = []
            for entity in entities:
                # Count relationships for this entity
                rel_records, _, _ = await instance.driver.execute_query(
                    """
                    MATCH (n:Entity {uuid: $uuid})-[:RELATES_TO]->(e:RelatesToNode_)
                    RETURN count(e) AS rel_count
                    """,
                    uuid=entity.uuid,
                )
                rel_count = rel_records[0]["rel_count"] if rel_records else 0

                result_list.append(
                    {
                        "uuid": entity.uuid,
                        "name": entity.name,
                        "type": "entity",
                        "created_at": entity.created_at.isoformat(),
                        "tags": entity.labels or [],
                        "scope": scope.value,
                        "relationship_count": rel_count,
                    }
                )

            logger.info("Listed entities", count=len(result_list))

            # Post-filter archived nodes — archived entities are invisible in all outputs
            try:
                from src.retention import get_retention_manager
                scope_key = self._get_group_id(scope, project_root)
                archived_uuids = get_retention_manager().get_archive_state_uuids(scope_key)
                result_list = [e for e in result_list if e.get("uuid") not in archived_uuids]
            except Exception:
                logger.warning("retention_filter_failed", method="list_entities")

            return result_list

        except Exception as e:
            logger.error(
                "Failed to list entities",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_entity(
        self,
        name: str,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict | list[dict] | None:
        """Get entity details by name.

        Args:
            name: Entity name to search for
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            - Single dict if one match found (with full details and relationships)
            - List of dicts if multiple matches (for disambiguation)
            - None if no matches found
        """
        logger.info("Getting entity", name=name, scope=scope.value)

        try:
            # Get recall instance and group_id
            instance = await self._get_recall_instance(scope, project_root)
            driver = instance.driver
            group_id = self._get_group_id(scope, project_root)

            # Query entities matching the name (case-insensitive partial match)
            records, _, _ = await driver.execute_query(
                """
                MATCH (n:Entity)
                WHERE n.group_id = $group_id AND lower(n.name) CONTAINS lower($name)
                RETURN
                    n.uuid AS uuid,
                    n.name AS name,
                    n.group_id AS group_id,
                    n.labels AS labels,
                    n.created_at AS created_at,
                    n.summary AS summary,
                    n.attributes AS attributes
                """,
                group_id=group_id,
                name=name,
            )

            if not records:
                return None

            # Build entity dicts with relationships
            entity_dicts = []
            for record in records:
                # Fetch outgoing relationships
                edge_records, _, _ = await driver.execute_query(
                    """
                    MATCH (n:Entity {uuid: $uuid})-[:RELATES_TO]->(e:RelatesToNode_)-[:RELATES_TO]->(m:Entity)
                    RETURN e.name AS name, e.fact AS fact, m.name AS target_name, e.created_at AS created_at
                    """,
                    uuid=record["uuid"],
                )

                # Fetch incoming relationships
                incoming_records, _, _ = await driver.execute_query(
                    """
                    MATCH (m:Entity)-[:RELATES_TO]->(e:RelatesToNode_)-[:RELATES_TO]->(n:Entity {uuid: $uuid})
                    RETURN e.name AS name, e.fact AS fact, m.name AS source_name, e.created_at AS created_at
                    """,
                    uuid=record["uuid"],
                )

                # Parse attributes
                attributes = (
                    json.loads(record["attributes"]) if record["attributes"] else {}
                )

                # Build relationships list
                relationships = [
                    {
                        "name": er["name"],
                        "fact": er["fact"],
                        "target": er["target_name"],
                        "created_at": str(er["created_at"]),
                    }
                    for er in edge_records
                ] + [
                    {
                        "name": er["name"],
                        "fact": er["fact"],
                        "source": er["source_name"],
                        "created_at": str(er["created_at"]),
                    }
                    for er in incoming_records
                ]

                # Build entity dict
                entity_dict = {
                    "uuid": record["uuid"],
                    "name": record["name"],
                    "type": "entity",
                    "created_at": (
                        record["created_at"].isoformat()
                        if hasattr(record["created_at"], "isoformat")
                        else str(record["created_at"])
                    ),
                    "tags": record["labels"] or [],
                    "scope": scope.value,
                    "summary": record["summary"] or "",
                    "attributes": attributes,
                    "relationships": relationships,
                }
                entity_dicts.append(entity_dict)

            # Record access for retention tracking (non-blocking)
            if entity_dicts:
                try:
                    from src.retention import get_retention_manager
                    scope_key = self._get_group_id(scope, project_root)
                    retention = get_retention_manager()
                    for ed in entity_dicts:
                        if ed.get("uuid"):
                            retention.record_access(uuid=ed["uuid"], scope=scope_key)
                except Exception:
                    logger.warning("retention_access_recording_failed", method="get_entity")

            # Return single dict, list, or None based on match count
            if len(entity_dicts) == 1:
                return entity_dicts[0]
            elif len(entity_dicts) > 1:
                return entity_dicts
            else:
                return None

        except Exception as e:
            logger.error(
                "Failed to get entity",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def delete_entities(
        self,
        names: list[str],
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> int:
        """Delete entities by name.

        Args:
            names: List of entity names to delete
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Count of deleted entities
        """
        logger.info("Deleting entities", names=names, scope=scope.value)

        try:
            # Get recall instance and group_id
            instance = await self._get_recall_instance(scope, project_root)
            driver = instance.driver
            group_id = self._get_group_id(scope, project_root)

            # Find UUIDs of entities to delete by matching names
            uuids_to_delete = []
            for name in names:
                records, _, _ = await driver.execute_query(
                    """
                    MATCH (n:Entity)
                    WHERE n.group_id = $group_id AND lower(n.name) = lower($name)
                    RETURN n.uuid AS uuid
                    """,
                    group_id=group_id,
                    name=name,
                )
                uuids_to_delete.extend([r["uuid"] for r in records])

            if not uuids_to_delete:
                logger.info("No entities found to delete")
                return 0

            # Delete using graphiti_core's API (handles LadybugDB-specific deletion)
            await Node.delete_by_uuids(driver, uuids_to_delete)

            logger.info("Deleted entities", count=len(uuids_to_delete))
            return len(uuids_to_delete)

        except Exception as e:
            logger.error(
                "Failed to delete entities",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def summarize(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        topic: Optional[str] = None,
    ) -> tuple[str, int]:
        """Generate a summary of the knowledge graph.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)
            topic: Optional topic filter

        Returns:
            Tuple of (summary_text, entity_count)

        Raises:
            LLMUnavailableError: If LLM is unavailable for summarization
        """
        logger.info("Generating summary", scope=scope.value, topic=topic)

        # Get recall instance and group_id
        instance = await self._get_recall_instance(scope, project_root)
        group_id = self._get_group_id(scope, project_root)

        # Load entities using EntityNode.get_by_group_ids
        entities = await EntityNode.get_by_group_ids(
            instance.driver, group_ids=[group_id], limit=200
        )

        if not entities:
            return ("No entities found in the knowledge graph.", 0)

        # Filter by topic if provided
        if topic:
            filtered = [
                e
                for e in entities
                if topic.lower() in e.name.lower()
                or (e.summary and topic.lower() in e.summary.lower())
            ]
            if filtered:
                entities = filtered
            # If no matches for topic filter, use all entities but note it in the prompt

        # Build LLM prompt from entity data
        entity_descriptions = []
        for e in entities[:100]:  # Cap at 100 entities for LLM context
            desc = f"- {e.name}"
            if e.summary:
                desc += f": {e.summary}"
            if e.labels:
                desc += f" (labels: {', '.join(e.labels)})"
            entity_descriptions.append(desc)

        entity_text = "\n".join(entity_descriptions)

        topic_clause = f" focusing on '{topic}'" if topic else ""
        prompt = (
            f"Summarize the following knowledge graph entities{topic_clause}. "
            f"Provide a concise, readable overview of what knowledge is stored. "
            f"Focus on key themes, relationships between concepts, and notable patterns.\n\n"
            f"Entities ({len(entities)} total):\n{entity_text}"
        )

        # Call ollama_chat via run_in_executor (since ollama_chat is sync and we're in async context)
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama_chat(messages=[{"role": "user", "content": prompt}]),
            )
            summary_text = response["message"]["content"]
            return (summary_text, len(entities))

        except LLMUnavailableError:
            # Fall back to a non-LLM summary
            entity_names = [e.name for e in entities[:20]]
            fallback = f"Knowledge graph contains {len(entities)} entities"
            if topic:
                fallback += f" (filtered by '{topic}')"
            fallback += f". Key entities: {', '.join(entity_names)}"
            if len(entities) > 20:
                fallback += f"... and {len(entities) - 20} more"
            return (fallback, len(entities))

    async def compact(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict:
        """Compact the knowledge graph by removing duplicates.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Dict with: merged_count, removed_count, new_entity_count, new_size_bytes
        """
        logger.info("Compacting graph", scope=scope.value)

        try:
            # Get recall instance, driver, and group_id
            instance = await self._get_recall_instance(scope, project_root)
            driver = instance.driver
            group_id = self._get_group_id(scope, project_root)

            # Load all entities
            entities = await EntityNode.get_by_group_ids(
                driver, group_ids=[group_id], limit=1000
            )
            original_count = len(entities)

            # Early return if no entities or only one entity
            if len(entities) <= 1:
                return {
                    "merged_count": 0,
                    "removed_count": 0,
                    "new_entity_count": original_count,
                    "new_size_bytes": 0,
                }

            # Find duplicates by grouping entities with identical lowercased names
            name_groups: dict[str, list] = defaultdict(list)
            for entity in entities:
                name_groups[entity.name.lower().strip()].append(entity)

            # Groups with more than 1 entity are duplicates
            duplicate_groups = {k: v for k, v in name_groups.items() if len(v) > 1}

            # For each duplicate group, keep the entity with the most information
            removed_count = 0
            merged_count = 0
            for name_key, group in duplicate_groups.items():
                # Sort by summary length descending - keep the most complete entity
                group.sort(key=lambda e: len(e.summary or ""), reverse=True)
                keep = group[0]  # Entity with most information
                to_remove = group[1:]  # Duplicates to delete

                if to_remove:
                    # Delete duplicate entity nodes
                    uuids_to_remove = [e.uuid for e in to_remove]
                    await Node.delete_by_uuids(driver, uuids_to_remove)
                    removed_count += len(to_remove)
                    merged_count += 1

            # Get new entity count after compaction
            remaining = await EntityNode.get_by_group_ids(driver, group_ids=[group_id])
            new_entity_count = len(remaining)

            # Get database size
            size_bytes = self._get_db_size(scope, project_root, driver)

            logger.info(
                "Compaction complete",
                merged_count=merged_count,
                removed_count=removed_count,
                new_count=new_entity_count,
            )

            return {
                "merged_count": merged_count,
                "removed_count": removed_count,
                "new_entity_count": new_entity_count,
                "new_size_bytes": size_bytes,
            }

        except Exception as e:
            logger.error(
                "Failed to compact graph",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def list_stale(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> list[dict]:
        """List entities that are stale (older than retention_days, not pinned, not archived).

        Fetches all entities for the scope, applies retention filters, computes staleness
        scores, and returns the stale candidates sorted ascending by score (most stale first).

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            List of dicts with: uuid, name, age_days, score — sorted ascending by score.
            Caller (CLI) applies display caps. Always returns full list.
        """
        from datetime import timezone as _tz

        from src.retention import get_retention_manager

        instance = await self._get_recall_instance(scope, project_root)
        group_id = self._get_group_id(scope, project_root)
        scope_key = group_id

        config = load_config()
        retention_days = config.retention_days

        retention = get_retention_manager()

        # Batch reads — two calls total, not N+1
        archived_uuids = retention.get_archive_state_uuids(scope_key)
        pinned_uuids = retention.get_pin_state_uuids(scope_key)

        entities = await EntityNode.get_by_group_ids(
            instance.driver, group_ids=[group_id]
        )

        now = datetime.now(_tz.utc)
        result_list = []
        for entity in entities:
            # Skip archived or pinned
            if entity.uuid in archived_uuids or entity.uuid in pinned_uuids:
                continue

            # Normalize timezone-naive created_at
            created_at = entity.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=_tz.utc)

            age_days = (now - created_at).total_seconds() / 86400.0

            # Only include nodes older than retention_days
            if age_days <= retention_days:
                continue

            access_record = retention.get_access_record(uuid=entity.uuid, scope=scope_key)
            last_accessed_at = access_record["last_accessed_at"]
            access_count = access_record["access_count"]

            from src.retention.manager import RetentionManager
            score = RetentionManager.compute_score(
                created_at=created_at,
                last_accessed_at=last_accessed_at,
                access_count=access_count,
                retention_days=retention_days,
            )

            result_list.append(
                {
                    "uuid": entity.uuid,
                    "name": entity.name,
                    "age_days": round(age_days, 1),
                    "score": score,
                }
            )

        # Sort ascending by score — lowest score = most stale = first
        result_list.sort(key=lambda x: x["score"])
        return result_list

    async def archive_nodes(
        self,
        uuids: list[str],
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> int:
        """Archive nodes in retention.db (SQLite-only — LadybugDB graph is untouched).

        Args:
            uuids: List of entity UUIDs to archive
            scope: Graph scope
            project_root: Project root path

        Returns:
            Count of nodes archived
        """
        from src.retention import get_retention_manager

        scope_key = self._get_group_id(scope, project_root)
        retention = get_retention_manager()

        for uuid in uuids:
            retention.archive_node(uuid=uuid, scope=scope_key)

        return len(uuids)

    async def record_access(
        self,
        uuid: str,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> None:
        """Record an access event for a node in the retention database.

        Failure is always silenced — access recording must not affect the caller.

        Args:
            uuid: Entity UUID that was accessed
            scope: Graph scope
            project_root: Project root path
        """
        try:
            from src.retention import get_retention_manager
            scope_key = self._get_group_id(scope, project_root)
            get_retention_manager().record_access(uuid=uuid, scope=scope_key)
        except Exception:
            logger.warning("retention_access_recording_failed", method="record_access")

    async def get_stats(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict:
        """Get knowledge graph statistics.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Dict with: entity_count, relationship_count, episode_count, duplicate_count, size_bytes
        """
        logger.info("Getting graph stats", scope=scope.value)

        try:
            # Get recall instance and group_id
            instance = await self._get_recall_instance(scope, project_root)
            driver = instance.driver
            group_id = self._get_group_id(scope, project_root)

            # Count entities
            entity_records, _, _ = await driver.execute_query(
                """
                MATCH (n:Entity)
                WHERE n.group_id = $group_id
                RETURN count(n) AS cnt
                """,
                group_id=group_id,
            )
            entity_count = entity_records[0]["cnt"] if entity_records else 0

            # Count relationships (RelatesToNode_ nodes represent edges in LadybugDB)
            rel_records, _, _ = await driver.execute_query(
                """
                MATCH (n:Entity)-[:RELATES_TO]->(e:RelatesToNode_)-[:RELATES_TO]->(m:Entity)
                WHERE e.group_id = $group_id
                RETURN count(e) AS cnt
                """,
                group_id=group_id,
            )
            relationship_count = rel_records[0]["cnt"] if rel_records else 0

            # Count episodes
            ep_records, _, _ = await driver.execute_query(
                """
                MATCH (e:Episodic)
                WHERE e.group_id = $group_id
                RETURN count(e) AS cnt
                """,
                group_id=group_id,
            )
            episode_count = ep_records[0]["cnt"] if ep_records else 0

            # Calculate database size
            size_bytes = self._get_db_size(scope, project_root, driver)

            return {
                "entity_count": entity_count,
                "relationship_count": relationship_count,
                "episode_count": episode_count,
                "duplicate_count": 0,  # Duplicate detection is handled by compact()
                "size_bytes": size_bytes,
            }

        except Exception as e:
            logger.error(
                "Failed to get graph stats",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return zeros dict on failure (stats should be best-effort)
            return {
                "entity_count": 0,
                "relationship_count": 0,
                "episode_count": 0,
                "duplicate_count": 0,
                "size_bytes": 0,
            }

    async def list_edges(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> list[dict]:
        """List all relationship edges for the given scope.

        Returns edges as dicts with source, target, label, fact keys.
        Uses driver.execute_query() — backend-agnostic (no direct ladybugdb calls).
        """
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return []

        try:
            driver = self._graph_manager.get_driver(scope, project_root)
            group_id = self._get_group_id(scope, project_root)

            query = """
                MATCH (a:Entity {group_id: $group_id})-[:RELATES_TO]->(rel:RelatesToNode_)-[:RELATES_TO]->(b:Entity {group_id: $group_id})
                RETURN a.uuid AS source, b.uuid AS target, rel.name AS label, rel.fact AS fact
                LIMIT 5000
            """
            results, _, _ = await driver.execute_query(query, group_id=group_id)
            edges = []
            for row in results:
                edges.append({
                    "source": row["source"],
                    "target": row["target"],
                    "label": row["label"] or "RELATES_TO",
                    "fact": row["fact"] or "",
                })
            return edges
        except Exception as e:
            logger.warning("list_edges failed", error=str(e), scope=str(scope))
            return []

    async def list_entities_readonly(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        limit: Optional[int] = None,
    ) -> list[dict]:
        """List all entity nodes for the given scope.

        Identical shape to list_entities() output but NEVER calls _get_recall_instance().
        Returns list of dicts with: uuid, name, tags, scope, summary, created_at, last_accessed_at.
        Uses driver.execute_query() — backend-agnostic (no direct ladybugdb calls).
        """
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return []

        try:
            driver = self._graph_manager.get_driver(scope, project_root)
            group_id = self._get_group_id(scope, project_root)

            limit_clause = f"LIMIT {limit}" if limit else ""
            query = f"""
                MATCH (e:Entity {{group_id: $group_id}})
                RETURN e.uuid AS uuid, e.name AS name, e.labels AS tags,
                       e.summary AS summary, e.created_at AS created_at
                {limit_clause}
            """
            results, _, _ = await driver.execute_query(query, group_id=group_id)
            entities = []
            scope_str = "global" if scope == GraphScope.GLOBAL else "project"
            for row in results:
                entities.append({
                    "uuid": row["uuid"],
                    "name": row["name"],
                    "tags": row["tags"] if isinstance(row["tags"], list) else [row["tags"]] if row["tags"] else ["Entity"],
                    "scope": scope_str,
                    "summary": row["summary"] or "",
                    "created_at": row["created_at"],
                    "last_accessed_at": None,
                    "access_count": 0,
                    "pinned": False,
                })

            # Apply retention status — compute per-entity classification
            try:
                retention = get_retention_manager()
                archived_uuids = retention.get_archive_state_uuids(group_id)
                pinned_uuids = retention.get_pin_state_uuids(group_id)
                _cfg = load_config()
                _retention_days = _cfg.retention_days
                from datetime import timezone as _tz
                _now = datetime.now(_tz.utc)
                for e in entities:
                    uuid = e.get("uuid", "")
                    if uuid in pinned_uuids:
                        e["retention_status"] = "Pinned"
                    elif uuid in archived_uuids:
                        e["retention_status"] = "Archived"
                    else:
                        # Stale: older than retention_days?
                        created_str = e.get("created_at")
                        is_stale = False
                        if created_str:
                            try:
                                created_dt = datetime.fromisoformat(str(created_str))
                                if created_dt.tzinfo is None:
                                    created_dt = created_dt.replace(tzinfo=_tz.utc)
                                age_days = (_now - created_dt).total_seconds() / 86400.0
                                if age_days > _retention_days:
                                    is_stale = True
                            except (ValueError, TypeError):
                                pass
                        e["retention_status"] = "Stale" if is_stale else "Normal"
                    e["pinned"] = uuid in pinned_uuids
            except Exception:
                for e in entities:
                    e.setdefault("retention_status", "Normal")

            return entities
        except Exception as e:
            logger.warning("list_entities_readonly failed", error=str(e), scope=str(scope))
            return []

    async def get_entity_by_uuid(
        self,
        uuid: str,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict | None:
        """Fetch a single entity node by UUID.

        Does NOT call _get_recall_instance(). Returns None if not found.
        Uses driver.execute_query() — backend-agnostic (no direct ladybugdb calls).
        """
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return None

        try:
            driver = self.graph_manager.get_driver(scope, project_root)

            query = """
                MATCH (e:Entity {uuid: $uuid})
                RETURN e.uuid AS uuid, e.name AS name, e.labels AS tags,
                       e.summary AS summary, e.created_at AS created_at
            """
            results, _, _ = await driver.execute_query(query, uuid=uuid)
            if results:
                row = results[0]
                return {
                    "uuid": row["uuid"],
                    "name": row["name"],
                    "tags": row["tags"] if isinstance(row["tags"], list) else [row["tags"]] if row["tags"] else ["Entity"],
                    "summary": row["summary"] or "",
                    "created_at": row["created_at"],
                    "last_accessed_at": None,
                    "access_count": 0,
                    "pinned": False,
                }
            return None
        except Exception as e:
            logger.warning("get_entity_by_uuid failed", error=str(e), uuid=uuid)
            return None

    async def list_episodes(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        limit: int = 50,
    ) -> list[dict]:
        """List episode (Episodic) nodes. Never calls _get_recall_instance().

        Returns list of dicts with: uuid, name, source_description, content,
        created_at, source. Sorted newest-first.
        """
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return []
        try:
            driver = self._graph_manager.get_driver(scope, project_root)
            group_id = self._get_group_id(scope, project_root)
            results, _, _ = await driver.execute_query(
                """
                MATCH (e:Episodic)
                WHERE e.group_id = $group_id
                RETURN e.uuid AS uuid, e.name AS name,
                       e.source_description AS source_description,
                       e.content AS content, e.created_at AS created_at,
                       e.source AS source
                ORDER BY e.created_at DESC
                LIMIT $limit
                """,
                group_id=group_id,
                limit=limit,
            )
            return [
                {
                    "uuid": row["uuid"],
                    "name": row["name"] or "",
                    "source_description": row["source_description"] or "",
                    "content": row["content"] or "",
                    "created_at": str(row["created_at"] or ""),
                    "source": str(row["source"] or ""),
                }
                for row in results
            ]
        except Exception as e:
            logger.warning("list_episodes failed", error=str(e), scope=str(scope))
            return []

    async def get_episode_detail(
        self,
        uuid: str,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict | None:
        """Fetch a single Episodic node with its entity mentions. Never calls _get_recall_instance()."""
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return None
        try:
            driver = self._graph_manager.get_driver(scope, project_root)
            # Episode base record
            results, _, _ = await driver.execute_query(
                """
                MATCH (e:Episodic {uuid: $uuid})
                RETURN e.uuid AS uuid, e.name AS name,
                       e.source_description AS source_description,
                       e.content AS content, e.created_at AS created_at,
                       e.source AS source
                """,
                uuid=uuid,
            )
            if not results:
                return None
            row = results[0]
            episode = {
                "uuid": row["uuid"],
                "name": row["name"] or "",
                "source_description": row["source_description"] or "",
                "content": row["content"] or "",
                "created_at": str(row["created_at"] or ""),
                "source": str(row["source"] or ""),
                "entities": [],
            }
            # Fetch entity mentions via MENTIONS edges
            try:
                mention_results, _, _ = await driver.execute_query(
                    """
                    MATCH (ep:Episodic {uuid: $uuid})-[:MENTIONS]->(e:Entity)
                    RETURN e.uuid AS uuid, e.name AS name, e.labels AS tags
                    """,
                    uuid=uuid,
                )
                episode["entities"] = [
                    {"uuid": r["uuid"], "name": r["name"] or "", "tags": r["tags"] or []}
                    for r in mention_results
                ]
            except Exception:
                pass  # MENTIONS edges may not exist for all episodes
            return episode
        except Exception as e:
            logger.warning("get_episode_detail failed", error=str(e), uuid=uuid)
            return None

    async def get_time_series_counts(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        days: int = 30,
    ) -> list[dict]:
        """Return daily counts of entities, edges, and episodes over `days` window.

        Returns list of dicts: [{day: "YYYY-MM-DD", entity_count: N, edge_count: N, episode_count: N}]
        sorted oldest-first. Never calls _get_recall_instance().

        Note: LadybugDB date() function support is unverified — aggregates at Python level
        from raw created_at timestamps as a fallback.
        """
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return []
        try:
            driver = self._graph_manager.get_driver(scope, project_root)
            group_id = self._get_group_id(scope, project_root)
            from datetime import timedelta
            since = (datetime.now() - timedelta(days=days)).isoformat()

            # Fetch raw created_at for entities
            entity_results, _, _ = await driver.execute_query(
                "MATCH (e:Entity) WHERE e.group_id = $group_id AND e.created_at >= $since RETURN e.created_at AS ts",
                group_id=group_id, since=since,
            )
            edge_results, _, _ = await driver.execute_query(
                """MATCH (a:Entity {group_id: $group_id})-[:RELATES_TO]->(rel:RelatesToNode_)
                   WHERE rel.created_at >= $since RETURN rel.created_at AS ts""",
                group_id=group_id, since=since,
            )
            ep_results, _, _ = await driver.execute_query(
                "MATCH (e:Episodic) WHERE e.group_id = $group_id AND e.created_at >= $since RETURN e.created_at AS ts",
                group_id=group_id, since=since,
            )

            # Aggregate by day in Python
            entity_by_day: dict = defaultdict(int)
            edge_by_day: dict = defaultdict(int)
            ep_by_day: dict = defaultdict(int)

            def _day(ts) -> str:
                if ts is None:
                    return ""
                s = str(ts)
                return s[:10] if len(s) >= 10 else s

            for row in entity_results:
                d = _day(row["ts"])
                if d:
                    entity_by_day[d] += 1
            for row in edge_results:
                d = _day(row["ts"])
                if d:
                    edge_by_day[d] += 1
            for row in ep_results:
                d = _day(row["ts"])
                if d:
                    ep_by_day[d] += 1

            all_days = sorted(set(entity_by_day) | set(edge_by_day) | set(ep_by_day))
            return [
                {
                    "day": d,
                    "entity_count": entity_by_day[d],
                    "edge_count": edge_by_day[d],
                    "episode_count": ep_by_day[d],
                }
                for d in all_days
            ]
        except Exception as e:
            logger.warning("get_time_series_counts failed", error=str(e), scope=str(scope))
            return []

    async def get_top_connected_entities(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        limit: int = 10,
    ) -> list[dict]:
        """Return top N entities ranked by edge count. Never calls _get_recall_instance().

        Returns list of dicts: [{uuid, name, edge_count}] sorted descending.
        """
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return []
        try:
            driver = self._graph_manager.get_driver(scope, project_root)
            group_id = self._get_group_id(scope, project_root)
            results, _, _ = await driver.execute_query(
                """
                MATCH (a:Entity {group_id: $group_id})-[:RELATES_TO]->(rel:RelatesToNode_)
                RETURN a.uuid AS uuid, a.name AS name, count(rel) AS edge_count
                ORDER BY edge_count DESC
                LIMIT $limit
                """,
                group_id=group_id,
                limit=limit,
            )
            return [
                {"uuid": row["uuid"], "name": row["name"] or "", "edge_count": int(row["edge_count"] or 0)}
                for row in results
            ]
        except Exception as e:
            logger.warning("get_top_connected_entities failed", error=str(e), scope=str(scope))
            return []

    async def get_retention_summary(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict:
        """Return retention status counts for entities. Never calls _get_recall_instance().

        Returns dict: {pinned: N, normal: N, stale: N, archived: N}
        Uses retention manager for pin/stale/archive state; entity count from driver.
        """
        db_path = self._resolve_db_path(scope, project_root)
        if not db_path or not db_path.exists():
            return {"pinned": 0, "normal": 0, "stale": 0, "archived": 0}
        try:
            driver = self._graph_manager.get_driver(scope, project_root)
            group_id = self._get_group_id(scope, project_root)

            # Total entity count
            results, _, _ = await driver.execute_query(
                "MATCH (e:Entity) WHERE e.group_id = $group_id RETURN e.uuid AS uuid",
                group_id=group_id,
            )
            all_uuids = {row["uuid"] for row in results}
            total = len(all_uuids)

            # Retention state from manager
            pinned_count = 0
            stale_count = 0
            archived_count = 0
            try:
                from src.retention import get_retention_manager
                retention = get_retention_manager()
                pinned_uuids = retention.get_pin_state_uuids(group_id)
                archived_uuids = retention.get_archive_state_uuids(group_id)
                stale_uuids = set(retention.get_stale_uuids(group_id)) if hasattr(retention, "get_stale_uuids") else set()
                pinned_count = len(pinned_uuids & all_uuids)
                archived_count = len(archived_uuids & all_uuids)
                stale_count = len(stale_uuids & all_uuids)
            except Exception:
                pass

            normal_count = total - pinned_count - stale_count - archived_count
            return {
                "pinned": pinned_count,
                "normal": max(0, normal_count),
                "stale": stale_count,
                "archived": archived_count,
            }
        except Exception as e:
            logger.warning("get_retention_summary failed", error=str(e), scope=str(scope))
            return {"pinned": 0, "normal": 0, "stale": 0, "archived": 0}
