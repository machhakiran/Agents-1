"""Health check (for load balancers and readiness)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
@router.get("/")
def health() -> dict:
    return {"status": "ok", "service": "ai-dev-agent"}
