# Full Functional Plan: Autonomous AI Development Agent

**Sources:** [AI_Agent_PDR.md](./AI_Agent_PDR.md) · [deepsense.ai: From Jira to PR – Claude-Powered AI Agents](https://deepsense.ai/blog/from-jira-to-pr-claude-powered-ai-agents-that-code-test-and-review-for-you/)

This document is a **build-ready functional plan** that merges the PDR requirements with proven implementation patterns from production AI Teammate-style systems.

---

## 1. System Overview

| Aspect | Specification |
|--------|----------------|
| **Role** | Autonomous “junior developer” from ticket → PR, no IDE required |
| **Trigger** | Webhook on ticket assignment (Jira / GitHub / GitLab) |
| **Stack** | FastAPI (Python), Docker, Google Cloud Run |
| **LLM** | Anthropic Claude (3.7 Sonnet / 4.0) |
| **Code engine** | `aider` for codebase mapping and incremental edits |
| **Git** | PyGitHub (GitHub), python-gitlab (GitLab) |

**End-to-end flow (high level):**  
Ticket assigned → Webhook → Clone repo → Map codebase → Plan → Implement → Lint/Test (retry until pass) → Commit/Push → Open PR → (Optional) Handle PR comments.

---

## 2. Functional Components & Build Plan

### 2.1. Trigger & Ingestion (Webhook Layer)

**Goal:** Accept task assignments from Jira/Git, respond immediately, process work async.

| # | Function | Description | Acceptance Criteria |
|---|----------|-------------|---------------------|
| F1.1 | **Webhook endpoint** | Single FastAPI route (e.g. `POST /webhook/task`) that receives Jira/Git payloads | Returns `201 Created` quickly; request body and headers logged |
| F1.2 | **Payload parsing** | Parse provider (GitHub/GitLab), repo path, ticket ID, and optional params from headers/body | Correct provider + repo + ticket ID extracted for downstream use |
| F1.3 | **Context extraction** | From payload: title, description, acceptance criteria, labels, reporter | Structured “task context” object available for planning and PR description |
| F1.4 | **Async processing** | Enqueue job (e.g. background task / queue) and return 201 without waiting for implementation | No blocking of webhook response; work runs in worker/background |
| F1.5 | **Status sync (Jira)** | On successful 201, automation rule moves ticket to “In Progress” | Documented contract so Jira automation can rely on 201 = “accepted” |
| F1.6 | **Idempotency / dedup** | Same ticket/repo not processed twice concurrently (e.g. by ticket ID + repo) | Duplicate assignments do not spawn duplicate pipelines |

**Implementation notes:**

- Use FastAPI `BackgroundTasks` or a task queue (e.g. Celery, Cloud Tasks) for async execution.
- Keep webhook handler thin: validate → extract → enqueue → return 201.

---

### 2.2. Repository Operations & Codebase Mapping

**Goal:** Isolated clone, branch creation, and semantic map for planning.

| # | Function | Description | Acceptance Criteria |
|---|----------|-------------|---------------------|
| F2.1 | **Resolve repository** | Map ticket/project to Git repo URL (config or payload) | Correct clone URL and default branch (e.g. `main`) determined |
| F2.2 | **Clone in isolation** | Clone into a temporary directory (or container filesystem) per task | No cross-task file sharing; cleanup after run |
| F2.3 | **Branch creation** | Create feature branch from `main` (e.g. `ai/<ticket-id>-short-description`) | Branch exists locally and naming is consistent and traceable |
| F2.4 | **Semantic map (aider)** | Use aider to generate map: key files, classes, functions, modules | Map covers structure and symbols needed for planning |
| F2.5 | **Map caching (optional)** | Cache map by repo + commit for same-repo tasks | Reduces duplicate mapping for multiple tickets in same repo |

**Implementation notes:**

- Use `aider`’s codebase-indexing/mapping capabilities; feed map into planning prompt.
- Enforce isolated workspaces (temp dir per run or separate container per job).

---

### 2.3. Planning (Pre-Implementation)

**Goal:** Turn task + codebase map into a concrete implementation plan for the LLM.

| # | Function | Description | Acceptance Criteria |
|---|----------|-------------|---------------------|
| F3.1 | **Plan generation** | LLM (Claude) produces a step-by-step plan: files to create/modify and rationale | Plan is structured (e.g. list of file + action + short reason) |
| F3.2 | **Plan inputs** | Plan uses: task context (F1.3), semantic map (F2.4), repo structure | No code written yet; only plan produced |
| F3.3 | **Plan storage** | Plan stored (e.g. in run state or log) for traceability and PR description | Plan recoverable for debugging and documentation |
| F3.4 | **Strict instructions in prompt** | System prompt includes: clean code, no TODOs/placeholders, performance considerations | Same instructions used in implementation phase |

**Implementation notes:**

- One dedicated “planning” call to Claude with ticket + map; output parsed into a structured plan.
- This plan is then injected into the implementation prompt (next phase).

---

### 2.4. AI-Powered Code Generation (Implementation)

**Goal:** Implement changes incrementally using Claude and aider.

| # | Function | Description | Acceptance Criteria |
|---|----------|-------------|---------------------|
| F4.1 | **LLM integration** | All code-generation calls use Anthropic API (Claude 3.7 Sonnet or 4.0) | Configurable model; API key from secrets |
| F4.2 | **Implementation prompt** | Prompt includes: task context, semantic map, implementation plan, strict coding rules | Single “implementation” prompt specification documented |
| F4.3 | **aider-driven edits** | Use aider to apply edits (add/modify/delete files) based on LLM output | Changes applied in repo workspace without manual file writes |
| F4.4 | **Incremental steps** | Implementation can be broken into multiple LLM + aider steps (e.g. by file or by sub-task) | Supports multi-file and multi-step changes |
| F4.5 | **Context window usage** | Stay within model context limits; use map + plan + relevant file chunks | No silent truncation of critical context |

**Implementation notes:**

- Blog and PDR emphasize “incremental, structured reasoning” and aider; keep prompts and tool use aligned with that.

---

### 2.5. Validation & Self-Correction Loop

**Goal:** Run repo linters and tests; on failure, feed errors back to Claude and retry until pass or max iterations.

| # | Function | Description | Acceptance Criteria |
|---|----------|-------------|---------------------|
| F5.1 | **Run linters** | Execute repo linter (e.g. from `package.json` / `Makefile` / `pyproject.toml`) in workspace | Linter exit code and stdout/stderr captured |
| F5.2 | **Run tests** | Execute repo test suite (e.g. `pytest`, `npm test`) in workspace | Test exit code and output captured |
| F5.3 | **Structured feedback** | On failure, format linter/test output into a concise “feedback” block for the LLM | Claude receives clear description of what failed and where |
| F5.4 | **Self-healing loop** | Send feedback to Claude, get new edits via aider, re-run linter + tests | Loop continues until both pass or max iterations (e.g. 5) |
| F5.5 | **Timeout / max retries** | Configurable max retries and overall job timeout | No infinite loops; task fails cleanly after limit |
| F5.6 | **Success gate** | Only proceed to “Delivery” when linter and tests pass | No PR opened on failed validation |

**Implementation notes:**

- Detection of “how to run linter/tests” can be convention-based (e.g. `npm run lint`, `pytest`, `make test`) or configurable per repo.

---

### 2.6. Delivery (Commit, Push, PR)

**Goal:** Commit changes, push branch, open PR with traceability and correct metadata.

| # | Function | Description | Acceptance Criteria |
|---|----------|-------------|---------------------|
| F6.1 | **Commit** | Single commit (or minimal commits) with message derived from ticket title/ID | Commit message references ticket and is descriptive |
| F6.2 | **Push** | Push feature branch to remote (GitHub/GitLab) using credentials from secrets | Branch visible on remote |
| F6.3 | **PR creation** | Open PR: base = `main`, head = feature branch | PR created via PyGitHub / python-gitlab |
| F6.4 | **PR title & description** | Title and body from ticket (title, description, acceptance criteria, link) | Traceability from PR back to ticket |
| F6.5 | **PR label** | Add label (e.g. `ai-generated`) to the PR | Label configurable; used for filtering/reporting |
| F6.6 | **Reviewer assignment** | Set reviewer(s): e.g. ticket reporter or configured tech leads | Assignee field set via API |
| F6.7 | **PR author** | PR author is the bot/service account used by the agent | Consistent “author” for all agent PRs |

**Implementation notes:**

- Use PyGitHub for GitHub and python-gitlab for GitLab; abstract behind a small “GitProvider” interface if supporting both.

---

### 2.7. PR Feedback Loop (Post-PR)

**Goal:** React to PR comments by updating code and pushing new commits.

| # | Function | Description | Acceptance Criteria |
|---|----------|-------------|---------------------|
| F7.1 | **PR comment webhook** | Separate endpoint (e.g. `POST /webhook/pr-comment`) for comment events from GitHub/GitLab | Payload parsed for repo, PR ID, comment body, author |
| F7.2 | **Filter by assignee/label** | Only process comments on PRs created by the agent (e.g. by author or `ai-generated` label) | Avoid reacting to unrelated PRs |
| F7.3 | **Context retrieval** | Load PR branch, current diff, and comment location (file, line) | Agent has full context for the suggested change |
| F7.4 | **LLM resolution** | Claude proposes code change to address comment (inline or general) | Edits produced in same format as main implementation (e.g. via aider) |
| F7.5 | **Apply & push** | Apply edits, run linter/tests (short loop), commit and push to same PR branch | PR updated with new commit(s) |
| F7.6 | **Optional: reply to comment** | Post a reply (e.g. “Fixed in commit X”) for transparency | Configurable; respects provider API limits |

**Implementation notes:**

- For “suggestions in a separate branch” (blog): optional flow where agent opens a new branch/PR linked to original PR and assigns same reviewer; can be Phase 4b.

---

### 2.8. Non-Functional & Cross-Cutting

**Security & secrets**

- All API keys (Anthropic, GitHub, GitLab, Jira) in a secure store (e.g. Cloud Secret Manager / vault).
- No secrets in code or logs; use env vars or runtime secret injection.

**Isolation**

- Each task runs in its own temp directory or container; no shared mutable state between tasks.
- Clone/run/cleanup lifecycle clearly defined.

**Traceability**

- Log: ticket ID, repo, branch, plan summary, validation results, PR URL, and timestamps.
- Optionally store minimal run metadata (e.g. in DB) for “list runs” or debugging.

**Observability**

- Metrics: webhooks received, tasks started/completed/failed, retry counts, PRs opened.
- Alerts on repeated failures or webhook errors.

---

## 3. Implementation Phases (Aligned with PDR Roadmap)

### Phase 1: Foundation (Webhook + Git API)

- Implement F1.1–F1.4 (webhook endpoint, parsing, async processing).
- Implement F2.1–F2.3 (resolve repo, clone, create branch) using PyGitHub/python-gitlab.
- Add F1.5 (contract for Jira status update on 201).
- **Deliverable:** Service that accepts a webhook, clones repo, creates branch, and exits (no code gen yet).

### Phase 2: Agent Core (Map + Plan + Implement)

- Integrate Anthropic API and configure Claude model (F4.1).
- Integrate aider for semantic map (F2.4) and for applying edits (F4.3, F4.4).
- Implement planning (F3.1–F3.4) and implementation prompt (F4.2, F4.5).
- **Deliverable:** End-to-end from webhook to implemented (but not yet validated) code in workspace.

### Phase 3: Validation Loop

- Implement F5.1–F5.6 (run linter/tests, feedback format, self-healing loop, timeouts).
- Gate “Delivery” on F5.6 (success gate).
- **Deliverable:** Agent that only proceeds to PR when linter and tests pass (with retries).

### Phase 4: Delivery & PR Feedback

- Implement F6.1–F6.7 (commit, push, PR creation, title/description, label, reviewers).
- Implement F7.1–F7.5 (PR comment webhook, filter, context, LLM resolution, apply & push).
- **Deliverable:** Full ticket → PR flow plus autonomous handling of PR comments.

### Phase 5: Deployment & Hardening

- Dockerize app (multi-stage build, non-root user).
- Deploy to Google Cloud Run; wire secrets and env.
- Add idempotency (F1.6), optional map caching (F2.5), and observability.
- Run benchmark tickets and tune system prompts (plan + implementation).
- **Deliverable:** Production-ready service with docs and runbooks.

---

## 4. Component Dependency Overview

```
Webhook (F1) → Clone & Map (F2) → Plan (F3) → Implement (F4) → Validate (F5) → Deliver (F6)
                                                                                    ↓
PR Comment Webhook (F7) ←───────────────────────────────────────────────────────────┘
```

- **F1** must be in place before any other component.
- **F2** is required for F3 and F4.
- **F3** output is required for F4.
- **F4** and **F5** are coupled (implement → validate → optional retry → F4 again).
- **F6** runs only after F5 succeeds.
- **F7** is independent of the main pipeline but uses the same F2/F4/F5 building blocks for “load PR branch and re-run validation.”

---

## 5. Success Criteria for “Full Functional” Agent

- [x] Ticket assigned in Jira/Git triggers webhook and task is processed asynchronously.
- [x] Repo is cloned, branch created, codebase mapped, and implementation plan generated.
- [x] Code is generated and applied; linter and tests run and retry until pass (or max retries).
- [x] PR creation (commit, push, PR via PyGitHub) — requires `GITHUB_TOKEN` with push scope.
- [ ] PR comments trigger automatic code updates (F7: stub endpoint; F7.2–F7.5 pending).
- [x] All secrets are externalized; runs are isolated and traceable.
- [x] Service runs in Docker and is deployable to Cloud Run (or equivalent).

**Note:** 403 on push = token expired, missing `repo` scope, or fine-grained token without push. See [agent/README_CREDENTIALS.md](agent/README_CREDENTIALS.md).

This plan is ready to be used as the single source of truth for building the autonomous AI development agent from ticket to PR, including PR feedback handling.
