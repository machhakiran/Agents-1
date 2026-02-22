"""FastAPI application entry. Run: uvicorn src.main:app --reload (from agent/)."""

import uvicorn

from .api.routes import api_router
from .config import get_settings
from .utils.logging import configure_logging
from fastapi import FastAPI

settings = get_settings()
configure_logging(level=settings.log_level, debug=settings.debug)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Autonomous AI Development Agent — Jira/Git ticket to PR",
)

app.include_router(api_router)


def main() -> None:
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
