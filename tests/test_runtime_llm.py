import types
from unittest.mock import patch

from if_then_mvp.runtime_llm import build_runtime_llm_clients, load_local_llm_config


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
