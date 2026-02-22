"""GitHub provider using PyGitHub (F6)."""

import logging
from typing import Any

from ...config import get_settings
from .provider import GitProviderInterface

logger = logging.getLogger(__name__)


class GitHubProvider(GitProviderInterface):
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            token = get_settings().github_token
            if not token:
                raise ValueError("github_token is not set (MANDATORY for GitHub)")
            try:
                from github import Github
                self._client = Github(token)
            except ImportError as e:
                raise ImportError("Install PyGithub: pip install PyGithub") from e
        return self._client

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
        gh = self._get_client()
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
        )
        if reviewer_logins:
            try:
                pr.create_review_request(reviewers=reviewer_logins)
            except Exception as e:
                logger.warning("Could not set reviewers: %s", e)
        label_name = (get_settings().pr_label_ai_generated or "ai-generated").strip()
        if label_name:
            try:
                repo.get_label(label_name)
            except Exception:
                try:
                    repo.create_label(label_name, "6f7370", "PR created by AI agent")
                except Exception as e:
                    logger.warning("Could not create label %s: %s", label_name, e)
            try:
                pr.add_to_labels(label_name)
            except Exception as e:
                logger.warning("Could not add label: %s", e)
        return {"url": pr.html_url, "number": pr.number, "id": pr.id}

    def add_label_to_pr(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        label: str,
    ) -> None:
        gh = self._get_client()
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        try:
            pr.add_to_labels(label)
        except Exception as e:
            logger.warning("Could not add label to PR: %s", e)
