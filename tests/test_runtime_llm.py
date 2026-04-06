import types
from unittest.mock import patch

from if_then_mvp.runtime_llm import (
    build_runtime_llm_client,
    build_runtime_llm_clients,
    load_effective_llm_config,
    load_local_llm_config,
)


def test_load_local_llm_config_reads_distinct_api_and_worker_configs(monkeypatch):
    fake_module = types.ModuleType("local_llm_config")
    fake_module.API_LLM_CONFIG = {
        "base_url": "https://api.example.test/v1",
        "api_key": "api-secret",
        "chat_model": "gpt-api",
    }
    fake_module.WORKER_LLM_CONFIG = {
        "base_url": "https://worker.example.test/v1",
        "api_key": "worker-secret",
        "chat_model": "gpt-worker",
    }
    monkeypatch.setitem(__import__("sys").modules, "local_llm_config", fake_module)

    config = load_local_llm_config()

    assert config.api.base_url == "https://api.example.test/v1"
    assert config.api.api_key == "api-secret"
    assert config.api.chat_model == "gpt-api"
    assert config.worker.base_url == "https://worker.example.test/v1"
    assert config.worker.api_key == "worker-secret"
    assert config.worker.chat_model == "gpt-worker"


def test_build_runtime_llm_clients_uses_loaded_api_and_worker_settings(monkeypatch):
    fake_module = types.ModuleType("local_llm_config")
    fake_module.API_LLM_CONFIG = {
        "base_url": "https://api.example.test/v1",
        "api_key": "api-secret",
        "chat_model": "gpt-api",
    }
    fake_module.WORKER_LLM_CONFIG = {
        "base_url": "https://worker.example.test/v1",
        "api_key": "worker-secret",
        "chat_model": "gpt-worker",
    }
    monkeypatch.setitem(__import__("sys").modules, "local_llm_config", fake_module)

    clients = build_runtime_llm_clients()

    assert clients.api.base_url == "https://api.example.test/v1"
    assert clients.api.api_key == "api-secret"
    assert clients.api.chat_model == "gpt-api"
    assert clients.worker.base_url == "https://worker.example.test/v1"
    assert clients.worker.api_key == "worker-secret"
    assert clients.worker.chat_model == "gpt-worker"


def test_load_local_llm_config_falls_back_to_project_root_file(tmp_path, monkeypatch):
    monkeypatch.delitem(__import__("sys").modules, "local_llm_config", raising=False)
    config_file = tmp_path / "local_llm_config.py"
    config_file.write_text(
        "\n".join(
            [
                "API_LLM_CONFIG = {",
                "    'base_url': 'https://api.example.test/v1',",
                "    'api_key': 'api-secret',",
                "    'chat_model': 'gpt-api',",
                "}",
                "WORKER_LLM_CONFIG = {",
                "    'base_url': 'https://worker.example.test/v1',",
                "    'api_key': 'worker-secret',",
                "    'chat_model': 'gpt-worker',",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    with patch("if_then_mvp.runtime_llm.importlib.import_module", side_effect=ModuleNotFoundError):
        config = load_local_llm_config(search_root=tmp_path)

    assert config.api.base_url == "https://api.example.test/v1"
    assert config.worker.chat_model == "gpt-worker"


def test_load_effective_llm_config_prefers_saved_settings_over_env_and_local_file(monkeypatch):
    fake_module = types.ModuleType("local_llm_config")
    fake_module.API_LLM_CONFIG = {
        "base_url": "https://file-api.example/v1",
        "api_key": "file-api-key",
        "chat_model": "file-api-model",
    }
    fake_module.WORKER_LLM_CONFIG = {
        "base_url": "https://file-worker.example/v1",
        "api_key": "file-worker-key",
        "chat_model": "file-worker-model",
    }
    monkeypatch.setitem(__import__("sys").modules, "local_llm_config", fake_module)
    monkeypatch.setenv("IF_THEN_LLM_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("IF_THEN_LLM_API_KEY", "env-key")
    monkeypatch.setenv("IF_THEN_LLM_CHAT_MODEL", "env-model")

    config = load_effective_llm_config(
        role="worker",
        settings_map={
            "llm.base_url": "https://db.example/v1",
            "llm.api_key": "db-key",
            "llm.chat_model": "db-model",
        },
    )

    assert config.base_url == "https://db.example/v1"
    assert config.api_key == "db-key"
    assert config.chat_model == "db-model"


def test_build_runtime_llm_client_falls_back_to_env_when_saved_settings_missing(monkeypatch):
    monkeypatch.delitem(__import__("sys").modules, "local_llm_config", raising=False)
    monkeypatch.setenv("IF_THEN_LLM_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("IF_THEN_LLM_API_KEY", "env-key")
    monkeypatch.setenv("IF_THEN_LLM_CHAT_MODEL", "env-model")

    client = build_runtime_llm_client(role="api", settings_map={})

    assert client.base_url == "https://env.example/v1"
    assert client.api_key == "env-key"
    assert client.chat_model == "env-model"
