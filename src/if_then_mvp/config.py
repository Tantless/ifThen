from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    data_dir: Path


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("IF_THEN_DATA_DIR", ".data"))
    return Settings(data_dir=data_dir)
