from uvicorn import run

from if_then_mvp.api import create_app
from if_then_mvp.runtime_llm import build_runtime_llm_clients


if __name__ == "__main__":
    clients = build_runtime_llm_clients()
    run(create_app(llm_client=clients.api), host="127.0.0.1", port=8000)
