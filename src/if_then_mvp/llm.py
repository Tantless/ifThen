from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


class ChatJSONClient(Protocol):
    def chat_json(self, *, system_prompt: str, user_prompt: str, response_model: type[TModel]) -> TModel: ...


class ChatCompletionsTransport(Protocol):
    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> str: ...


@dataclass(slots=True)
class OpenAICompatibleTransport:
    timeout_seconds: float = 60.0

    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> str:
        import httpx

        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


@dataclass(slots=True)
class LLMClient:
    base_url: str
    api_key: str
    chat_model: str
    transport: ChatCompletionsTransport = field(default_factory=OpenAICompatibleTransport)

    def chat_json(self, *, system_prompt: str, user_prompt: str, response_model: type[TModel]) -> TModel:
        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        content = self.transport.post_chat_completion(
            base_url=self.base_url,
            api_key=self.api_key,
            payload=payload,
        )
        return response_model.model_validate_json(content)
