"""Shared filesystem paths."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT_DIR / ".cache"
CONFIG_PATH = ROOT_DIR / "config.json"
