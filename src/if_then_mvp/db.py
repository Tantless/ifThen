from pathlib import Path

from .config import get_settings


def get_data_dir() -> Path:
    return get_settings().data_dir
