"""src/llm/health.py — Health check for configured LLM and embeddings providers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog

from src.config import Config
from src.llm.client import LLMError, make_llm_client

logger = structlog.get_logger(__name__)


@dataclass
class HealthResult:
    provider: str
    model: str
    status: str               # "OK" | "UNREACHABLE"
    error: str | None
    embeddings_status: str    # "OK" | "UNREACHABLE" | "not configured"
    embeddings_error: str | None


async def check_health(config: Config) -> HealthResult:
    """Probe configured providers. Never raises — failures produce UNREACHABLE status."""
    client = make_llm_client(config)

    # Probe LLM provider
    status = "OK"
    error: str | None = None
    try:
        await asyncio.wait_for(
            client.chat([{"role": "user", "content": "ping"}]),
            timeout=5.0,
        )
    except (LLMError, asyncio.TimeoutError) as e:
        status = "UNREACHABLE"
        error = str(e)
    except Exception as e:  # noqa: BLE001
        status = "UNREACHABLE"
        error = repr(e)

    # Probe embeddings
    embeddings_status: str
    embeddings_error: str | None = None
    if config.embeddings is None:
        embeddings_status = "not configured"
    else:
        try:
            result = await asyncio.wait_for(
                client.embed(["ping"]),
                timeout=5.0,
            )
            if result:
                embeddings_status = "OK"
            else:
                embeddings_status = "UNREACHABLE"
                embeddings_error = "empty response from embeddings endpoint"
        except (LLMError, asyncio.TimeoutError) as e:
            embeddings_status = "UNREACHABLE"
            embeddings_error = str(e)
        except Exception as e:  # noqa: BLE001
            embeddings_status = "UNREACHABLE"
            embeddings_error = repr(e)

    return HealthResult(
        provider=config.llm.provider,
        model=config.llm.model,
        status=status,
        error=error,
        embeddings_status=embeddings_status,
        embeddings_error=embeddings_error,
    )
