from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

TModel = TypeVar("TModel", bound=BaseModel)
logger = logging.getLogger(__name__)
TRANSIENT_HTTP_STATUS_CODES = {429, 502, 503, 504}


class ChatJSONClient(Protocol):
    def chat_json(self, *, system_prompt: str, user_prompt: str, response_model: type[TModel]) -> TModel: ...


class ChatCompletionsTransport(Protocol):
    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> str: ...


class LLMClientError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenAICompatibleTransport:
    timeout_seconds: float = 60.0
    max_attempts: int = 3
    retry_backoff_seconds: float = 5.0

    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> str:
        import httpx

        headers = {"Authorization": f"Bearer {api_key}"}
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        max_attempts = max(1, self.max_attempts)
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()

                    try:
                        response_payload = response.json()
                    except ValueError as exc:
                        raise LLMClientError("Chat completion response did not contain valid JSON") from exc

                    try:
                        return _extract_message_content(response_payload)
                    except LLMClientError as exc:
                        if not _should_retry_with_stream(response_payload, exc):
                            raise

                        stream_response = client.post(
                            endpoint,
                            json={**payload, "stream": True},
                            headers=headers,
                        )
                        stream_response.raise_for_status()
                        return _extract_streaming_message_content(
                            stream_response.text,
                            missing_content_error=str(exc),
                        )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                should_retry = status_code in TRANSIENT_HTTP_STATUS_CODES and attempt < max_attempts
                _log_chat_completion_http_error(
                    error=exc,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    status_code=status_code,
                    will_retry=should_retry,
                )
                if should_retry:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise LLMClientError(_chat_completion_request_error_message(exc, status_code=status_code)) from exc
            except httpx.TimeoutException as exc:
                last_error = exc
                should_retry = attempt < max_attempts
                _log_chat_completion_http_error(
                    error=exc,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    status_code=None,
                    will_retry=should_retry,
                )
                if should_retry:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise LLMClientError(_chat_completion_request_error_message(exc, status_code=None)) from exc
            except httpx.HTTPError as exc:
                _log_chat_completion_http_error(
                    error=exc,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    status_code=None,
                    will_retry=False,
                )
                raise LLMClientError(_chat_completion_request_error_message(exc, status_code=None)) from exc

        if last_error is not None:
            raise LLMClientError(_chat_completion_request_error_message(last_error, status_code=None)) from last_error
        raise LLMClientError("Chat completion request failed")


def _chat_completion_request_error_message(error: Exception, *, status_code: int | None) -> str:
    status_part = f" status_code={status_code}" if status_code is not None else ""
    return f"Chat completion request failed: {type(error).__name__}{status_part}"


def _log_chat_completion_http_error(
    *,
    error: Exception,
    attempt: int,
    max_attempts: int,
    status_code: int | None,
    will_retry: bool,
) -> None:
    logger.warning(
        "chat_completion_request_failed error_type=%s status_code=%s attempt=%s max_attempts=%s will_retry=%s",
        type(error).__name__,
        status_code,
        attempt,
        max_attempts,
        will_retry,
    )


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


def _should_retry_with_stream(response_payload: Any, error: LLMClientError) -> bool:
    if str(error) != "Chat completion message content must be a string":
        return False

    if not isinstance(response_payload, dict):
        return False

    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return False

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return False

    message = first_choice.get("message")
    return isinstance(message, dict)


def _extract_streaming_message_content(sse_payload: str, *, missing_content_error: str) -> str:
    content_parts: list[str] = []

    for raw_line in sse_payload.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("data:"):
            continue

        data = line[5:].strip()
        if data == "[DONE]":
            break

        try:
            chunk_payload = json.loads(data)
        except json.JSONDecodeError as exc:
            raise LLMClientError("Chat completion stream chunk did not contain valid JSON") from exc

        choices = chunk_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            continue

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            continue

        delta = first_choice.get("delta")
        if not isinstance(delta, dict):
            continue

        content = delta.get("content")
        if isinstance(content, str):
            content_parts.append(content)

    if not content_parts:
        raise LLMClientError(missing_content_error)

    return "".join(content_parts)
