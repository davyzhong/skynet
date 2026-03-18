"""LLM gateway for multiple provider support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

from app.config import get_settings


class ProviderType(Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    provider: ProviderType
    model: str
    tokens_used: int | None = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion for prompt."""
        pass

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """Generate chat completion."""
        pass


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        return self._client

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using Ollama."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)

        payload = {
            "prompt": prompt,
            "model": model,
            "stream": False,
        }

        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data.get("response", ""),
            provider=ProviderType.OLLAMA,
            model=model,
        )

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """Generate chat completion using Ollama."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)

        payload = {
            "messages": messages,
            "model": model,
            "stream": False,
        }

        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data.get("message", {}).get("content", ""),
            provider=ProviderType.OLLAMA,
            model=model,
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None, model: str = "claude-3-sonnet-20240229"):
        settings = get_settings()
        self.api_key = api_key or settings.llm.anthropic_api_key or ""
        self.model = model
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.anthropic.com",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate completion using Anthropic."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", 1024)

        payload = {
            "model": model,
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": max_tokens,
        }

        response = await client.post("/v1/complete", json=payload)
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data.get("completion", ""),
            provider=ProviderType.ANTHROPIC,
            model=model,
            tokens_used=data.get("usage", {}).get("tokens"),
        )

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """Generate chat completion using Anthropic."""
        client = await self._get_client()
        model = kwargs.get("model", self.model)
        max_tokens = kwargs.get("max_tokens", 1024)

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        response = await client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        content = data.get("content", [{}])
        text = content[0].get("text", "") if content else ""

        return LLMResponse(
            content=text,
            provider=ProviderType.ANTHROPIC,
            model=model,
            tokens_used=data.get("usage", {}).get("input_tokens"),
        )


class LLMWrapper:
    """Wrapper that tries multiple providers in order."""

    def __init__(self, providers: list[BaseLLMProvider] | None = None):
        if providers is None:
            settings = get_settings()
            providers = [
                OllamaProvider(base_url=settings.llm.ollama_base_url),
            ]
            if settings.llm.anthropic_api_key:
                providers.append(AnthropicProvider(api_key=settings.llm.anthropic_api_key))

        self.providers = providers

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Try providers in order until one succeeds."""
        errors = []

        for provider in self.providers:
            try:
                return await provider.complete(prompt, **kwargs)
            except Exception as e:
                errors.append(f"{provider.__class__.__name__}: {e}")
                continue

        raise RuntimeError(f"All providers failed: {errors}")

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        """Try providers in order until one succeeds."""
        errors = []

        for provider in self.providers:
            try:
                return await provider.chat(messages, **kwargs)
            except Exception as e:
                errors.append(f"{provider.__class__.__name__}: {e}")
                continue

        raise RuntimeError(f"All providers failed: {errors}")
