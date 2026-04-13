"""Logging configuration for AbletonOS."""

import logging
import os
from pathlib import Path

from rich.logging import RichHandler

# XDG-style paths
APP_NAME = "abletonOS"
CONFIG_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
LOGS_DIR = CONFIG_DIR / "logs"

DEFAULT_LOG_LEVEL = logging.INFO
DEBUG_ENV_VAR = "ABLETONOS_DEBUG"


def setup_logging(debug: bool = False) -> logging.Logger:
    """Set up logging for the CLI.

    Args:
        debug: If True, set log level to DEBUG. Otherwise, INFO.

    Returns:
        Configured root logger.
    """
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_level = (
        logging.DEBUG if (debug or os.getenv(DEBUG_ENV_VAR)) else DEFAULT_LOG_LEVEL
    )

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=debug)],
    )

    logger = logging.getLogger("abletonos")
    logger.setLevel(log_level)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(f"abletonos.{name}")


def get_log_file_path(name: str = "cli.log") -> Path:
    """Get the path to a log file.

    Args:
        name: Log file name (default: cli.log).

    Returns:
        Path to the log file.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / name
