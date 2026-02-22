"""
Implementation service (F4.2–F4.5).
Uses Claude to generate edits from task + map + plan; applies edits to workspace.
No aider dependency: we parse EDIT_FILE blocks and write/update files directly.
"""

import logging
import re
from pathlib import Path

from ..models.task import TaskContext
from ..models.plan import ImplementationPlan
from .llm import chat
from .prompts import (
    IMPLEMENTATION_SYSTEM,
    IMPLEMENTATION_USER_TEMPLATE,
    IMPLEMENTATION_FEEDBACK_APPENDIX,
)

logger = logging.getLogger(__name__)

# Match EDIT_FILE: path then ```lang\ncontent\n```
RE_EDIT = re.compile(
    r"(?m)^EDIT_FILE:\s*(.+?)\s*$\s*```(?:new|\w+)\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _read_file_safe(work_dir: Path, rel_path: str, max_lines: int = 500) -> str:
    """Read file content for context; truncate if large."""
    p = work_dir / rel_path
    if not p.is_file():
        return "(file not found)"
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
        lines = raw.splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + "\n... (truncated)"
        return raw
    except Exception as e:
        return f"(read error: {e})"


def _gather_file_contents(work_dir: Path, plan: ImplementationPlan) -> str:
    """Build a block of file contents for files in the plan (modify/delete need current content)."""
    parts: list[str] = []
    for step in plan.steps:
        if step.action == "create":
            parts.append(f"### {step.file_path} (new)\n(no existing content)\n")
        else:
            content = _read_file_safe(work_dir, step.file_path)
            parts.append(f"### {step.file_path}\n{content}\n")
    return "\n".join(parts)


def _apply_edits(work_dir: Path, raw_response: str) -> list[str]:
    """
    Parse EDIT_FILE blocks and apply to workspace. Returns list of modified paths.
    """
    applied: list[str] = []
    for m in RE_EDIT.finditer(raw_response):
        rel_path = m.group(1).strip()
        content = m.group(2).rstrip()
        if ".." in rel_path or rel_path.startswith("/"):
            logger.warning("Skipping unsafe path: %s", rel_path)
            continue
        full = work_dir / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        applied.append(rel_path)
    return applied


def implement(
    work_dir: Path,
    task: TaskContext,
    repo_map: str,
    plan: ImplementationPlan,
    feedback: str | None = None,
) -> list[str]:
    """
    Generate implementation from task + map + plan; apply edits to work_dir (F4.2–F4.5).
    If feedback is set (self-heal), append validation feedback and ask for fixes (F5.4).
    Returns list of file paths that were created or modified.
    """
    if not plan.steps and not feedback:
        logger.info("No plan steps; skipping implementation")
        return []

    plan_text = plan.summary or ""
    for s in plan.steps:
        plan_text += f"\n- {s.file_path}: {s.action} — {s.reason}"

    file_contents = _gather_file_contents(work_dir, plan) if plan.steps else "(no plan; fix issues below)"

    user_msg = IMPLEMENTATION_USER_TEMPLATE.format(
        ticket_id=task.ticket_id,
        title=task.title or "(no title)",
        description=task.description or "(no description)",
        plan_text=plan_text or "(fix validation issues only)",
        repo_map=repo_map or "(no map)",
        file_contents=file_contents,
    )
    if feedback:
        user_msg += IMPLEMENTATION_FEEDBACK_APPENDIX.format(feedback=feedback)

    raw = chat(
        system=IMPLEMENTATION_SYSTEM,
        user_message=user_msg,
        max_tokens=16384,
    )

    applied = _apply_edits(work_dir, raw)
    logger.info("Applied edits to %s files: %s", len(applied), applied)
    return applied
