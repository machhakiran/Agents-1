"""FastAPI dependencies."""

from ..config import get_settings

def get_config():
    return get_settings()
