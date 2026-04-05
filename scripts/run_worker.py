from if_then_mvp.llm import LLMClient
from if_then_mvp.worker import run_forever


if __name__ == "__main__":
    client = LLMClient(base_url="http://localhost:4000/v1", api_key="dev-key", chat_model="gpt-4.1-mini")
    run_forever(llm_client=client)
