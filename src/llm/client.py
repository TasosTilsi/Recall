"""OllamaClient with cloud-first failover and retry logic.

This module provides the core LLM client that implements the cloud-first/local-fallback
pattern. All LLM operations flow through this client which handles retries, cooldowns,
and automatic failover per the decisions in CONTEXT.md.
"""

import json
import re
import time
from pathlib import Path

import httpx
import structlog
from ollama import Client, ResponseError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from src.llm.config import LLMConfig, get_state_path
from src.llm.quota import QuotaTracker
from src.llm.queue import LLMRequestQueue

logger = structlog.get_logger()


class LLMUnavailableError(Exception):
    """Raised when both cloud and local LLM providers fail.

    Message format per CONTEXT.md:
      "LLM unavailable. Request queued for retry. ID: <uuid>"

    The request_id is populated by the queue module (Plan 03-04).
    Before queue integration, request_id is None and message is:
      "LLM unavailable. Request will be queued for retry."
    """

    def __init__(self, message: str | None = None, request_id: str | None = None):
        self.request_id = request_id
        if message is None:
            if request_id:
                message = f"LLM unavailable. Request queued for retry. ID: {request_id}"
            else:
                message = "LLM unavailable. Request will be queued for retry."
        super().__init__(message)


class OllamaClient:
    """Ollama client with cloud-first failover and automatic retry.

    Implements the cloud-first/local-fallback pattern with:
    - Cloud Ollama tried first when not in cooldown
    - Automatic retry with fixed delay on errors
    - Rate-limit (429) triggers 10-minute cooldown
    - Non-rate-limit errors do NOT set cooldown; cloud is tried on next request
    - Automatic failover to local Ollama on cloud failure
    - Clear error messages for missing local models
    """

    def __init__(self, config: LLMConfig):
        """Initialize OllamaClient with configuration.

        Args:
            config: LLM configuration (from load_config())
        """
        self.config = config
        self._current_provider: str = "none"

        # Configure cloud client with authentication and timeouts
        cloud_headers = {}
        if config.cloud_api_key:
            cloud_headers["Authorization"] = f"Bearer {config.cloud_api_key}"

        cloud_timeout = httpx.Timeout(
            connect=5.0,
            read=config.request_timeout_seconds,
            write=10.0,
            pool=20.0,
        )

        self.cloud_client = Client(
            host=config.cloud_endpoint,
            headers=cloud_headers,
            timeout=cloud_timeout,
        )

        # Configure local client timeouts (read uses config to handle large structured prompts)
        local_timeout = httpx.Timeout(
            connect=2.0,
            read=float(config.request_timeout_seconds),
            write=10.0,
            pool=5.0,
        )

        self.local_client = Client(
            host=config.local_endpoint,
            timeout=local_timeout,
        )

        # Initialize cooldown state
        self.cloud_cooldown_until = 0  # Unix timestamp
        self._load_cooldown_state()

        # Per-operation 401 tracking: when an operation gets 401 from cloud,
        # stop trying cloud for that operation for the rest of the session.
        # This prevents hammering cloud with embed calls when the API key
        # doesn't include embedding access (chat may still work fine).
        self._cloud_denied_ops: set[str] = set()

        # Initialize quota tracker and request queue
        self._quota_tracker = QuotaTracker(config.quota_warning_threshold)
        self._request_queue = LLMRequestQueue(config)

        # Handle local_auto_start config
        # TODO: local_auto_start implementation deferred. Config field exists for future use.
        if config.local_auto_start:
            logger.debug(
                "local_auto_start is configured but auto-start is not yet implemented. "
                "Start Ollama manually: ollama serve"
            )

        logger.debug(
            "OllamaClient initialized",
            cloud_endpoint=config.cloud_endpoint,
            local_endpoint=config.local_endpoint,
            has_api_key=bool(config.cloud_api_key),
        )

    def _is_cloud_available(self, operation: str | None = None) -> bool:
        """Check if cloud Ollama can be used for the given operation.

        Checks: API key set, cloud models configured for the operation,
        per-operation 401 denials, and rate-limit cooldown.

        Args:
            operation: Operation to check ("chat", "generate", "embed").
                      If None, only checks global availability.

        Returns:
            True if cloud can handle this operation.
        """
        if not self.config.cloud_api_key:
            return False

        # Require cloud_models configured for chat/generate operations
        if operation in ("chat", "generate") and not self.config.cloud_models:
            return False

        # Embed: skip cloud entirely (no cloud embedding support configured)
        if operation == "embed":
            return False

        # Check per-operation denial (e.g. 401 on a specific endpoint)
        if operation and operation in self._cloud_denied_ops:
            logger.debug(
                "Cloud denied for operation (prior 401)",
                operation=operation,
            )
            return False

        current_time = time.time()
        is_available = current_time >= self.cloud_cooldown_until

        if not is_available:
            remaining = int(self.cloud_cooldown_until - current_time)
            logger.debug(
                "Cloud in rate-limit cooldown",
                remaining_seconds=remaining,
            )

        return is_available

    def _load_cooldown_state(self):
        """Load cooldown state from disk if exists."""
        state_path = get_state_path()
        if not state_path.exists():
            return

        try:
            with open(state_path) as f:
                state = json.load(f)
                self.cloud_cooldown_until = state.get("cloud_cooldown_until", 0)
                logger.debug(
                    "Cooldown state loaded",
                    cloud_cooldown_until=self.cloud_cooldown_until,
                )
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(
                "Failed to load cooldown state, starting fresh",
                error=str(e),
            )

    def _save_cooldown_state(self):
        """Save cooldown state to disk for persistence across restarts."""
        state_path = get_state_path()

        # Ensure parent directory exists
        state_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(state_path, "w") as f:
                json.dump({"cloud_cooldown_until": self.cloud_cooldown_until}, f)
        except OSError as e:
            logger.warning(
                "Failed to save cooldown state",
                error=str(e),
            )

    def _handle_cloud_error(self, error: ResponseError, operation: str | None = None):
        """Handle cloud error with appropriate cooldown and logging.

        Args:
            error: ResponseError from cloud Ollama
            operation: Operation that failed ("chat", "generate", "embed")
        """
        if error.status_code == 429:
            # Rate limit: Set 10-minute cooldown
            self.cloud_cooldown_until = time.time() + self.config.rate_limit_cooldown_seconds
            self._save_cooldown_state()
            logger.warning(
                "Cloud rate-limited (429). Cooldown activated",
                cooldown_seconds=self.config.rate_limit_cooldown_seconds,
                cooldown_until=self.cloud_cooldown_until,
            )
        elif error.status_code == 401 and operation:
            # 401 on a specific operation: the API key lacks access for this
            # endpoint (e.g. embed). Stop trying cloud for this operation
            # for the rest of the session to avoid repeated failed round-trips.
            self._cloud_denied_ops.add(operation)
            logger.warning(
                "Cloud denied (401) for operation — disabling cloud for this op",
                operation=operation,
                error=str(error.error),
            )
        else:
            # Non-rate-limit, non-401 errors do NOT set cooldown.
            # Cloud will be tried again on the very next request.
            logger.warning(
                "Cloud error (non-rate-limit)",
                status_code=error.status_code,
                error=str(error.error),
            )

        # Log failover event if configured
        if self.config.failover_logging:
            logger.info(
                "llm_failover",
                from_provider="cloud",
                to_provider="local",
                reason="rate_limit" if error.status_code == 429 else "error",
                error_code=error.status_code,
            )

    def _try_cloud(self, operation: str, **kwargs):
        """Try operation across all cloud models with retry on each.

        Iterates self.config.cloud_models in order. On 401, stops immediately
        (fail fast) and falls back to local. On other errors, tries the next
        cloud model. Only falls back to local after ALL cloud models fail.

        Args:
            operation: Operation name ("chat", "generate")
            **kwargs: Arguments to pass to the operation (model= will be set per-model)

        Returns:
            Operation result on first successful cloud model.

        Raises:
            ResponseError: If a 401 is received (caller should fall back to local).
            LLMUnavailableError: If all cloud models fail with non-401 errors.
        """
        last_error = None
        for cloud_model in self.config.cloud_models:
            try:
                call_kwargs = {**kwargs, "model": cloud_model}
                result = self._retry_cloud(operation, **call_kwargs)
                return result
            except (ResponseError, RetryError) as e:
                # Extract the underlying ResponseError
                if isinstance(e, RetryError):
                    if hasattr(e.last_attempt, 'exception') and e.last_attempt.exception():
                        e = e.last_attempt.exception()

                last_error = e
                if isinstance(e, ResponseError):
                    self._handle_cloud_error(e, operation=operation)

                    # 401 → fail fast: stop trying cloud models, fall back to local
                    if e.status_code == 401:
                        logger.info(
                            "Cloud 401 — skipping remaining cloud models",
                            model=cloud_model,
                            operation=operation,
                        )
                        raise

                    # 429 → cooldown set, no point trying other cloud models
                    if e.status_code == 429:
                        logger.info(
                            "Cloud rate-limited — skipping remaining cloud models",
                            model=cloud_model,
                            operation=operation,
                        )
                        raise

                    # Other errors (e.g. 400 bad request, model not found)
                    # → try next cloud model
                    logger.debug(
                        "Cloud model failed, trying next",
                        model=cloud_model,
                        operation=operation,
                        error=str(e.error),
                    )

        # All cloud models failed — raise the last error so caller falls back to local
        if isinstance(last_error, ResponseError):
            raise last_error
        raise LLMUnavailableError(
            f"All cloud models failed. Last error: {last_error}"
        ) from last_error

    def _retry_cloud(self, operation: str, **kwargs):
        """Retry cloud operation with tenacity.

        Args:
            operation: Operation name ("chat", "generate", or "embed")
            **kwargs: Arguments to pass to the operation

        Returns:
            Operation result

        Raises:
            ResponseError: If all retry attempts fail
        """

        def _is_retryable(exc: BaseException) -> bool:
            """Only retry transient errors (connection issues, 5xx). Never retry 4xx."""
            if isinstance(exc, ResponseError):
                return exc.status_code >= 500
            return isinstance(exc, ConnectionError)

        @retry(
            stop=stop_after_attempt(self.config.retry_max_attempts),
            wait=wait_fixed(self.config.retry_delay_seconds),
            retry=lambda retry_state: _is_retryable(retry_state.outcome.exception())
            if retry_state.outcome.exception()
            else False,
            before_sleep=lambda retry_state: logger.info(
                "Retrying cloud request",
                attempt=retry_state.attempt_number,
                max_attempts=self.config.retry_max_attempts,
                delay_seconds=self.config.retry_delay_seconds,
            ),
        )
        def _do_retry():
            if operation == "chat":
                return self.cloud_client.chat(**kwargs)
            elif operation == "generate":
                return self.cloud_client.generate(**kwargs)
            elif operation == "embed":
                return self.cloud_client.embed(**kwargs)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        result = _do_retry()
        self._current_provider = "cloud"

        # Track quota usage after successful cloud call
        # Note: ollama library may not expose raw httpx response headers
        # Check if response has headers attribute, otherwise fall back to local counting
        if hasattr(result, 'headers') and result.headers:
            self._quota_tracker.update_from_headers(result.headers)
        else:
            # Fallback: increment local count
            self._quota_tracker.increment_local_count()

        return result

    def _check_local_models(self) -> list[str]:
        """Check which models are available in local Ollama.

        Returns:
            List of available model names

        Raises:
            LLMUnavailableError: If local Ollama is not running
        """
        try:
            response = self.local_client.list()
            # Ollama SDK v0.6+ returns Pydantic models with .models attribute
            # and each model has .model (not ["name"])
            models = getattr(response, "models", None) or response.get("models", [])
            return [getattr(m, "model", None) or m.get("name", "") for m in models]
        except Exception as e:
            raise LLMUnavailableError(
                "Local Ollama not running. Start with: ollama serve"
            ) from e

    def _try_local(self, operation: str, model: str | None, **kwargs):
        """Try operation with local Ollama.

        Args:
            operation: Operation name ("chat", "generate", or "embed")
            model: Model name (None = use fallback chain)
            **kwargs: Arguments to pass to the operation

        Returns:
            Operation result

        Raises:
            LLMUnavailableError: If local Ollama unavailable or models not pulled
        """
        # Check local Ollama is running
        available_models = self._check_local_models()

        # Determine which model to use
        if model is not None:
            # Specific model requested - check exact name or with :latest suffix
            # (Ollama stores models as "name:tag"; config may omit ":latest")
            model_with_tag = model if ":" in model else f"{model}:latest"
            if model not in available_models and model_with_tag not in available_models:
                raise LLMUnavailableError(
                    f"Model {model} not available. Run: ollama pull {model}"
                )
            # Use the canonical name that is actually listed
            canonical = model if model in available_models else model_with_tag
            models_to_try = [canonical]
        else:
            # Use fallback chain
            models_to_try = [
                m for m in self.config.local_models if m in available_models
            ]
            if not models_to_try:
                missing = ", ".join(self.config.local_models)
                raise LLMUnavailableError(
                    f"No configured models available. Run: ollama pull {missing}"
                )

            # Sort largest-first so we prefer quality, but keep all models for fallback.
            # get_largest_available_model() would reduce to one entry — removing the
            # fallback chain entirely. Instead, sort by param count and try each in turn.
            models_to_try = sorted(
                models_to_try,
                key=lambda m: _extract_param_count(m),
                reverse=True,
            )

        # Try each model in order
        last_error = None
        for model_name in models_to_try:
            try:
                kwargs["model"] = model_name
                if operation == "chat":
                    result = self.local_client.chat(**kwargs)
                elif operation == "generate":
                    result = self.local_client.generate(**kwargs)
                elif operation == "embed":
                    result = self.local_client.embed(**kwargs)
                else:
                    raise ValueError(f"Unknown operation: {operation}")

                self._current_provider = "local"
                logger.debug(
                    "Local operation succeeded",
                    operation=operation,
                    model=model_name,
                )
                return result
            except Exception as e:
                last_error = e
                logger.debug(
                    "Local model failed, trying next",
                    model=model_name,
                    error=str(e),
                )

        # All models failed
        raise LLMUnavailableError(
            f"All local models failed. Last error: {last_error}"
        ) from last_error

    def chat(self, model: str | None = None, messages: list[dict] | None = None, **kwargs):
        """Send chat completion request with automatic failover.

        Tries all cloud models in order. On 401, fails fast to local.
        On other errors, tries next cloud model. Falls back to local only
        after all cloud models are exhausted.

        Args:
            model: Model name (None = use cloud default or local fallback)
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional arguments for ollama.chat()

        Returns:
            Chat completion response

        Raises:
            LLMUnavailableError: If both cloud and local fail (request queued with ID)
        """
        try:
            # Try cloud if available
            if self._is_cloud_available("chat"):
                try:
                    # Cloud models may not support Ollama's format= constrained generation.
                    # Strip it; cloud relies on the example injected into the prompt by
                    # OllamaLLMClient._inject_example() for structured-output guidance.
                    cloud_kwargs = {k: v for k, v in kwargs.items() if k != "format"}
                    return self._try_cloud("chat", messages=messages, **cloud_kwargs)
                except (ResponseError, LLMUnavailableError):
                    # Fall through to local
                    pass

            # Fallback to local
            return self._try_local("chat", model, messages=messages, **kwargs)

        except LLMUnavailableError as e:
            # Both cloud and local failed - queue the request
            params = {"model": model, "messages": messages, **kwargs}
            request_id = self._request_queue.enqueue("chat", params, str(e))

            # Raise with queue ID
            raise LLMUnavailableError(
                f"LLM unavailable. Request queued for retry. ID: {request_id}",
                request_id=request_id
            ) from e

    def generate(self, model: str | None = None, prompt: str | None = None, **kwargs):
        """Send generate request with automatic failover.

        Tries all cloud models in order. On 401, fails fast to local.
        On other errors, tries next cloud model. Falls back to local only
        after all cloud models are exhausted.

        Args:
            model: Model name (None = use cloud default or local fallback)
            prompt: Prompt text
            **kwargs: Additional arguments for ollama.generate()

        Returns:
            Generate response

        Raises:
            LLMUnavailableError: If both cloud and local fail (request queued with ID)
        """
        try:
            # Try cloud if available
            if self._is_cloud_available("generate"):
                try:
                    return self._try_cloud("generate", prompt=prompt, **kwargs)
                except (ResponseError, LLMUnavailableError):
                    # Fall through to local
                    pass

            # Fallback to local
            return self._try_local("generate", model, prompt=prompt, **kwargs)

        except LLMUnavailableError as e:
            # Both cloud and local failed - queue the request
            params = {"model": model, "prompt": prompt, **kwargs}
            request_id = self._request_queue.enqueue("generate", params, str(e))

            # Raise with queue ID
            raise LLMUnavailableError(
                f"LLM unavailable. Request queued for retry. ID: {request_id}",
                request_id=request_id
            ) from e

    def embed(self, model: str | None = None, input: str | list[str] | None = None, **kwargs):
        """Send embeddings request with automatic failover.

        Args:
            model: Model name (None = use embeddings_model from config)
            input: Text or list of texts to embed
            **kwargs: Additional arguments for ollama.embed()

        Returns:
            Embeddings response

        Raises:
            LLMUnavailableError: If both cloud and local fail (request queued with ID)
        """
        try:
            # Cloud: use explicit model or first in embeddings_models list
            embed_model = model or self.config.embeddings_models[0]

            # Try cloud if available
            if self._is_cloud_available("embed"):
                try:
                    return self._retry_cloud("embed", model=embed_model, input=input, **kwargs)
                except (ResponseError, RetryError) as e:
                    # Extract ResponseError from RetryError if needed
                    if isinstance(e, RetryError):
                        if hasattr(e.last_attempt, 'exception') and e.last_attempt.exception():
                            e = e.last_attempt.exception()
                    if isinstance(e, ResponseError):
                        self._handle_cloud_error(e, operation="embed")
                    # Fall through to local

            # Local fallback: if specific model requested, delegate to _try_local
            if model is not None:
                return self._try_local("embed", model, input=input, **kwargs)

            # No specific model: try each embeddings_models entry that exists locally
            available_models = self._check_local_models()
            last_error = None
            for m in self.config.embeddings_models:
                canonical = m if m in available_models else (
                    f"{m}:latest" if f"{m}:latest" in available_models else None
                )
                if canonical is None:
                    continue
                try:
                    result = self.local_client.embed(model=canonical, input=input, **kwargs)
                    self._current_provider = "local"
                    return result
                except Exception as e:
                    last_error = e
                    continue
            raise LLMUnavailableError(
                f"No embedding models available locally. Last error: {last_error}"
            )

        except LLMUnavailableError as e:
            # Both cloud and local failed - queue the request
            params = {"model": embed_model, "input": input, **kwargs}
            request_id = self._request_queue.enqueue("embed", params, str(e))

            # Raise with queue ID
            raise LLMUnavailableError(
                f"LLM unavailable. Request queued for retry. ID: {request_id}",
                request_id=request_id
            ) from e

    @property
    def current_provider(self) -> str:
        """Get the current active provider.

        Returns:
            "cloud", "local", or "none"
        """
        return self._current_provider

    def get_quota_status(self):
        """Get current quota status from tracker.

        Returns:
            QuotaInfo with limit, remaining, usage details
        """
        return self._quota_tracker.get_status()

    def get_queue_stats(self) -> dict:
        """Get request queue statistics.

        Returns:
            Dict with pending count, max size, TTL hours
        """
        return self._request_queue.get_queue_stats()

    def process_queue(self) -> tuple[int, int]:
        """Process all queued requests.

        Attempts to retry all failed requests in the queue.
        Items are removed on success, kept on failure for later retry.

        Returns:
            Tuple of (success_count, failure_count)
        """
        def processor(operation: str, params: dict):
            """Process a queued request by calling the appropriate method."""
            if operation == "chat":
                return self.chat(**params)
            elif operation == "generate":
                return self.generate(**params)
            elif operation == "embed":
                return self.embed(**params)
            else:
                raise ValueError(f"Unknown operation: {operation}")

        success, failure = self._request_queue.process_all(processor)

        logger.info(
            "queue_processing_complete",
            success=success,
            failure=failure,
            remaining=self._request_queue.get_pending_count()
        )

        return (success, failure)


def _extract_param_count(model_name: str) -> int:
    """Extract parameter count from a model name string.

    Examples: "gemma2:9b" -> 9_000_000_000, "llama3.2:3B" -> 3_000_000_000
    """
    match = re.search(r"(\d+)b", model_name.lower())
    return int(match.group(1)) * 1_000_000_000 if match else 0


def get_largest_available_model(models: list[str], available: list[str]) -> str | None:
    """Select largest model from list based on parameter count.

    Args:
        models: List of model names to consider
        available: List of available model names

    Returns:
        Largest available model name, or None if none available
    """
    # Filter to only available models
    available_set = set(available)
    candidates = [m for m in models if m in available_set]

    if not candidates:
        return None

    # Sort by parameter count descending, return largest
    return max(candidates, key=_extract_param_count)
