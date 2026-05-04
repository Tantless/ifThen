from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from if_then_mvp.llm import ChatJSONClient


DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / "llm_config.env"
TModel = TypeVar("TModel", bound=BaseModel)


class ProviderConfigError(RuntimeError):
    pass


class ResponsesProviderError(RuntimeError):
    pass


class ResponsesTransport(Protocol):
    def post_responses(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class EnvLLMConfig:
    base_url: str
    api_key: str
    model: str


@dataclass(slots=True)
class OpenAIResponsesTransport:
    timeout_seconds: float = 120.0
    max_attempts: int = 3
    retry_backoff_seconds: float = 5.0

    def post_responses(self, *, base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(1, max(1, self.max_attempts) + 1):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(f"{base_url.rstrip('/')}/responses", headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code in {429, 502, 503, 504} and attempt < self.max_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise ResponsesProviderError(f"Responses request failed: {type(exc).__name__}") from exc
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue
                raise ResponsesProviderError(f"Responses request failed: {type(exc).__name__}") from exc
            except httpx.HTTPError as exc:
                raise ResponsesProviderError(f"Responses request failed: {type(exc).__name__}") from exc
            except ValueError as exc:
                raise ResponsesProviderError("Responses request returned invalid JSON") from exc

            if not isinstance(data, dict):
                raise ResponsesProviderError("Responses response body must be a JSON object")
            return data

        if last_error is not None:
            raise ResponsesProviderError(f"Responses request failed: {type(last_error).__name__}") from last_error
        raise ResponsesProviderError("Responses request failed")


@dataclass(slots=True)
class ResponsesJSONClient:
    base_url: str
    api_key: str
    model: str
    transport: ResponsesTransport = field(default_factory=OpenAIResponsesTransport)
    max_output_tokens: int = 2048

    def chat_json(self, *, system_prompt: str, user_prompt: str, response_model: type[TModel]) -> TModel:
        content = self._post_json_prompt(system_prompt=system_prompt, user_prompt=user_prompt)
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
                raise ResponsesProviderError("Failed to validate structured Responses output") from exc

    def _post_json_prompt(self, *, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": self.max_output_tokens,
        }
        response_payload = self.transport.post_responses(
            base_url=self.base_url,
            api_key=self.api_key,
            payload=payload,
        )
        return extract_responses_output_text(response_payload)

    def _repair_structured_output(self, *, invalid_content: str, response_model: type[BaseModel]) -> str:
        schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=False, sort_keys=True)
        repair_prompt = (
            "目标 JSON Schema：\n"
            f"{schema_json}\n\n"
            "当前 JSON 内容：\n"
            f"{invalid_content}\n\n"
            "请只返回一个符合 schema 的 JSON 对象。"
            "尽量保留原意，并用最保守、最安全的值补齐缺失字段。"
        )
        return self._post_json_prompt(
            system_prompt="请将给定的 JSON 修复为符合要求的结构。",
            user_prompt=repair_prompt,
        )


def load_env_file(path: Path = DEFAULT_ENV_FILE) -> EnvLLMConfig:
    if not path.exists():
        raise ProviderConfigError(f"Missing env file: {path.name}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    base_url = values.get("API_BASE_URL") or values.get("API_URL")
    api_key = values.get("API_KEY")
    model = values.get("MODEL_NAME")
    missing = [
        key
        for key, value in (
            ("API_BASE_URL", base_url),
            ("API_KEY", api_key),
            ("MODEL_NAME", model),
        )
        if not value
    ]
    if missing:
        raise ProviderConfigError(f"env file missing required keys: {', '.join(missing)}")
    return EnvLLMConfig(base_url=str(base_url), api_key=str(api_key), model=str(model))


def build_responses_client(*, env_file: Path = DEFAULT_ENV_FILE) -> tuple[ChatJSONClient, dict[str, Any]]:
    config = load_env_file(env_file)
    return ResponsesJSONClient(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
    ), {
        "status": "configured",
        "source": env_file.name,
        "api": "responses",
        "model": config.model,
    }


def extract_responses_output_text(response_payload: dict[str, Any]) -> str:
    status = response_payload.get("status")
    if status not in {None, "completed"}:
        raise ResponsesProviderError(f"Responses request did not complete: {status}")
    for item in response_payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content_item in item.get("content") or []:
            if (
                isinstance(content_item, dict)
                and content_item.get("type") == "output_text"
                and isinstance(content_item.get("text"), str)
            ):
                return content_item["text"]
    raise ResponsesProviderError("Responses output did not contain output_text")
