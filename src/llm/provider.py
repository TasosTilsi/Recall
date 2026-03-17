"""Multi-provider LLM routing for Phase 13.

When [llm] section is present in llm.toml, this module handles:
- SDK auto-detection by URL (no explicit type field required)
- ProviderClient: async clients for primary/fallback/embed tiers
- validate_provider_startup(): lightweight ping, fail-fast with sys.exit(1)

When [llm] is absent (llm_mode == "legacy"), this module is a no-op.
"""

import asyncio
import sys
from typing import Literal
from urllib.parse import urlparse

import structlog

from src.llm.config import LLMConfig

logger = structlog.get_logger(__name__)


def _detect_sdk(url: str) -> Literal["ollama", "openai"]:
    """Detect which SDK to use based on URL.

    Rules (from CONTEXT.md locked decision):
    - localhost or 127.0.0.1 → ollama
    - hostname ends with .local → ollama
    - ollama.com in hostname → ollama
    - anything else → openai (AsyncOpenAI with base_url override)

    Args:
        url: The provider URL string.

    Returns:
        "ollama" or "openai"
    """
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
    except Exception:
        return "openai"

    if hostname in ("localhost", "127.0.0.1"):
        return "ollama"
    if hostname.endswith(".local"):
        return "ollama"
    if "ollama.com" in hostname:
        return "ollama"
    return "openai"


class ProviderClient:
    """Async client holder for primary/fallback/embed tiers.

    Instantiated when [llm] is present in config. Holds the correct SDK client
    per tier based on URL auto-detection. Exposes ping_primary() and ping_embed()
    for startup validation.

    Never used when config.llm_mode == "legacy".
    """

    def __init__(self, config: LLMConfig):
        self._config = config
        self._primary_sdk = _detect_sdk(config.llm_primary_url or "")
        self._embed_sdk = _detect_sdk(config.llm_embed_url or "")
        self._fallback_sdk = _detect_sdk(config.llm_fallback_url or "") if config.llm_fallback_url else None

    async def ping_primary(self) -> tuple[bool, str]:
        """Ping the primary provider endpoint to verify reachability and auth.

        Uses a short timeout (connect=1s, read=3s, no retries) — startup ping
        must not add perceptible latency.

        Returns:
            (ok: bool, error_detail: str) — error_detail is "" on success.
        """
        if self._primary_sdk == "openai":
            return await _ping_openai_compatible(
                self._config.llm_primary_url or "",
                self._config.llm_primary_api_key,
            )
        else:
            return _ping_ollama(self._config.llm_primary_url or "")

    async def ping_embed(self) -> tuple[bool, str]:
        """Ping the embed provider endpoint."""
        if self._embed_sdk == "openai":
            return await _ping_openai_compatible(
                self._config.llm_embed_url or "",
                self._config.llm_embed_api_key,
            )
        else:
            return _ping_ollama(self._config.llm_embed_url or "")

    def primary_label(self) -> str:
        """Human-readable label: 'openai/gpt-4o-mini @ api.openai.com'"""
        try:
            hostname = urlparse(self._config.llm_primary_url or "").hostname or self._config.llm_primary_url
        except Exception:
            hostname = self._config.llm_primary_url or "?"
        first_model = self._config.llm_primary_models[0] if self._config.llm_primary_models else "?"
        sdk_name = self._primary_sdk
        return f"{sdk_name}/{first_model} @ {hostname}"

    def embed_label(self) -> str:
        """Human-readable label for embed tier."""
        try:
            hostname = urlparse(self._config.llm_embed_url or "").hostname or self._config.llm_embed_url
        except Exception:
            hostname = self._config.llm_embed_url or "?"
        first_model = self._config.llm_embed_models[0] if self._config.llm_embed_models else "?"
        sdk_name = self._embed_sdk
        return f"{sdk_name}/{first_model} @ {hostname}"

    def fallback_label(self) -> str | None:
        """Human-readable label for fallback tier, or None if unconfigured."""
        if not self._config.llm_fallback_url:
            return None
        try:
            hostname = urlparse(self._config.llm_fallback_url).hostname or self._config.llm_fallback_url
        except Exception:
            hostname = self._config.llm_fallback_url
        first_model = self._config.llm_fallback_models[0] if self._config.llm_fallback_models else "?"
        sdk_name = self._fallback_sdk or "ollama"
        return f"{sdk_name}/{first_model} @ {hostname}"


async def _ping_openai_compatible(base_url: str, api_key: str | None) -> tuple[bool, str]:
    """Ping an OpenAI-compatible endpoint via models.list().

    Uses AsyncOpenAI with a 3-second total timeout and zero retries.
    Returns (True, "") on success, (False, error_detail) on failure.
    """
    from openai import AsyncOpenAI, AuthenticationError, APIConnectionError
    import httpx

    client = AsyncOpenAI(
        api_key=api_key or "no-key",
        base_url=base_url,
        timeout=httpx.Timeout(connect=1.0, read=3.0, write=2.0, pool=5.0),
        max_retries=0,
    )
    try:
        await client.models.list()
        return True, ""
    except AuthenticationError:
        return False, "API key rejected (401) — check primary_api_key in llm.toml"
    except APIConnectionError as e:
        return False, f"Connection refused: {e}"
    except Exception as e:
        return False, str(e)


def _ping_ollama(url: str) -> tuple[bool, str]:
    """Ping an Ollama endpoint via the ollama SDK list() call (sync)."""
    from ollama import Client
    try:
        client = Client(host=url)
        client.list()
        return True, ""
    except Exception as e:
        return False, str(e)


def validate_provider_startup(config: LLMConfig) -> None:
    """Validate provider connectivity at CLI startup.

    Must be called BEFORE any asyncio.run(graph_operation) to avoid
    RuntimeError from nested event loops.

    When llm_mode == "legacy": no-op (Ollama path handles its own errors).
    When llm_mode == "provider": pings primary endpoint; sys.exit(1) on failure.

    Error message format (CONTEXT.md spec):
        "Provider unreachable: <primary_url> — check primary_api_key and primary_url in ~/.graphiti/llm.toml"
    """
    if config.llm_mode != "provider":
        return  # legacy Ollama path — no startup ping

    provider_client = ProviderClient(config)
    ok, error_detail = asyncio.run(provider_client.ping_primary())
    if not ok:
        msg = (
            f"Provider unreachable: {config.llm_primary_url} — "
            f"check primary_api_key and primary_url in ~/.graphiti/llm.toml\n"
            f"Detail: {error_detail}"
        )
        print(msg, file=sys.stderr)
        sys.exit(1)

    logger.debug(
        "Provider startup validation passed",
        url=config.llm_primary_url,
        label=provider_client.primary_label(),
    )
