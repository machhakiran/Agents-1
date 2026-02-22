# AI Teammate — Agent Package

This directory contains the **AI Teammate** agent application (FastAPI server and pipeline).

- **Full README (project name, description, architecture, tech stack, flow diagram, installation, testing, copyright):** [../README.md](../README.md)
- **Credentials (MANDATORY vs optional):** [README_CREDENTIALS.md](README_CREDENTIALS.md)
- **Functional plan:** [../AGENT_FUNCTIONAL_PLAN.md](../AGENT_FUNCTIONAL_PLAN.md)

## Quick run

```bash
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit: GITHUB_TOKEN, ANTHROPIC_API_KEY
export PYTHONPATH="${PWD}"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/api/health`
- Task webhook: `POST http://localhost:8000/api/webhook/task` (see [../README.md#local-end-to-end-testing-macos](../README.md#local-end-to-end-testing-macos))

## Phases

- **Phase 1:** Webhook, parse, clone, branch, idempotency
- **Phase 2:** Codebase map, plan (Claude), implement (Claude + EDIT_FILE)
- **Phase 3:** Linter/tests + self-heal loop
- **Phase 4:** Commit, push, create PR
- **Phase 5 (stub):** PR comment webhook
