"""
JARVIS — Core Configuration Loader
"""
import os
import yaml
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


CONFIG = load_config()


def get(section: str, key: str = None, default=None):
    """Helper to safely get config values."""
    section_data = CONFIG.get(section, {})
    if key is None:
        return section_data
    return section_data.get(key, default)
