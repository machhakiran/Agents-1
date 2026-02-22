"""API routes."""

from fastapi import APIRouter

from .health import router as health_router
from .webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api", tags=["api"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(webhooks_router, prefix="/webhook", tags=["webhooks"])

__all__ = ["api_router"]
