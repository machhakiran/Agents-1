"""GitLab provider using python-gitlab (F6)."""

import logging
from typing import Any

from ...config import get_settings
from .provider import GitProviderInterface

logger = logging.getLogger(__name__)


class GitLabProvider(GitProviderInterface):
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            token = get_settings().gitlab_token
            url = get_settings().gitlab_url or "https://gitlab.com"
            if not token:
                raise ValueError("gitlab_token is not set (MANDATORY for GitLab)")
            try:
                import gitlab
                self._client = gitlab.Gitlab(url, private_token=token)
                self._client.auth()
            except ImportError as e:
                raise ImportError("Install python-gitlab: pip install python-gitlab") from e
        return self._client

    def _get_project(self, repo_owner: str, repo_name: str):
        gl = self._get_client()
        full_path = f"{repo_owner}/{repo_name}"
        return gl.projects.get(full_path)

    def create_pull_request(
        self,
        repo_owner: str,
        repo_name: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
        reviewer_logins: list[str] | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        project = self._get_project(repo_owner, repo_name)
        label_name = (get_settings().pr_label_ai_generated or "ai-generated").strip()
        mr_labels = list(labels or [])
        if label_name and label_name not in mr_labels:
            mr_labels.append(label_name)
        mr = project.mergerequests.create(
            {
                "source_branch": head_branch,
                "target_branch": base_branch,
                "title": title,
                "description": body,
                "labels": mr_labels,
            }
        )
        if reviewer_logins:
            try:
                mr.assignee_ids = []  # Could resolve user IDs from logins
            except Exception as e:
                logger.warning("Could not set assignees: %s", e)
        return {"url": mr.web_url, "number": mr.iid, "id": mr.id}

    def add_label_to_pr(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        label: str,
    ) -> None:
        project = self._get_project(repo_owner, repo_name)
        mr = project.mergerequests.get(pr_number)
        try:
            mr.labels.append(label)
            mr.save()
        except Exception as e:
            logger.warning("Could not add label to MR: %s", e)
