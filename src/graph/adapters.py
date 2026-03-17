"""Adapters that bridge our Ollama client to graphiti_core interfaces.

OllamaLLMClient adapts our src.llm.chat() to graphiti_core's LLMClient ABC.
OllamaEmbedder adapts our src.llm.embed() to graphiti_core's EmbedderClient ABC.

Both adapters handle the async/sync bridge since graphiti_core is async
but our OllamaClient is synchronous.
"""

import asyncio
import json
import re
import structlog
from typing import Any, Iterable

from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import LLMConfig as GraphitiLLMConfig, ModelSize
from graphiti_core.prompts.models import Message
from pydantic import BaseModel

from src.llm import chat as ollama_chat, embed as ollama_embed

logger = structlog.get_logger(__name__)


class NoOpCrossEncoder(CrossEncoderClient):
    """No-op cross encoder that returns passages with descending scores.

    Used when no reranking service is available (e.g., local Ollama setup
    without OpenAI). Passages are returned in their original order with
    linearly decreasing scores.
    """

    async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]:
        """Return passages in original order with descending scores."""
        n = len(passages)
        return [(p, 1.0 - i / max(n, 1)) for i, p in enumerate(passages)]


class OllamaLLMClient(LLMClient):
    """Adapter that routes graphiti_core LLM calls through our OllamaClient.

    This adapter implements graphiti_core's abstract LLMClient interface,
    routing all requests through our src.llm module which handles:
    - Cloud/local failover
    - Rate limiting and cooldowns
    - Request queuing on failures
    - Quota tracking

    The adapter bridges the async/sync gap: graphiti_core is async,
    our OllamaClient is sync (makes blocking HTTP calls).
    """

    def __init__(self):
        """Initialize OllamaLLMClient.

        Creates a minimal GraphitiLLMConfig with model=None since we route
        through our own client which manages model selection.
        """
        # Create minimal config - we don't use graphiti's model selection
        config = GraphitiLLMConfig(model=None)
        super().__init__(config)
        logger.debug("OllamaLLMClient initialized")

    def _strip_schema_suffix(self, message_dicts: list[dict]) -> list[dict]:
        """Strip embedded JSON schema from the last user/system message.

        graphiti-core appends a JSON schema to prompt messages in this form:
            "Respond with a JSON object in the following format:\n\n{...schema...}"

        When using Ollama's format= parameter (constrained generation), the schema
        in the prompt is redundant: the format= parameter already constrains output.
        Removing it shortens the prompt significantly and speeds up inference.
        """
        if not message_dicts:
            return message_dicts

        result = list(message_dicts)
        for i in range(len(result) - 1, -1, -1):
            msg = result[i]
            if msg.get("role") in ("user", "system"):
                content = msg.get("content", "")
                stripped = re.sub(
                    r"\s*Respond with a JSON object in the following format:\s*\n\s*\{.*$",
                    "",
                    content,
                    flags=re.DOTALL,
                )
                if stripped != content:
                    result[i] = {**msg, "content": stripped.rstrip()}
                    break
        return result

    def _schema_to_example(self, schema: dict) -> Any:
        """Recursively build a minimal concrete example value from a JSON schema.

        Resolves $ref references against $defs. Returns the smallest valid
        instance of each type so the injected example stays compact.
        """
        defs = schema.get("$defs", {})
        return self._resolve_node(schema, defs)

    def _resolve_node(self, node: dict, defs: dict) -> Any:
        """Resolve one schema node to a concrete example value."""
        if "$ref" in node:
            ref_name = node["$ref"].split("/")[-1]
            return self._resolve_node(defs.get(ref_name, {}), defs)

        type_ = node.get("type")

        if type_ == "object":
            return {
                k: self._resolve_node(v, defs)
                for k, v in node.get("properties", {}).items()
            }
        if type_ == "array":
            item = self._resolve_node(node.get("items", {}), defs)
            return [item]
        if type_ == "string":
            return "example"
        if type_ == "integer":
            return 0
        if type_ == "number":
            return 0.0
        if type_ == "boolean":
            return True
        return None

    @staticmethod
    def _normalize_field_names(data: Any) -> Any:
        """Recursively strip leading dots from dict keys in LLM JSON output.

        Some cloud models mirror dot-prefixed filenames from content into
        field names, producing {".name": "value"} instead of {"name": "value"}.
        This normalizes keys before Pydantic validation to prevent spurious
        'Field required' errors.

        Args:
            data: Parsed JSON value (dict, list, or scalar)

        Returns:
            Same structure with leading dots stripped from all dict keys
        """
        if isinstance(data, dict):
            return {
                k.lstrip("."): OllamaLLMClient._normalize_field_names(v)
                for k, v in data.items()
            }
        if isinstance(data, list):
            return [OllamaLLMClient._normalize_field_names(item) for item in data]
        return data

    def _inject_example(
        self, message_dicts: list[dict], response_model: type[BaseModel]
    ) -> list[dict]:
        """Append a concrete one-line JSON example to the last user/system message.

        Cloud models that ignore the format= schema constraint can use this as a
        concrete template to copy, reducing field-name mismatches. Local models
        with grammar-based constrained generation ignore the extra text.

        The example is appended AFTER _strip_schema_suffix() so the verbose
        schema block is replaced by a compact single-line concrete instance.
        """
        example = self._schema_to_example(response_model.model_json_schema())
        suffix = f"\n\nExample output: {json.dumps(example, separators=(',', ':'))}"

        result = list(message_dicts)
        for i in range(len(result) - 1, -1, -1):
            msg = result[i]
            if msg.get("role") in ("user", "system"):
                result[i] = {**msg, "content": msg.get("content", "") + suffix}
                break
        return result

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = 8192,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        """Generate response from messages via our Ollama client.

        Args:
            messages: List of Message objects with role and content
            response_model: Optional Pydantic model for structured output
            max_tokens: Maximum tokens in response (unused - our client manages)
            model_size: Model size hint (unused - our client manages)

        Returns:
            Dict with response content or parsed model dict

        Raises:
            Exception: If LLM call fails (propagates from our client)
        """
        # Convert Message objects to dicts for our client
        message_dicts = [{"role": m.role, "content": m.content} for m in messages]

        logger.debug(
            "Generating response",
            num_messages=len(message_dicts),
            has_response_model=response_model is not None,
        )

        try:
            # When a response model is provided, pass its JSON schema as the Ollama
            # `format` parameter to enable grammar-based constrained generation.
            # This forces the model to emit valid JSON matching the schema rather
            # than echoing the schema back or wrapping it in prose/code fences.
            call_kwargs: dict[str, Any] = {}
            if response_model is not None:
                call_kwargs["format"] = response_model.model_json_schema()
                # graphiti-core appends the full JSON schema to prompts like:
                #   "Respond with a JSON object in the following format:\n\n{...schema...}"
                # With format= (constrained generation), this schema is redundant and
                # makes prompts much longer, slowing constrained sampling significantly.
                # Strip it so the model only processes the semantic instruction.
                message_dicts = self._strip_schema_suffix(message_dicts)
                # Append a compact concrete example so cloud models that ignore
                # format= still have a template with exact field names to copy.
                message_dicts = self._inject_example(message_dicts, response_model)

            # Call our sync ollama_chat in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama_chat(messages=message_dicts, **call_kwargs),
            )

            # Extract response content
            response_text = response["message"]["content"]

            # If response_model provided, parse as JSON and validate
            if response_model is not None:
                try:
                    # Strip markdown code fences if present (safety net for non-constrained paths)
                    clean_text = response_text.strip()
                    if clean_text.startswith("```"):
                        clean_text = re.sub(r'^```(?:json)?\s*\n?', '', clean_text)
                        clean_text = re.sub(r'\n?```\s*$', '', clean_text).strip()
                    # Try to parse the response as JSON
                    parsed_data = json.loads(clean_text)
                    # Normalize dot-prefixed keys before any validation (cloud models
                    # sometimes mirror filenames like ".env" into field names,
                    # producing {".name": "value"} instead of {"name": "value"})
                    parsed_data = self._normalize_field_names(parsed_data)
                    # Some cloud models return a bare list instead of the expected wrapped
                    # object, even when format= is set. Try wrapping the list under each
                    # list-typed field in the model and return the first that validates.
                    # This avoids blindly picking the first field when multiple list fields
                    # exist, and avoids silently accepting a wrong-field wrap.
                    if isinstance(parsed_data, list):
                        for field_name, field_info in response_model.model_fields.items():
                            origin = getattr(field_info.annotation, '__origin__', None)
                            if origin is list:
                                try:
                                    validated = response_model.model_validate(
                                        {field_name: parsed_data}
                                    )
                                    logger.debug(
                                        "bare_list_normalised",
                                        field=field_name,
                                        model=response_model.__name__,
                                    )
                                    return validated.model_dump()
                                except (ValueError, Exception):
                                    continue
                        # No list field accepted the bare list — let the fallback handle it
                        raise ValueError(
                            f"Bare list response did not match any list field "
                            f"in {response_model.__name__}"
                        )
                    # Validate against the model
                    validated = response_model.model_validate(parsed_data)
                    # Return as dict
                    return validated.model_dump()
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        "Failed to parse response as structured output",
                        error=str(e),
                        response_preview=response_text[:200],
                    )
                    # Fall back to returning content as-is
                    return {"content": response_text}

            # No response model - return plain content
            return {"content": response_text}

        except Exception as e:
            logger.error(
                "Failed to generate response",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class OllamaEmbedder(EmbedderClient):
    """Adapter that routes graphiti_core embedding calls through our Ollama client.

    This adapter implements graphiti_core's abstract EmbedderClient interface,
    routing all embedding requests through our src.llm.embed() function which
    handles cloud/local failover automatically.
    """

    def __init__(self):
        """Initialize OllamaEmbedder."""
        super().__init__()
        logger.debug("OllamaEmbedder initialized")


    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        """Create embeddings for a batch of strings.

        graphiti-core calls this when embedding multiple nodes at once.
        Delegates to create() for each item since our Ollama client is per-request.
        """
        results = []
        for text in input_data_list:
            embedding = await self.create(text)
            results.append(embedding)
        return results

    async def create(
        self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    ) -> list[float]:
        """Create embeddings for input data via our Ollama client.

        Args:
            input_data: Text string, list of strings, or token IDs to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            Exception: If embedding call fails (propagates from our client)

        Note:
            graphiti_core typically calls this with single strings for node/edge
            embeddings. If a list is provided, we embed the first item.
        """
        # Handle different input types
        if isinstance(input_data, str):
            text_to_embed = input_data
        elif isinstance(input_data, list) and len(input_data) > 0:
            # If list of strings, embed the first one
            # graphiti_core typically passes single strings
            text_to_embed = str(input_data[0])
        else:
            # Handle edge cases (empty list, iterables, etc.)
            logger.warning(
                "Unexpected input_data type, converting to string",
                input_type=type(input_data),
            )
            text_to_embed = str(input_data)

        logger.debug(
            "Creating embedding",
            text_length=len(text_to_embed),
        )

        try:
            # Call our sync embed in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama_embed(input=text_to_embed),
            )

            # Extract embedding from response
            # Our embed() returns: {"embeddings": [[float, float, ...]]}
            embeddings = response.get("embeddings", [])
            if not embeddings or len(embeddings) == 0:
                raise ValueError("No embeddings returned from Ollama")

            # Return first embedding vector
            embedding_vector = embeddings[0]
            logger.debug("Embedding created", vector_length=len(embedding_vector))

            return embedding_vector

        except Exception as e:
            logger.error(
                "Failed to create embedding",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


# ---------------------------------------------------------------------------
# Phase 13: Adapter factories — select correct client based on LLMConfig
# ---------------------------------------------------------------------------


def make_llm_client(config):
    """Return the appropriate graphiti-core LLMClient based on config.

    When [llm] section present and primary URL is openai-compatible:
        → OpenAIGenericClient (graphiti-core's built-in openai adapter)
    When [llm] section present and primary URL is Ollama (localhost):
        → OllamaLLMClient (existing adapter — Ollama SDK)
    When [llm] absent (legacy mode):
        → OllamaLLMClient (existing path, no change)

    Args:
        config: LLMConfig instance (from load_config())

    Returns:
        An instance implementing graphiti_core.llm_client.client.LLMClient
    """
    from src.llm.provider import _detect_sdk

    if config.llm_mode == "provider":
        primary_sdk = _detect_sdk(config.llm_primary_url or "")
        if primary_sdk == "openai":
            from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
            from graphiti_core.llm_client.config import LLMConfig as GraphitiLLMConfig
            graphiti_cfg = GraphitiLLMConfig(
                api_key=config.llm_primary_api_key,
                base_url=config.llm_primary_url,
                model=config.llm_primary_models[0] if config.llm_primary_models else "gpt-4o-mini",
            )
            logger.debug(
                "make_llm_client: using OpenAIGenericClient",
                base_url=config.llm_primary_url,
                model=graphiti_cfg.model,
            )
            return OpenAIGenericClient(config=graphiti_cfg)
        else:
            # primary URL is Ollama endpoint — use existing Ollama adapter
            logger.debug("make_llm_client: provider mode but Ollama URL, using OllamaLLMClient")
            return OllamaLLMClient()
    # Legacy path — no [llm] section
    logger.debug("make_llm_client: legacy mode, using OllamaLLMClient")
    return OllamaLLMClient()


def make_embedder(config):
    """Return the appropriate graphiti-core EmbedderClient based on config.

    When [llm] section present and embed URL is openai-compatible:
        → OpenAIEmbedder (graphiti-core's built-in openai embedder)
    When [llm] section present and embed URL is Ollama:
        → OllamaEmbedder (existing adapter)
    When [llm] absent (legacy mode):
        → OllamaEmbedder (existing path, no change)

    Args:
        config: LLMConfig instance (from load_config())

    Returns:
        An instance implementing graphiti_core.embedder.client.EmbedderClient
    """
    from src.llm.provider import _detect_sdk

    if config.llm_mode == "provider":
        embed_sdk = _detect_sdk(config.llm_embed_url or "")
        if embed_sdk == "openai":
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
            embed_cfg = OpenAIEmbedderConfig(
                api_key=config.llm_embed_api_key or config.llm_primary_api_key,
                base_url=config.llm_embed_url,
                embedding_model=config.llm_embed_models[0] if config.llm_embed_models else "text-embedding-3-small",
            )
            logger.debug(
                "make_embedder: using OpenAIEmbedder",
                base_url=config.llm_embed_url,
                model=embed_cfg.embedding_model,
            )
            return OpenAIEmbedder(config=embed_cfg)
        else:
            logger.debug("make_embedder: provider mode but Ollama embed URL, using OllamaEmbedder")
            return OllamaEmbedder()
    # Legacy path
    logger.debug("make_embedder: legacy mode, using OllamaEmbedder")
    return OllamaEmbedder()
