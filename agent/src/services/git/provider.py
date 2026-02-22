"""
Abstract Git provider and factory (F6: PR creation, reviewers).
Concrete: GitHub (PyGitHub), GitLab (python-gitlab).
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from ...models.task import GitProvider as GitProviderEnum

logger = logging.getLogger(__name__)


class GitProviderInterface(ABC):
    """Abstract interface for Git host operations (PR create, set reviewers, etc.)."""

    @abstractmethod
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
        """Create PR/MR. Returns dict with 'url', 'number', 'id'."""
        ...

    @abstractmethod
    def add_label_to_pr(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        label: str,
    ) -> None:
        """Add label to PR (e.g. ai-generated)."""
        ...


def get_git_provider(provider: GitProviderEnum) -> GitProviderInterface:
    """Return concrete provider for GitHub or GitLab."""
    if provider == GitProviderEnum.GITHUB:
        from .github_provider import GitHubProvider
        return GitHubProvider()
    if provider == GitProviderEnum.GITLAB:
        from .gitlab_provider import GitLabProvider
        return GitLabProvider()
    raise ValueError(f"Unknown provider: {provider}")
