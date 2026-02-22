"""
Webhook endpoints (F1.1, F1.4, F1.5, F1.6).
POST /webhook/task — task assignment; returns 201 and processes async.
POST /webhook/pr-comment — PR comment (Phase 4); stub for now.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, Request, status
from fastapi.responses import JSONResponse

from ...models.task import TaskContext
from ...core.pipeline import run_pipeline
from ...services.webhook_parser import parse_task_payload
from ...utils.idempotency import idempotency_check
from ...utils.logging import log_task

logger = logging.getLogger(__name__)

router = APIRouter()


def _task_from_body(
    body: dict[str, Any],
    x_git_provider: str | None = None,
    x_repo: str | None = None,
) -> tuple[TaskContext | None, str | None]:
    """Parse body into task context. Returns (task for pipeline, error_message)."""
    payload = parse_task_payload(body, provider_header=x_git_provider, repo_header=x_repo)
    if not payload:
        return None, "Could not parse task from payload (expected GitHub issue or GitLab issue format, or X-Git-Provider and X-Repo headers)"
    task = payload.to_task_context()
    return task, None


@router.post(
    "/task",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Task accepted and queued"},
        400: {"description": "Bad payload"},
        409: {"description": "Duplicate task (idempotency)"},
    },
)
async def webhook_task(
    request: Request,
    background_tasks: BackgroundTasks,
    x_git_provider: str | None = Header(None, alias="X-Git-Provider"),
    x_repo: str | None = Header(None, alias="X-Repo"),
) -> dict:
    """
    Receive task assignment (Jira/Git). Responds 201 immediately; runs pipeline in background.
    Jira automation can rely on 201 = move ticket to "In Progress" (F1.5).
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("Webhook body not JSON: %s", e)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid JSON body"},
        )

    task, parse_error = _task_from_body(body, x_git_provider=x_git_provider, x_repo=x_repo)
    if parse_error or task is None:
        logger.info("Webhook parse failed: %s", parse_error)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": parse_error},
        )

    if not idempotency_check(task.ticket_id, task.repo_full_name):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "Task already in progress for this ticket and repo"},
        )

    log_task(logger, task.ticket_id, "Webhook accepted", repo=task.repo_full_name)
    background_tasks.add_task(run_pipeline, task)
    return {"status": "accepted", "ticket_id": task.ticket_id, "repo": task.repo_full_name}


@router.post(
    "/pr-comment",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Comment accepted for processing"},
        400: {"description": "Bad payload"},
    },
)
async def webhook_pr_comment(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    PR comment webhook (F7.1). Stub: accept and log; Phase 4 will process.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("PR comment webhook body not JSON: %s", e)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid JSON body"},
        )
    logger.info("PR comment webhook received (stub): keys=%s", list(body.keys()))
    return {"status": "accepted", "message": "PR comment handling (Phase 4) not yet implemented"}
