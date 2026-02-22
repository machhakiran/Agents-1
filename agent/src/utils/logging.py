"""Structured logging setup."""

import logging
import sys
from typing import Any


def configure_logging(level: str = "INFO", debug: bool = False) -> None:
    """Configure root logger and format."""
    log_level = logging.DEBUG if debug else getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    logging.basicConfig(
        level=log_level,
        format=fmt,
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


def log_task(logger: logging.Logger, task_id: str, message: str, **kwargs: Any) -> None:
    """Log with task_id for traceability."""
    extra = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
    logger.info("[%s] %s %s", task_id, message, extra)
