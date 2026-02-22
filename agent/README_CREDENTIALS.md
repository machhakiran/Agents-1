# Credentials: Defaults vs MANDATORY

Use **defaults** where possible for local/dev. The following must be set in **production** or when using the relevant feature.

---

## MANDATORY (no safe default)

| Variable | When required | Notes |
|----------|----------------|--------|
| **GITHUB_TOKEN** | GitHub as Git provider (clone private repos, create PRs) | Personal Access Token with `repo` scope. **Never** commit; use env or secret manager. |
| **GITLAB_TOKEN** | GitLab as Git provider | Project/Group access token or Personal Access Token. |
| **ANTHROPIC_API_KEY** | Phase 2+ (code generation, planning) | Required for Claude API. No default. |

For **public repos only** (clone without PR creation), you can leave `GITHUB_TOKEN` empty for clone if you use public HTTPS URLs; PR creation and private clone will still require a token.

---

## Optional / Defaults

| Variable | Default | Purpose |
|----------|---------|---------|
| GIT_USERNAME | *(empty)* | Git HTTPS username (only if not using token in URL). |
| GIT_PASSWORD | *(empty)* | Git HTTPS password (only if not using token in URL). |
| GITLAB_URL | `https://gitlab.com` | GitLab instance URL. |
| JIRA_* | *(empty)* | Jira base URL, username, API token — only for Jira status sync (e.g. move to "In Progress"). |
| REDIS_URL | `redis://localhost:6379/0` | Used when `IDEMPOTENCY_BACKEND=redis`. |
| WORKSPACE_BASE | `/tmp/ai_agent_workspaces` | Base path for clone workspaces. |

---

## Summary

- **Phase 1 (webhook + clone + branch):**  
  **MANDATORY** for private repos: `GITHUB_TOKEN` or `GITLAB_TOKEN` (depending on provider).  
  Optional: Jira credentials if you want 201 → "In Progress" in Jira.

- **Phase 2+ (code gen, PR creation):**  
  **MANDATORY:** `GITHUB_TOKEN` or `GITLAB_TOKEN` (for push/PR) and **ANTHROPIC_API_KEY** (for Claude).

- **Default user/password:**  
  No default **user/password** for Git in production; use **tokens** (GITHUB_TOKEN / GITLAB_TOKEN) in clone URLs.  
  `GIT_USERNAME` / `GIT_PASSWORD` are only for custom HTTPS auth when you cannot use token-in-URL.
