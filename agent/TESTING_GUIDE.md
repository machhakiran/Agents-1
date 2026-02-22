# Step-by-Step Testing Guide (macOS, Local End-to-End)

**The main [README.md](../README.md) in the repo root now includes a combined overview, installation, and testing section.** This file is an extended, step-by-step version of the same flow for local E2E testing on macOS.

---

## Prerequisites

- **macOS** (tested on recent versions)
- **Python 3.11+** — `python3 --version`
- **git** — `git --version`
- **Optional for full flow:** A **GitHub** (or GitLab) repo you can push to, and tokens (see below)

---

## Step 1: Open the project and create a virtual environment

```bash
cd /path/to/Agents-1/agent
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your prompt.

---

## Step 2: Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If you see SSL or network errors, use a VPN or try:

```bash
pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

---

## Step 3: Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your favourite editor. Choose one of the two testing modes below.

### Option A: Phase 1 only (webhook + clone + branch)

Use this to verify **webhook parsing**, **clone**, and **branch creation** without using Claude or creating a PR.

- Use a **public** repo so clone works without a token, or set a token if the repo is private.
- Leave `ANTHROPIC_API_KEY` **empty** so Phase 2–4 are skipped.

Example for a **public** GitHub repo:

```env
# Leave empty to test Phase 1 only (clone will use public URL)
GITHUB_TOKEN=

# Leave empty — Phase 2 will be skipped
ANTHROPIC_API_KEY=
```

If your test repo is **private**, set:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

### Option B: Full flow (Phase 1 → 2 → 3 → 4)

Use this to run **map → plan → implement → validate → commit → push → PR**.

Set all of:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```

Use a **test repo** you own (or have write access to). The agent will create a branch and open a PR there.

Save `.env` and **do not commit it** (it should be in `.gitignore`).

---

## Step 4: Start the server

From the `agent` directory with the venv activated:

```bash
export PYTHONPATH="${PWD}"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

You should see something like:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

Leave this terminal open. Use a **second terminal** for the steps below.

---

## Step 5: Test health endpoint

In a **new terminal** (same machine):

```bash
curl -s http://localhost:8000/api/health
```

**Expected:**

```json
{"status":"ok","service":"ai-dev-agent"}
```

If you get "Connection refused", the server is not running or the port is wrong.

---

## Step 6: Test task webhook (Phase 1)

The agent accepts a task via `POST /api/webhook/task`. You can send either:

- A **GitHub-style** JSON body (issue + repository), or  
- A **minimal body** plus headers **X-Git-Provider** and **X-Repo**.

Replace `YOUR_GITHUB_USERNAME` and `YOUR_REPO_NAME` with a real **public** repo (e.g. your fork of a small project) so clone works.

### 6a. Using headers (easiest)

```bash
curl -s -X POST http://localhost:8000/api/webhook/task \
  -H "Content-Type: application/json" \
  -H "X-Git-Provider: github" \
  -H "X-Repo: YOUR_GITHUB_USERNAME/YOUR_REPO_NAME" \
  -d '{
    "ticket_id": "TEST-1",
    "title": "Add a README line",
    "description": "Add one line to README: Test from AI agent."
  }'
```

**Expected:** HTTP **201** and a JSON body like:

```json
{"status":"accepted","ticket_id":"TEST-1","repo":"YOUR_GITHUB_USERNAME/YOUR_REPO_NAME"}
```

**Note:** The parser expects either GitHub issue shape or GitLab issue shape. With headers we still need a body that can be parsed. The parser may not find `issue` or `object_attributes`, so it might return **400**. Use the **GitHub-style payload** below if that happens.

### 6b. Using a GitHub-style payload (recommended)

A sample payload is in `agent/scripts/sample_payloads/webhook_task_github.json`. Copy it and replace the placeholders:

```bash
cd /path/to/Agents-1/agent
cp scripts/sample_payloads/webhook_task_github.json /tmp/my_webhook.json
# Edit /tmp/my_webhook.json: replace YOUR_GITHUB_USERNAME and YOUR_REPO_NAME everywhere
```

Or create the file manually. It must contain `issue` and `repository` (GitHub format). Example:

```json
{
  "issue": {
    "number": 42,
    "title": "Add a README line",
    "body": "Add one line to README: Test from AI agent.",
    "labels": [{"name": "test"}],
    "assignees": [{"login": "your-github-username"}],
    "user": {"login": "your-github-username"}
  },
  "repository": {
    "full_name": "YOUR_GITHUB_USERNAME/YOUR_REPO_NAME",
    "default_branch": "main",
    "name": "YOUR_REPO_NAME",
    "owner": {"login": "YOUR_GITHUB_USERNAME"}
  }
}
```

Then send it (use your JSON file path):

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST http://localhost:8000/api/webhook/task \
  -H "Content-Type: application/json" \
  -d @/tmp/my_webhook.json
