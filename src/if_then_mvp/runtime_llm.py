from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import importlib
import importlib.util
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select

from if_then_mvp.llm import LLMClient
from if_then_mvp.models import AppSetting


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


def load_effective_llm_config(
    *,
    role: str,
    settings_map: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
    search_root: Path | None = None,
) -> RuntimeLLMConfig:
    settings_map = dict(settings_map or {})
    env = env or os.environ

    base_url = settings_map.get("llm.base_url") or env.get("IF_THEN_LLM_BASE_URL")
    api_key = settings_map.get("llm.api_key") or env.get("IF_THEN_LLM_API_KEY")

    # 根据 role 选择对应的模型配置
    if role == "api":
        # API (推演) 优先使用 llm.simulation_model，回退到 llm.chat_model
        chat_model = (
            settings_map.get("llm.simulation_model")
            or settings_map.get("llm.chat_model")
            or env.get("IF_THEN_LLM_SIMULATION_MODEL")
            or env.get("IF_THEN_LLM_CHAT_MODEL")
        )
    else:
        # Worker (分析) 使用 llm.chat_model
        chat_model = settings_map.get("llm.chat_model") or env.get("IF_THEN_LLM_CHAT_MODEL")

    if base_url and api_key and chat_model:
        return RuntimeLLMConfig(
            base_url=base_url,
            api_key=api_key,
            chat_model=chat_model,
        )

    fallback = load_local_llm_config(search_root=search_root)
    selected = fallback.api if role == "api" else fallback.worker
    return RuntimeLLMConfig(
        base_url=selected.base_url,
        api_key=selected.api_key,
        chat_model=selected.chat_model,
    )


def build_runtime_llm_client(
    *,
    role: str,
    settings_map: Mapping[str, str] | None = None,
    env: Mapping[str, str] | None = None,
    search_root: Path | None = None,
) -> LLMClient:
    config = load_effective_llm_config(
        role=role,
        settings_map=settings_map,
        env=env,
        search_root=search_root,
    )
    return LLMClient(
        base_url=config.base_url,
        api_key=config.api_key,
        chat_model=config.chat_model,
    )


def load_runtime_settings_map(session) -> dict[str, str]:
    rows = session.execute(
        select(AppSetting).where(
            AppSetting.setting_key.in_(("llm.base_url", "llm.api_key", "llm.chat_model", "llm.simulation_model"))
        )
    ).scalars().all()
    return {row.setting_key: row.setting_value for row in rows}


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
