"""
LLM service: Anthropic Claude (F4.1).
Configurable model; API key from settings (MANDATORY for Phase 2+).
"""

import logging
from typing import Any

from ..config import get_settings

logger = logging.getLogger(__name__)


def _get_client():
    api_key = get_settings().anthropic_api_key
    if not api_key:
        raise ValueError("anthropic_api_key is not set (MANDATORY for Phase 2+)")
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=api_key)
    except ImportError as e:
        raise ImportError("Install anthropic: pip install anthropic") from e


def chat(
    system: str,
    user_message: str,
    *,
    model: str | None = None,
    max_tokens: int = 8192,
) -> str:
    """
    Single turn: system + user message, return assistant text.
    Uses settings.anthropic_model if model is None.
    """
    settings = get_settings()
    model = model or settings.anthropic_model
    client = _get_client()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    text = ""
    for block in resp.content:
        if hasattr(block, "text"):
            text += block.text
    return text.strip()


def chat_multi(
    system: str,
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    max_tokens: int = 8192,
) -> str:
    """
    Multi-turn: system + list of {"role": "user"|"assistant", "content": str}.
    Returns the latest assistant text.
    """
    settings = get_settings()
    model = model or settings.anthropic_model
    client = _get_client()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    text = ""
    for block in resp.content:
        if hasattr(block, "text"):
            text += block.text
    return text.strip()
