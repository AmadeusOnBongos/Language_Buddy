from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

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


class GroqClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(
            base_url=settings.llm_base_url or "https://api.groq.com/openai/v1",
            api_key=api_key,
        )
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
        kwargs = dict(
            model=model or self.model,
            messages=msgs,
            temperature=temperature,
        )
        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "",
        )


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
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
        kwargs = dict(
            model=model or self.model,
            messages=msgs,
            temperature=temperature,
        )
        response = self.client.chat.completions.create(**kwargs)
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
