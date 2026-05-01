from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    analysis_llm_max_concurrency: int


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("IF_THEN_DATA_DIR", ".data"))
    return Settings(
        data_dir=data_dir,
        analysis_llm_max_concurrency=_read_positive_int("IF_THEN_ANALYSIS_LLM_MAX_CONCURRENCY", 4),
    )


def _read_positive_int(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    return max(1, value)
