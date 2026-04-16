import os

from uvicorn import run

from if_then_mvp.api import create_app


if __name__ == "__main__":
    run(create_app(), host="127.0.0.1", port=int(os.environ.get("IF_THEN_API_PORT", "8000")))
