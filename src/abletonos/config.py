"""Configuration module for AbletonOS."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


# XDG Base Directory paths (Phase 0 spec)
ABLETONOS_DIR = Path.home() / ".abletonOS"
CONFIG_DIR = ABLETONOS_DIR / "config"
DATA_DIR = ABLETONOS_DIR / "db"
LOGS_DIR = ABLETONOS_DIR / "logs"
TEMPLATES_DIR = ABLETONOS_DIR / "templates"

CONFIG_FILE = CONFIG_DIR / "config.yaml"


@dataclass(frozen=True)
class AbletonOSConfig:
    """Configuration for AbletonOS."""

    project_root: str
    pocketbase_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "project_root": self.project_root,
            "pocketbase_url": self.pocketbase_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AbletonOSConfig:
        """Create from dictionary loaded from YAML."""
        return cls(
            project_root=data["project_root"],
            pocketbase_url=data.get("pocketbase_url"),
        )


def load_config() -> AbletonOSConfig:
    """Load configuration from config.yaml.

    Returns:
        AbletonOSConfig instance with loaded data.

    Raises:
        FileNotFoundError: If config file doesn't exist.
    """
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_FILE}. Run 'abletonos init-config' first.")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    return AbletonOSConfig(
        project_root=data.get("project_root", ""),
        pocketbase_url=data.get("pocketbase_url"),
    )


def save_config(config: AbletonOSConfig) -> None:
    """Save configuration to config.yaml atomically.

    Args:
        config: The configuration to save.
    """
    ensure_directories()

    # Atomic write: temp file + rename
    temp_file = CONFIG_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(asdict(config), f, default_flow_style=False, sort_keys=False)
        temp_file.rename(CONFIG_FILE)
    except Exception:
        if temp_file.exists():
            temp_file.unlink()
        raise


def ensure_directories() -> None:
    """Create the default AbletonOS directory structure.

    Creates ~/.abletonOS/{config,db,logs,templates}/
    """
    for subdir in [CONFIG_DIR, DATA_DIR, LOGS_DIR, TEMPLATES_DIR]:
        subdir.mkdir(parents=True, exist_ok=True)
