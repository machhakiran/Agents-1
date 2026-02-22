"""
Planning service (F3.1–F3.4).
Produces a structured implementation plan from task context + repo map.
"""

import logging
import re

from ..models.task import TaskContext
from ..models.plan import ImplementationPlan, PlanStep
from .llm import chat
from .prompts import PLANNING_SYSTEM, PLANNING_USER_TEMPLATE

logger = logging.getLogger(__name__)

# Match "FILE: path" then "ACTION: create|modify|delete" then "REASON: ..."
RE_STEP = re.compile(
    r"(?m)^[-*]?\s*FILE:\s*(.+?)\s*$"
    r"\s*ACTION:\s*(create|modify|delete)\s*$"
    r"\s*REASON:\s*(.+?)(?=\n(?:[-*]?\s*FILE:|\s*SUMMARY:|\Z))",
    re.DOTALL | re.IGNORECASE,
)
RE_SUMMARY = re.compile(r"(?m)^\s*SUMMARY:\s*(.+?)\Z", re.DOTALL | re.IGNORECASE)


def create_plan(task: TaskContext, repo_map: str) -> ImplementationPlan:
    """
    Call Claude with task + repo_map; parse response into ImplementationPlan (F3.1, F3.2).
    Plan is stored in returned object for traceability (F3.3).
    """
    acceptance_section = ""
    if task.acceptance_criteria:
        acceptance_section = "Acceptance criteria:\n" + "\n".join(
            f"- {c}" for c in task.acceptance_criteria
        )

    user_msg = PLANNING_USER_TEMPLATE.format(
        ticket_id=task.ticket_id,
        title=task.title or "(no title)",
        description=task.description or "(no description)",
        acceptance_section=acceptance_section,
        repo_map=repo_map or "(no map)",
    )

    raw = chat(system=PLANNING_SYSTEM, user_message=user_msg, max_tokens=4096)
    steps: list[PlanStep] = []
    for m in RE_STEP.finditer(raw):
        file_path = m.group(1).strip()
        action = m.group(2).strip().lower()
        if action not in ("create", "modify", "delete"):
            action = "modify"
        reason = m.group(3).strip().split("\n")[0]
        steps.append(PlanStep(file_path=file_path, action=action, reason=reason))

    summary = ""
    sm = RE_SUMMARY.search(raw)
    if sm:
        summary = sm.group(1).strip().split("\n")[0]

    return ImplementationPlan(steps=steps, summary=summary)
