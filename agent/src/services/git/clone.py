"""
Clone and branch operations (F2.1–F2.3).
Uses GitPython or subprocess git; clone URL can include token for private repos.
"""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from ...config import get_settings
from ...models.task import TaskContext

logger = logging.getLogger(__name__)


def get_clone_url(task: TaskContext) -> str:
    """
    Build clone URL. For GitHub: https://<token>@github.com/owner/repo.git
    For GitLab: https://oauth2:<token>@gitlab.com/owner/repo.git
    Uses github_token/gitlab_token from settings (no default; MANDATORY for private repos).
    """
    settings = get_settings()
    owner = task.repo_owner
    name = task.repo_name
    if task.provider.value == "github":
        token = settings.github_token
        if token:
            return f"https://x-access-token:{token}@github.com/{owner}/{name}.git"
        return f"https://github.com/{owner}/{name}.git"
    if task.provider.value == "gitlab":
        token = settings.gitlab_token
        base = (settings.gitlab_url or "https://gitlab.com").rstrip("/")
        if token:
            return f"https://oauth2:{token}@{base.replace('https://', '')}/{owner}/{name}.git"
        return f"{base}/{owner}/{name}.git"
    return f"https://github.com/{owner}/{name}.git"


def _run_git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {}), "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        env=full_env,
    )


def clone_repo(clone_url: str, work_dir: Path, branch: str | None = None) -> None:
    """
    Clone repository into work_dir. If branch is set, checkout that branch after clone.
    work_dir must be an empty or non-existent directory (we create parent).
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    if any(work_dir.iterdir()):
        raise FileExistsError(f"Workspace not empty: {work_dir}")

    depth = "--depth=50"  # shallow clone for speed
    args = ["clone", depth, "--single-branch"]
    if branch:
        args.extend(["--branch", branch])
    args.extend([clone_url, str(work_dir)])

    r = _run_git(work_dir.parent, *args)
    if r.returncode != 0:
        logger.error("Clone failed: %s %s", r.stderr, r.stdout)
        raise RuntimeError(f"Git clone failed: {r.stderr or r.stdout}")

    if branch:
        _run_git(work_dir, "checkout", branch)


def create_feature_branch(work_dir: Path, task: TaskContext) -> str:
    """
    Create and checkout feature branch from default_branch.
    Branch name: ai/<ticket-id>-<slug> (slug from title, sanitized).
    Returns the new branch name.
    Handles shallow clones: prefers origin/base, falls back to HEAD if fetch fails.
    """
    work_dir = Path(work_dir)
    base = task.default_branch or "main"
    ticket_slug = re.sub(r"[^a-zA-Z0-9]+", "-", (task.ticket_id + " " + (task.title or ""))[:60]).strip("-") or "task"
    branch_name = f"ai/{ticket_slug}"[:100]

    r = _run_git(work_dir, "fetch", "origin", base)
    if r.returncode == 0:
        _run_git(work_dir, "checkout", "-b", branch_name, f"origin/{base}")
    else:
        # Shallow clone or remote ref missing: create branch from current HEAD
        logger.debug("Fetch origin/%s failed (%s), creating branch from HEAD", base, r.stderr or r.stdout)
        _run_git(work_dir, "checkout", "-b", branch_name)
    return branch_name


def commit(work_dir: Path, message: str) -> None:
    """Stage all changes and commit (F6.1)."""
    work_dir = Path(work_dir)
    r = _run_git(work_dir, "add", "-A")
    if r.returncode != 0:
        raise RuntimeError(f"Git add failed: {r.stderr or r.stdout}")
    r = _run_git(work_dir, "commit", "-m", message)
    if r.returncode != 0:
        if "nothing to commit" in (r.stdout or "") or "nothing to commit" in (r.stderr or ""):
            logger.info("Nothing to commit (working tree clean)")
            return
        raise RuntimeError(f"Git commit failed: {r.stderr or r.stdout}")


def push(work_dir: Path, branch_name: str) -> None:
    """Push branch to origin (F6.2). Remote URL already has credentials from clone."""
    work_dir = Path(work_dir)
    r = _run_git(work_dir, "push", "origin", branch_name)
    if r.returncode != 0:
        logger.error("Push failed: %s %s", r.stderr, r.stdout)
        raise RuntimeError(f"Git push failed: {r.stderr or r.stdout}")
