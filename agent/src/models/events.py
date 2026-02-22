"""Event models for webhooks (e.g. PR comments)."""

from pydantic import BaseModel, Field


class PRCommentPayload(BaseModel):
    """Parsed PR comment webhook (F7.1)."""

    provider: str = Field(..., description="github | gitlab")
    repo_owner: str = ""
    repo_name: str = ""
    repo_full_name: str = ""
    pr_number: int = Field(..., description="Pull request number")
    comment_id: str | int = Field(..., description="Comment ID")
    comment_body: str = Field(..., description="Comment text")
    comment_author: str = ""
    pr_author: str = ""
    pr_branch: str = ""
    pr_base_branch: str = "main"
    file_path: str | None = None
    line_number: int | None = None
    raw: dict = Field(default_factory=dict)
