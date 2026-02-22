"""Task and webhook payload models (F1.2, F1.3)."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GitProvider(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"


class TaskContext(BaseModel):
    """Structured task context extracted from webhook (F1.3)."""

    ticket_id: str = Field(..., description="Ticket/issue ID")
    title: str = Field(default="", description="Ticket title")
    description: str = Field(default="", description="Ticket body/description")
    acceptance_criteria: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    reporter: str | None = Field(default=None, description="Ticket reporter (reviewer candidate)")
    project_key: str | None = Field(default=None)
    provider: GitProvider = Field(..., description="Git provider")
    repo_owner: str = Field(..., description="Owner/org or group")
    repo_name: str = Field(..., description="Repository name")
    repo_full_name: str = Field(..., description="e.g. owner/repo or group/repo")
    default_branch: str = Field(default="main")
    raw_payload: dict[str, Any] = Field(default_factory=dict, description="Original payload for traceability")


class WebhookTaskPayload(BaseModel):
    """Parsed webhook payload for task assignment (F1.2)."""

    provider: GitProvider
    repo_owner: str
    repo_name: str
    repo_full_name: str
    default_branch: str = "main"
    ticket_id: str
    title: str = ""
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    reporter: str | None = None
    project_key: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    def to_task_context(self) -> TaskContext:
        return TaskContext(
            ticket_id=self.ticket_id,
            title=self.title,
            description=self.description,
            acceptance_criteria=self.acceptance_criteria,
            labels=self.labels,
            reporter=self.reporter,
            project_key=self.project_key,
            provider=self.provider,
            repo_owner=self.repo_owner,
            repo_name=self.repo_name,
            repo_full_name=self.repo_full_name,
            default_branch=self.default_branch,
            raw_payload=self.raw,
        )
