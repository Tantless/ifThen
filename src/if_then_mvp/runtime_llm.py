from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.util
from pathlib import Path
from typing import Any

from if_then_mvp.llm import LLMClient


@dataclass(frozen=True)
class RuntimeLLMConfig:
    base_url: str
    api_key: str
    chat_model: str


@dataclass(frozen=True)
class RuntimeLLMClients:
    api: LLMClient
    worker: LLMClient


@dataclass(frozen=True)
class LocalLLMConfig:
    api: RuntimeLLMConfig
    worker: RuntimeLLMConfig


def load_local_llm_config(
    module_name: str = "local_llm_config",
    *,
    search_root: Path | None = None,
) -> LocalLLMConfig:
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        module = _load_module_from_project_root(
            module_name=module_name,
            search_root=search_root or _default_search_root(),
        )
        if module is None:
            raise RuntimeError(
                "Missing local_llm_config.py. Create it in the project root with API_LLM_CONFIG and WORKER_LLM_CONFIG."
            ) from exc

    return LocalLLMConfig(
        api=_load_runtime_config(module=module, attribute_name="API_LLM_CONFIG"),
        worker=_load_runtime_config(module=module, attribute_name="WORKER_LLM_CONFIG"),
    )


def build_runtime_llm_clients(module_name: str = "local_llm_config") -> RuntimeLLMClients:
    config = load_local_llm_config(module_name=module_name)
    return RuntimeLLMClients(
        api=LLMClient(
            base_url=config.api.base_url,
            api_key=config.api.api_key,
            chat_model=config.api.chat_model,
        ),
        worker=LLMClient(
            base_url=config.worker.base_url,
            api_key=config.worker.api_key,
            chat_model=config.worker.chat_model,
        ),
    )


def _load_runtime_config(*, module: Any, attribute_name: str) -> RuntimeLLMConfig:
    payload = getattr(module, attribute_name, None)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{attribute_name} must be a dict with base_url, api_key, and chat_model.")

    base_url = str(payload.get("base_url", "")).strip()
    api_key = str(payload.get("api_key", "")).strip()
    chat_model = str(payload.get("chat_model", "")).strip()

    if not base_url or not api_key or not chat_model:
        raise RuntimeError(f"{attribute_name} is missing base_url, api_key, or chat_model.")

    return RuntimeLLMConfig(
        base_url=base_url,
        api_key=api_key,
        chat_model=chat_model,
    )


def _default_search_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_module_from_project_root(*, module_name: str, search_root: Path) -> Any | None:
    module_path = search_root / f"{module_name}.py"
    if not module_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
