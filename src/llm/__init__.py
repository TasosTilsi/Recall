"""LLM integration with cloud Ollama primary, local Ollama fallback.

Quick start:
    from src.llm import chat, embed, get_status

    # Chat with automatic failover
    response = chat([{"role": "user", "content": "Hello"}])

    # Generate embeddings (uses nomic-embed-text by default)
    embeddings = embed("Text to embed")

    # Check system status
    status = get_status()
    print(f"Using: {status['current_provider']}")

Configuration:
    Copy config/llm.toml to ~/.recall/config.toml and customize.
    Set OLLAMA_API_KEY environment variable for cloud access.

Error handling:
    If both cloud and local fail, LLMUnavailableError is raised.
    The request is automatically queued for retry.
    The exception includes the queue ID for tracking.
"""

from .client import LLMUnavailableError, OllamaClient
from .config import LLMConfig, load_config
from .queue import LLMRequestQueue, QueuedRequest
from .quota import QuotaInfo, QuotaTracker

# Singleton client management
_client: OllamaClient | None = None
_config: LLMConfig | None = None


def get_client(config: LLMConfig | None = None) -> OllamaClient:
    """Get or create the singleton OllamaClient.

    Args:
        config: Optional config, uses load_config() if not provided.
                Only used on first call; subsequent calls return existing client.

    Returns:
        Configured OllamaClient instance
    """
    global _client, _config
    if _client is None:
        _config = config or load_config()
        _client = OllamaClient(_config)
    return _client


def reset_client() -> None:
    """Reset the singleton client. Useful for testing."""
    global _client, _config
    _client = None
    _config = None


def chat(messages: list[dict], model: str | None = None, **kwargs) -> dict:
    """Send chat messages to LLM.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Optional model name, uses default from config
        **kwargs: Additional arguments passed to ollama.chat

    Returns:
        Response dict from Ollama

    Raises:
        LLMUnavailableError: If both cloud and local fail (request queued)
    """
    return get_client().chat(model=model, messages=messages, **kwargs)


def generate(prompt: str, model: str | None = None, **kwargs) -> dict:
    """Generate text from prompt.

    Args:
        prompt: Text prompt
        model: Optional model name
        **kwargs: Additional arguments

    Returns:
        Response dict from Ollama

    Raises:
        LLMUnavailableError: If both cloud and local fail (request queued)
    """
    return get_client().generate(model=model, prompt=prompt, **kwargs)


def embed(input: str | list[str], model: str | None = None) -> dict:
    """Generate embeddings for text.

    Args:
        input: Text or list of texts to embed
        model: Optional model name, defaults to nomic-embed-text

    Returns:
        Response dict with embeddings

    Raises:
        LLMUnavailableError: If both cloud and local fail (request queued)
    """
    return get_client().embed(model=model, input=input)


def get_status() -> dict:
    """Get LLM system status.

    Returns:
        Dict with current_provider, quota_status, queue_stats
    """
    client = get_client()
    return {
        "current_provider": client.current_provider,
        "quota": client.get_quota_status(),
        "queue": client.get_queue_stats(),
    }


def make_indexer_llm_client():
    """Return ClaudeCliLLMClient if claude binary available, else OllamaLLMClient.

    Used by indexer.py and session_stop.py for batch extraction and summarization.
    Detection runs once per call (shutil.which is fast, no caching needed here).
    """
    from src.llm.claude_cli_client import claude_cli_available
    if claude_cli_available():
        from src.llm.claude_cli_client import ClaudeCliLLMClient
        return ClaudeCliLLMClient()
    from src.graph.adapters import OllamaLLMClient
    return OllamaLLMClient()


__all__ = [
    # Config
    "LLMConfig",
    "load_config",
    # Client
    "OllamaClient",
    "LLMUnavailableError",
    # Quota
    "QuotaTracker",
    "QuotaInfo",
    # Queue
    "LLMRequestQueue",
    "QueuedRequest",
    # Convenience API
    "get_client",
    "reset_client",
    "chat",
    "generate",
    "embed",
    "get_status",
    # Indexer factory
    "make_indexer_llm_client",
]
