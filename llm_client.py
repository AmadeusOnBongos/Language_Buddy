from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI, OpenAI

from config import settings


@dataclass
class LLMResponse:
    content: str
    finish_reason: str


class LLMClient(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def async_chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> LLMResponse:
        ...


class GroqClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        base_url = settings.llm_base_url or "https://api.groq.com/openai/v1"
        self._sync = OpenAI(base_url=base_url, api_key=api_key)
        self._async = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> LLMResponse:
        kwargs = dict(
            model=model or self.model,
            input=messages,
            temperature=temperature,
        )
        if system:
            kwargs["instructions"] = system
        response = self._sync.responses.create(**kwargs)
        return LLMResponse(
            content=response.output_text or "",
            finish_reason="stop",
        )

    async def async_chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> LLMResponse:
        kwargs = dict(
            model=model or self.model,
            input=messages,
            temperature=temperature,
        )
        if system:
            kwargs["instructions"] = system
        response = await self._async.responses.create(**kwargs)
        return LLMResponse(
            content=response.output_text or "",
            finish_reason="stop",
        )


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self._sync = OpenAI(api_key=api_key)
        self._async = AsyncOpenAI(api_key=api_key)
        self.model = model

    def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> LLMResponse:
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})
        response = self._sync.chat.completions.create(
            model=model or self.model,
            messages=msgs,
            temperature=temperature,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "",
        )

    async def async_chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> LLMResponse:
        msgs = list(messages)
        if system:
            msgs.insert(0, {"role": "system", "content": system})
        response = await self._async.chat.completions.create(
            model=model or self.model,
            messages=msgs,
            temperature=temperature,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "",
        )


def get_llm_client() -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "groq":
        return GroqClient(api_key=settings.llm_api_key, model=settings.llm_model)
    elif provider == "openai":
        return OpenAIClient(api_key=settings.llm_api_key, model=settings.llm_model)
    raise ValueError(f"Unknown LLM provider: {provider}")
