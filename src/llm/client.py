"""src/llm/client.py — v3.0 single-provider LLM client. No fallback, no retry."""
from __future__ import annotations

import asyncio
import json
import shutil
from asyncio.subprocess import PIPE
from dataclasses import dataclass

import httpx
import structlog

from src.config import Config

logger = structlog.get_logger(__name__)


class LLMError(Exception):
    """Raised when an LLM operation fails. Message names provider and URL."""


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str


class LLMClient:
    """Single-provider LLM client. No fallback, no retry on other providers."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._provider = config.llm.provider

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        if self._provider == "claude":
            return await self._chat_claude(messages)
        elif self._provider == "ollama":
            return await self._chat_ollama(messages)
        elif self._provider == "openai":
            return await self._chat_openai(messages)
        else:
            raise LLMError(f"Unknown provider: {self._provider}")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self._config.embeddings is None:
            raise LLMError("embeddings not configured — add [embeddings] section to config.toml")

        emb = self._config.embeddings
        url = emb.url or "http://localhost:11434"

        if emb.provider == "ollama":
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.post(
                        f"{url}/api/embed",
                        json={"model": emb.model, "input": texts},
                        timeout=30.0,
                    )
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    raise LLMError(f"ollama embeddings unreachable at {url}: {e}") from e
                if resp.status_code != 200:
                    raise LLMError(f"ollama embeddings error {resp.status_code} at {url}")
                return resp.json()["embeddings"]

        elif emb.provider == "openai":
            headers = {"Content-Type": "application/json"}
            if emb.api_key:
                headers["Authorization"] = f"Bearer {emb.api_key}"
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.post(
                        f"{url}/embeddings",
                        json={"model": emb.model, "input": texts},
                        headers=headers,
                        timeout=30.0,
                    )
                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    raise LLMError(f"openai embeddings unreachable at {url}: {e}") from e
                if resp.status_code != 200:
                    raise LLMError(f"openai embeddings error {resp.status_code} at {url}")
                return [item["embedding"] for item in resp.json()["data"]]

        else:
            raise LLMError(f"Unknown embeddings provider: {emb.provider}")

    async def _chat_claude(self, messages: list[dict]) -> LLMResponse:
        url = self._config.llm.url or "https://api.anthropic.com/v1/messages"
        api_key = self._config.llm.api_key
        if not api_key:
            raise LLMError("claude provider requires api_key in [llm] config")

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Anthropic 'messages' API doesn't use a 'system' role in the messages list.
        # It has a top-level 'system' field.
        system_prompt = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system_prompt = m["content"]
            else:
                user_messages.append(m)

        payload = {
            "model": self._config.llm.model,
            "messages": user_messages,
            "max_tokens": 4096,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=60.0,
                )
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise LLMError(f"anthropic unreachable at {url}: {e}") from e

        if resp.status_code != 200:
            raise LLMError(f"anthropic error {resp.status_code} at {url}: {resp.text}")

        content = resp.json()["content"][0]["text"]
        return LLMResponse(content=content, provider="claude", model=self._config.llm.model)

    async def _chat_ollama(self, messages: list[dict]) -> LLMResponse:
        url = self._config.llm.url or "http://localhost:11434"
        headers = {}
        if self._config.llm.api_key:
            headers["Authorization"] = f"Bearer {self._config.llm.api_key}"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{url}/api/chat",
                    json={"model": self._config.llm.model, "messages": messages, "stream": False},
                    headers=headers,
                    timeout=30.0,
                )
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise LLMError(f"ollama unreachable at {url}: {e}") from e

        if resp.status_code != 200:
            raise LLMError(f"ollama error {resp.status_code} at {url}")

        content = resp.json()["message"]["content"]
        return LLMResponse(content=content, provider="ollama", model=self._config.llm.model)

    async def _chat_openai(self, messages: list[dict]) -> LLMResponse:
        url = self._config.llm.url
        if not url:
            raise LLMError("openai provider requires url in [llm] config")

        headers = {"Content-Type": "application/json"}
        if self._config.llm.api_key:
            headers["Authorization"] = f"Bearer {self._config.llm.api_key}"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{url}/chat/completions",
                    json={"model": self._config.llm.model, "messages": messages},
                    headers=headers,
                    timeout=30.0,
                )
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                raise LLMError(f"openai-compatible provider unreachable at {url}: {e}") from e

        if resp.status_code != 200:
            raise LLMError(f"openai-compatible provider error {resp.status_code} at {url}")

        content = resp.json()["choices"][0]["message"]["content"]
        return LLMResponse(content=content, provider="openai", model=self._config.llm.model)


def make_llm_client(config: Config) -> LLMClient:
    """Factory — construct LLMClient from config."""
    return LLMClient(config)
