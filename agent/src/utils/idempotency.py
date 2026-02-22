"""
Idempotency for webhook handling (F1.6).
Memory backend: in-process set. Redis: use key = f"task:{ticket_id}:{repo_full_name}".
"""

import logging
from typing import Callable

from ..config import get_settings

logger = logging.getLogger(__name__)

# In-memory set of (ticket_id, repo_full_name) currently being processed
_in_progress: set[tuple[str, str]] = set()


def _key(ticket_id: str, repo_full_name: str) -> tuple[str, str]:
    return (ticket_id.strip(), repo_full_name.strip())


def idempotency_check(ticket_id: str, repo_full_name: str) -> bool:
    """
    Return True if this task can proceed (not already in progress).
    If True, caller should call idempotency_release when done.
    """
    settings = get_settings()
    if settings.idempotency_backend == "redis":
        # TODO: Redis GET/SET with NX and TTL (e.g. task_timeout_seconds)
        logger.warning("Redis idempotency not implemented; using memory")
    k = _key(ticket_id, repo_full_name)
    if k in _in_progress:
        logger.info("Idempotency: task already in progress ticket_id=%s repo=%s", ticket_id, repo_full_name)
        return False
    _in_progress.add(k)
    return True


def idempotency_release(ticket_id: str, repo_full_name: str) -> None:
    """Release idempotency lock after task completion (success or failure)."""
    k = _key(ticket_id, repo_full_name)
    _in_progress.discard(k)
