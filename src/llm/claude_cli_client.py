"""Claude CLI LLM client that wraps `claude -p` subprocess calls.

This module provides:
- ClaudeCliLLMClient: graphiti-core LLMClient implementation using `claude -p`
- _claude_p: async helper that invokes the claude CLI subprocess
- claude_cli_available: detects whether the claude binary is on PATH

Used by make_indexer_llm_client() in Phase 20 for fast batch extraction
without requiring ANTHROPIC_API_KEY (leverages Claude Code subscription auth).
"""

import asyncio
import json
import re
import shutil
from asyncio.subprocess import PIPE
from typing import Any

import structlog
from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import LLMConfig as GraphitiLLMConfig, ModelSize
from graphiti_core.prompts.models import Message
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# Module-level sentinel for availability caching
_CLAUDE_AVAILABLE: bool | None = None


async def _claude_p(prompt: str, cli: str = "claude", model: str | None = "sonnet") -> str:
    """Invoke an AI CLI subprocess with a prompt and return the result text.

    For `claude`: uses `--output-format json` for structured output and passes
    `--model` when specified. Output is parsed from the JSON `result` field.

    For any other CLI binary: invokes `<cli> -p <prompt>` and reads stdout
    directly as plain text. The binary must accept a prompt via `-p` flag.

    Args:
        prompt: The full prompt string to pass to the CLI
        cli: Binary name (default: "claude"). Override via config [indexer] cli.
        model: Model name passed as --model to claude (ignored for other CLIs).
               Defaults to "sonnet" — override via config [indexer] model.

    Returns:
        The result text string

    Raises:
        RuntimeError: If the subprocess exits with non-zero return code
        asyncio.TimeoutError: If subprocess does not complete within 120 seconds
    """
    if cli == "claude":
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if model:
            cmd += ["--model", model]
        parse_json = True
    else:
        cmd = [cli, "-p", prompt]
        parse_json = False

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=PIPE,
        stderr=PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        raise asyncio.TimeoutError(f"{cli} -p timed out after 120 seconds")

    if proc.returncode != 0:
        raise RuntimeError(
            f"{cli} -p failed (exit {proc.returncode}): {stderr.decode()}"
        )

    raw = stdout.decode()
    if parse_json:
        result = json.loads(raw)["result"]
    else:
        result = raw.strip()

    logger.debug("ai_cli_p_complete", cli=cli, result_length=len(result))
    return result


def claude_cli_available() -> bool:
    """Return True if the `claude` binary is available on PATH.

    Caches the result in a module-level sentinel. Use ai_cli_available() to
    check a configurable binary name.

    Returns:
        True if claude is on PATH, False otherwise
    """
    global _CLAUDE_AVAILABLE
    if _CLAUDE_AVAILABLE is None:
        _CLAUDE_AVAILABLE = shutil.which("claude") is not None
    return _CLAUDE_AVAILABLE


def ai_cli_available(cli: str = "claude") -> bool:
    """Return True if the given AI CLI binary is available on PATH.

    Args:
        cli: Binary name to check (default: "claude")

    Returns:
        True if the binary is on PATH, False otherwise
    """
    if cli == "claude":
        return claude_cli_available()
    return shutil.which(cli) is not None


class ClaudeCliLLMClient(LLMClient):
    """graphiti-core LLMClient that routes calls through `claude -p` subprocess.

    Implements the LLMClient ABC by invoking the Claude Code CLI binary.
    No ANTHROPIC_API_KEY required — uses Claude Code subscription auth.

    This client is used by make_indexer_llm_client() when claude is on PATH,
    enabling fast batch extraction in Phase 20 without requiring network API keys.

    Note:
        Do NOT strip the JSON schema suffix that graphiti-core appends to
        messages. Claude handles structured output via prompt instructions
        natively (unlike Ollama which uses format= parameter). Stripping the
        schema would remove critical formatting instructions for Claude.
    """

    def __init__(self, cli: str = "claude", model: str = "sonnet"):
        """Initialize ClaudeCliLLMClient.

        Args:
            cli: AI CLI binary to invoke (default: "claude").
            model: Model name passed as --model to claude (default: "sonnet").
                   Ignored for non-claude CLIs.
        """
        config = GraphitiLLMConfig(model=None)
        super().__init__(config)
        self._cli = cli
        self._model = model
        logger.debug("ClaudeCliLLMClient initialized", cli=cli, model=model)

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = 8192,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        """Generate a response via the claude CLI subprocess.

        Builds a single prompt string from the message list, invokes
        `claude -p`, and optionally parses the result as a Pydantic model.

        Args:
            messages: List of Message objects with role and content
            response_model: Optional Pydantic model for structured JSON output
            max_tokens: Maximum tokens (passed to claude implicitly via prompt)
            model_size: Model size hint (unused — claude binary manages selection)

        Returns:
            Dict with parsed model fields (if response_model provided),
            or {"content": result_text} for unstructured responses.

        Raises:
            RuntimeError: If claude subprocess fails
            asyncio.TimeoutError: If claude subprocess exceeds 120s timeout
        """
        # Build a single prompt string from the message list
        prompt = "\n\n".join(
            f"{m.role.upper()}: {m.content}" for m in messages
        )

        logger.debug(
            "claude_cli_generate",
            num_messages=len(messages),
            has_response_model=response_model is not None,
            prompt_length=len(prompt),
        )

        result_text = await _claude_p(prompt, cli=self._cli, model=self._model)

        if response_model is not None:
            try:
                # Strip markdown code fences if present
                clean_text = result_text.strip()
                clean_text = re.sub(r'^```json?\n', '', clean_text)
                clean_text = re.sub(r'\n```$', '', clean_text).strip()
                # Parse and validate against the response model
                parsed = json.loads(clean_text)
                validated = response_model.model_validate(parsed)
                return validated.model_dump()
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "claude_cli_parse_failed",
                    error=str(e),
                    response_preview=result_text[:200],
                )
                return {"content": result_text}

        return {"content": result_text}
