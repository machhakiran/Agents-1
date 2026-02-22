"""
Application settings with defaults. Mandatory secrets must be set via env.
See README_CREDENTIALS.md for which credentials are MANDATORY vs default.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central config; load from env and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----- App -----
    app_name: str = Field(default="ai-dev-agent", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    # ----- Server -----
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8000, description="Bind port")

    # ----- Webhook / Idempotency -----
    # Default: in-memory set for dedup (single instance). Production: use Redis key.
    idempotency_backend: Literal["memory", "redis"] = Field(
        default="memory", description="Idempotency backend"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL when idempotency_backend=redis",
    )

    # ----- Git provider -----
    git_provider: Literal["github", "gitlab"] = Field(
        default="github", description="Default Git provider"
    )
    default_branch: str = Field(default="main", description="Default branch to base from")

    # ----- MANDATORY: Git / GitHub (when git_provider=github) -----
    # GitHub Personal Access Token with repo scope. No default in production.
    github_token: str = Field(default="", description="[MANDATORY for GitHub] PAT with repo scope")

    # ----- MANDATORY: Git / GitLab (when git_provider=gitlab) -----
    gitlab_token: str = Field(default="", description="[MANDATORY for GitLab] Access token")
    gitlab_url: str = Field(
        default="https://gitlab.com",
        description="GitLab instance URL (default: gitlab.com)",
    )

    # ----- Optional: Git clone (defaults for local/dev) -----
    # For private repos over HTTPS; leave empty if using SSH or token in URL.
    git_username: str = Field(default="", description="Git clone username (optional)")
    git_password: str = Field(default="", description="Git clone password (optional)")

    # ----- MANDATORY for Phase 2+: Anthropic -----
    anthropic_api_key: str = Field(
        default="",
        description="[MANDATORY for code gen] Anthropic API key for Claude",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Claude model (e.g. claude-sonnet-4-20250514, claude-3-5-sonnet-20241022)",
    )

    # ----- Pipeline -----
    workspace_base: str = Field(
        default="/tmp/ai_agent_workspaces",
        description="Base directory for clone workspaces",
    )
    max_validation_retries: int = Field(default=5, description="Max self-healing retries (F5)")
    task_timeout_seconds: int = Field(default=1800, description="Max seconds per task run")
    pr_label_ai_generated: str = Field(default="ai-generated", description="PR label for agent PRs")

    # ----- Jira (optional; for status sync) -----
    jira_base_url: str = Field(default="", description="Jira base URL (e.g. https://your.atlassian.net)")
    jira_username: str = Field(default="", description="Jira user for API (optional)")
    jira_api_token: str = Field(default="", description="Jira API token (optional)")


@lru_cache
def get_settings() -> Settings:
    return Settings()
