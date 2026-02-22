"""
Webhook payload parsing (F1.2, F1.3).
Supports GitHub/GitLab issue-assignment style payloads and generic JSON body + headers.
"""

import logging
from typing import Any

from ..models.task import GitProvider, WebhookTaskPayload

logger = logging.getLogger(__name__)


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _safe_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if x]
    return []


def parse_github_issue(body: dict[str, Any]) -> WebhookTaskPayload | None:
    """Parse GitHub issue/assign event. Expects 'issue' and optionally 'repository'."""
    issue = body.get("issue") or body.get("pull_request")
    repo = body.get("repository") or {}
    if not issue:
        return None

    repo_full = repo.get("full_name") or _safe_str(repo.get("name", ""))
    if "/" not in repo_full:
        owner = _safe_str(repo.get("owner", {}).get("login") or repo.get("owner"))
        name = _safe_str(repo.get("name", ""))
        repo_full = f"{owner}/{name}" if owner and name else repo_full
    parts = repo_full.split("/", 1)
    owner = parts[0] if len(parts) > 1 else ""
    name = parts[1] if len(parts) > 1 else parts[0]

    number = issue.get("number") or issue.get("id")
    ticket_id = f"#{number}" if number is not None else _safe_str(issue.get("id"))

    assignees = issue.get("assignees") or []
    reporter = None
    if assignees:
        reporter = assignees[0].get("login") if isinstance(assignees[0], dict) else str(assignees[0])
    if not reporter:
        reporter = (issue.get("user") or {}).get("login")

    labels = _safe_list([l.get("name") if isinstance(l, dict) else l for l in (issue.get("labels") or [])])
    body_text = issue.get("body") or ""

    return WebhookTaskPayload(
        provider=GitProvider.GITHUB,
        repo_owner=owner,
        repo_name=name,
        repo_full_name=repo_full,
        default_branch=(repo.get("default_branch") or "main"),
        ticket_id=ticket_id,
        title=_safe_str(issue.get("title", "")),
        description=body_text,
        acceptance_criteria=[body_text] if body_text else [],
        labels=labels,
        reporter=reporter,
        project_key=None,
        raw=body,
    )


def parse_gitlab_issue(body: dict[str, Any]) -> WebhookTaskPayload | None:
    """Parse GitLab issue/merge request hook. Expects 'object_attributes' and 'project'."""
    attrs = body.get("object_attributes") or {}
    project = body.get("project") or {}
    if not attrs:
        return None

    path_with_namespace = project.get("path_with_namespace") or _safe_str(project.get("path", ""))
    parts = path_with_namespace.split("/", 1)
    owner = parts[0] if len(parts) > 1 else ""
    name = parts[1] if len(parts) > 1 else path_with_namespace

    iid = attrs.get("iid") or attrs.get("id")
    ticket_id = f"!{iid}" if iid is not None else _safe_str(attrs.get("id"))

    assignee = body.get("assignee") or (body.get("assignees") or [{}])[0] if body.get("assignees") else None
    reporter = assignee.get("username") if isinstance(assignee, dict) else None
    if not reporter:
        author = attrs.get("author_id")
        # GitLab may include 'user' or we'd need to look up; use author_id as fallback
        reporter = str(author) if author else None

    labels = _safe_list([l.get("title") if isinstance(l, dict) else l for l in (body.get("labels") or [])])

    return WebhookTaskPayload(
        provider=GitProvider.GITLAB,
        repo_owner=owner,
        repo_name=name,
        repo_full_name=path_with_namespace,
        default_branch=(project.get("default_branch") or "main"),
        ticket_id=ticket_id,
        title=_safe_str(attrs.get("title", "")),
        description=_safe_str(attrs.get("description", "")),
        acceptance_criteria=[],
        labels=labels,
        reporter=reporter,
        project_key=project.get("path_with_namespace"),
        raw=body,
    )


def parse_task_payload(
    body: dict[str, Any],
    provider_header: str | None = None,
    repo_header: str | None = None,
) -> WebhookTaskPayload | None:
    """
    Parse webhook body into WebhookTaskPayload.
    If provider_header/repo_header are set (e.g. X-Git-Provider: github, X-Repo: owner/repo),
    use them; otherwise try GitHub then GitLab payload shapes.
    """
    provider = (provider_header or "").strip().lower() or None
    repo_full = (repo_header or "").strip()

    if provider == "github" or (not provider and body.get("issue") is not None):
        parsed = parse_github_issue(body)
    elif provider == "gitlab" or (not provider and body.get("object_attributes") is not None):
        parsed = parse_gitlab_issue(body)
    else:
        parsed = parse_github_issue(body) or parse_gitlab_issue(body)

    if not parsed:
        return None

    if repo_full and "/" in repo_full:
        p = repo_full.split("/", 1)
        parsed.repo_owner = p[0]
        parsed.repo_name = p[1]
        parsed.repo_full_name = repo_full

    return parsed
