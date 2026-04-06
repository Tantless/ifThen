from if_then_mvp.runtime_llm import build_runtime_llm_clients
from if_then_mvp.worker import run_forever


if __name__ == "__main__":
    clients = build_runtime_llm_clients()
    run_forever(llm_client=clients.worker)