```

**Expected:**

- HTTP **201**
- Body: `{"status":"accepted","ticket_id":"#42","repo":"YOUR_GITHUB_USERNAME/YOUR_REPO_NAME"}`

---

## Step 7: Watch server logs (Phase 1)

In the **first terminal** (where uvicorn is running) you should see logs similar to:

```
INFO:     [TEST-1 or #42] Webhook accepted repo=...
INFO:     [TEST-1 or #42] Pipeline started run_id=...
INFO:     [TEST-1 or #42] Clone and branch ready branch=ai/...
INFO:     ... Phase 2 skipped (no ANTHROPIC_API_KEY)
```

If you see **"Clone failed"** or **"Git clone failed"**:

- Check that the repo exists and is **public** (or that `GITHUB_TOKEN` is set for a private repo).
- Check that `YOUR_GITHUB_USERNAME/YOUR_REPO_NAME` matches the repo.

Phase 1 is working when: **201** from curl, and logs show **"Clone and branch ready"** (and optionally "Phase 2 skipped").

---

## Step 8: Test full flow (Phase 2 → 4) — optional

Only if you configured **Option B** (GITHUB_TOKEN + ANTHROPIC_API_KEY) and use a repo you can push to:

1. Use the same **GitHub-style** payload as in Step 6b, with a **real repo** you own.
2. Set the **title** and **body** to a **small, clear task**, e.g.:
   - "Add a function that returns 'Hello, World' in `src/hello.py`"
   - Use a repo that already has a simple structure (e.g. Python with `pyproject.toml` or Node with `package.json`).

3. Send the webhook (same `curl` as 6b, with your payload).

4. In the server logs you should see, in order:
   - Clone and branch ready
   - Codebase map built
   - Plan created
   - Implementation applied
   - Validation passed (or retries if linter/tests fail)
   - PR created

5. On GitHub:
   - Open the repo → **Branches** → you should see a branch like `ai/#42-...` or `ai/TEST-1-...`.
   - Open **Pull requests** → you should see a new PR with title like `#42: Add a README line`, label `ai-generated`, and body from the ticket.

If validation keeps failing, check the logs for linter/test output; the agent will retry up to `MAX_VALIDATION_RETRIES` (default 5).

---

## Step 9: Test PR comment webhook (stub)

The PR comment endpoint is a stub but should accept requests:

```bash
curl -s -w "\nHTTP_CODE:%{http_code}\n" -X POST http://localhost:8000/api/webhook/pr-comment \
  -H "Content-Type: application/json" \
  -d '{"comment": {"body": "Please add a test"}, "repository": {"full_name": "owner/repo"}, "pull_request": {"number": 1}}'
```

**Expected:** HTTP **202** and a message that PR comment handling is not yet implemented.

---

## Step 10: Idempotency (optional)

Send the **same** task webhook again (same ticket_id and repo) within a short time. You should get HTTP **409** and a body like:

```json
{"error": "Task already in progress for this ticket and repo"}
```

After the first run finishes, you can send the same payload again; the second run may then get **201** (idempotency is per run, not permanent).

---

## Quick reference: endpoints

| What              | Method | URL                          | Expected |
|-------------------|--------|------------------------------|----------|
| Health            | GET    | `http://localhost:8000/api/health` | 200, `{"status":"ok",...}` |
| Task webhook      | POST   | `http://localhost:8000/api/webhook/task` | 201 (or 400/409) |
| PR comment webhook| POST   | `http://localhost:8000/api/webhook/pr-comment` | 202 |

---

## Troubleshooting

| Problem | What to check |
|--------|----------------|
| **400 Bad Request** on `/webhook/task` | Body must be valid JSON. For GitHub, include `issue` and `repository`. Or use headers `X-Git-Provider` and `X-Repo` and a body the parser accepts. |
| **409 Conflict** | Same ticket + repo already in progress; wait for the run to finish or use a different ticket_id/repo. |
| **Clone failed** | Repo exists? Public repo or valid `GITHUB_TOKEN`? Correct `full_name` (owner/repo)? |
| **Phase 2 skipped** | `ANTHROPIC_API_KEY` not set or empty in `.env`. |
| **Validation failed / no PR** | Linter or tests failed and self-heal hit max retries. Check logs for the exact errors. |
| **PR not created** | Validation must pass. Need `GITHUB_TOKEN` (or `GITLAB_TOKEN`) and run must have completed Phase 2 (so there is code to commit). |
| **Module not found** when starting server | Run from the `agent` directory and set `PYTHONPATH=${PWD}` (or run `uvicorn` from `agent` so `src` is on the path). |

---

## Summary checklist

- [ ] Venv created and activated, dependencies installed  
- [ ] `.env` created from `.env.example` and required vars set (at least for Phase 1: repo + optional token)  
- [ ] Server starts with `uvicorn src.main:app --reload --host 0.0.0.0 --port 8000`  
- [ ] `GET /api/health` returns 200 and `{"status":"ok",...}`  
- [ ] `POST /api/webhook/task` with GitHub-style payload returns 201 and logs show "Clone and branch ready"  
- [ ] (Optional) With token + Anthropic key, full flow runs and a PR appears on GitHub  
- [ ] (Optional) Sending same task again during a run returns 409  
- [ ] `POST /api/webhook/pr-comment` returns 202  

Once all of the above pass, the project is working end-to-end locally on macOS for the implemented flows.
