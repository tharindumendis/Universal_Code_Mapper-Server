import os
from pathlib import Path

def get_base_dir(data_dir: str | None = None) -> Path:
    """Return the base directory for UCM storage (~/.ucm)."""
    if data_dir:
        return Path(data_dir).resolve()
    return Path.home() / ".ucm"
