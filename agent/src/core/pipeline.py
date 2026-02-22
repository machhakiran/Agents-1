"""
Main pipeline: webhook task → clone → branch → map → plan → implement → validate (loop) → deliver.
Phase 3: validation loop. Phase 4: commit, push, PR.
"""

import logging
import shutil
import uuid
from pathlib import Path

from ..config import get_settings
from ..models.task import TaskContext
from ..services.git import (
    clone_repo,
    create_feature_branch,
    get_clone_url,
    get_git_provider,
    commit,
    push,
)
from ..services.codebase_map import build_map
from ..services.planner import create_plan
from ..services.implementer import implement
from ..services.validator import run_validation
from ..utils.idempotency import idempotency_release
from ..utils.logging import log_task

logger = logging.getLogger(__name__)


def _pr_body(task: TaskContext) -> str:
    """Build PR description from task (F6.4)."""
    parts = [f"**Ticket:** {task.ticket_id}", f"**Title:** {task.title or '(no title)'}", ""]
    if task.description:
        parts.append("## Description\n")
        parts.append(task.description.strip())
        parts.append("")
    if task.acceptance_criteria:
        parts.append("## Acceptance criteria")
        for c in task.acceptance_criteria:
            parts.append(f"- {c}")
    return "\n".join(parts)


def run_pipeline(task: TaskContext) -> None:
    """
    Run the full pipeline: clone → branch → map → plan → implement → validate (retry) → commit → push → PR.
    Cleans up workspace in finally. Delivery (F6) only when validation passes (F5.6).
    """
    run_id = str(uuid.uuid4())[:8]
    log_task(logger, task.ticket_id, "Pipeline started", run_id=run_id)

    base = Path(get_settings().workspace_base)
    base.mkdir(parents=True, exist_ok=True)
    work_dir = base / f"{task.repo_name}_{run_id}_{task.ticket_id.replace('#', '').replace('!', '')}"
    settings = get_settings()
    branch_name: str | None = None
    repo_map = ""
    plan = None
    validation_passed = False

    try:
        clone_url = get_clone_url(task)
        clone_repo(clone_url, work_dir, branch=task.default_branch or None)
        branch_name = create_feature_branch(work_dir, task)
        log_task(logger, task.ticket_id, "Clone and branch ready", branch=branch_name, run_id=run_id)

        if not settings.anthropic_api_key:
            logger.info("[%s] Phase 2 skipped (no ANTHROPIC_API_KEY)", task.ticket_id)
        else:
            repo_map = build_map(work_dir)
            log_task(logger, task.ticket_id, "Codebase map built", run_id=run_id)
            plan = create_plan(task, repo_map)
            log_task(logger, task.ticket_id, "Plan created", steps=len(plan.steps), run_id=run_id)
            implement(work_dir, task, repo_map, plan)
            log_task(logger, task.ticket_id, "Implementation applied", run_id=run_id)

            # Phase 3: validation loop (F5.4, F5.5)
            for attempt in range(settings.max_validation_retries + 1):
                result = run_validation(work_dir, timeout=min(300, settings.task_timeout_seconds))
                if result.success:
                    validation_passed = True
                    log_task(logger, task.ticket_id, "Validation passed", attempt=attempt + 1, run_id=run_id)
                    break
                log_task(logger, task.ticket_id, "Validation failed, self-heal attempt", attempt=attempt + 1, run_id=run_id)
                if attempt < settings.max_validation_retries and plan and plan.steps:
                    implement(work_dir, task, repo_map, plan, feedback=result.feedback)
                else:
                    logger.warning("[%s] Validation failed after max retries; skipping PR", task.ticket_id)
                    break

        # Phase 4: deliver only when validation passed and we have code changes (Phase 2 ran)
        if (
            validation_passed
            and branch_name
            and settings.anthropic_api_key
            and (settings.github_token or settings.gitlab_token)
        ):
            commit_message = f"{task.ticket_id}: {task.title or 'Implement task'}"[:200]
            commit(work_dir, commit_message)
            push(work_dir, branch_name)
            provider = get_git_provider(task.provider)
            pr = provider.create_pull_request(
                repo_owner=task.repo_owner,
                repo_name=task.repo_name,
                head_branch=branch_name,
                base_branch=task.default_branch or "main",
                title=f"{task.ticket_id}: {task.title or 'Implement task'}"[:256],
                body=_pr_body(task),
                reviewer_logins=[task.reporter] if task.reporter else None,
                labels=[settings.pr_label_ai_generated] if settings.pr_label_ai_generated else None,
            )
            log_task(logger, task.ticket_id, "PR created", pr_url=pr.get("url"), run_id=run_id)
    finally:
        if work_dir.exists():
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception as e:
                logger.warning("Cleanup workspace %s: %s", work_dir, e)
        idempotency_release(task.ticket_id, task.repo_full_name)
