from pathlib import Path

import yaml


def load_config(path: str) -> dict:
    """Load a YAML configuration file into a dictionary."""
    with Path(path).open("r") as f:
        return yaml.safe_load(f)
