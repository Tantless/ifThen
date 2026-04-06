from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

TModel = TypeVar("TModel", bound=BaseModel)


class ChatJSONClient(Protocol):
    def chat_json(self, *, system_prompt: str, user_prompt: str, response_model: type[TModel]) -> TModel: ...


class ChatCompletionsTransport(Protocol):
    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> str: ...


class LLMClientError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenAICompatibleTransport:
    timeout_seconds: float = 60.0

    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> str:
        import httpx

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMClientError("Chat completion request failed") from exc

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise LLMClientError("Chat completion response did not contain valid JSON") from exc

        return _extract_message_content(response_payload)


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
        try:
            return response_model.model_validate_json(content)
        except ValidationError:
            repaired_content = self._repair_structured_output(
                invalid_content=content,
                response_model=response_model,
            )
            try:
                return response_model.model_validate_json(repaired_content)
            except ValidationError as exc:
                raise LLMClientError("Failed to validate structured LLM response") from exc

    def _repair_structured_output(self, *, invalid_content: str, response_model: type[TModel]) -> str:
        schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=False, sort_keys=True)
        repair_payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": "请将给定的 JSON 修复为符合要求的结构。"},
                {
                    "role": "user",
                    "content": (
                        "目标 JSON Schema：\n"
                        f"{schema_json}\n\n"
                        "当前 JSON 内容：\n"
                        f"{invalid_content}\n\n"
                        "请只返回一个符合 schema 的 JSON 对象。"
                        "尽量保留原意，并用最保守、最安全的值补齐缺失字段。"
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        }
        return self.transport.post_chat_completion(
            base_url=self.base_url,
            api_key=self.api_key,
            payload=repair_payload,
        )


def _extract_message_content(response_payload: Any) -> str:
    if not isinstance(response_payload, dict):
        raise LLMClientError("Chat completion response body must be a JSON object")

    choices = response_payload.get("choices")
    if not isinstance(choices, list):
        raise LLMClientError("Chat completion response is missing a choices list")
    if not choices:
        raise LLMClientError("Chat completion response returned no choices")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LLMClientError("Chat completion choice must be an object")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise LLMClientError("Chat completion choice is missing a message object")

    content = message.get("content")
    if not isinstance(content, str):
        raise LLMClientError("Chat completion message content must be a string")

    return content
