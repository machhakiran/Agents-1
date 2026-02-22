# AI Teammate — Autonomous AI Development Agent

**Project name:** AI Teammate (ai-dev-agent)  
**Tagline:** From Jira/Git ticket to code, tests, and Pull Request — fully automated.

---

## Description

AI Teammate is an **autonomous software development agent** that acts as a junior developer in your toolchain. It listens for task assignments (Jira or GitHub/GitLab issues), clones the target repository, maps the codebase, plans changes, implements them using Anthropic's Claude, runs linters and tests with self-correction, then commits, pushes, and opens a Pull Request — all without human-in-the-loop coding.

**Core value:** Bridge project planning (ticket assignment) and technical implementation (PR creation) to increase engineering throughput while keeping code quality high.

- **Trigger:** Webhook on ticket assignment (Jira, GitHub, or GitLab).
- **Execution:** Asynchronous; the API returns `201 Created` immediately and runs the pipeline in the background.
- **Output:** A PR with the original ticket context, `ai-generated` label, and optional reviewer assignment.

See [AI_Agent_PDR.md](AI_Agent_PDR.md) and [AGENT_FUNCTIONAL_PLAN.md](AGENT_FUNCTIONAL_PLAN.md) for product and functional design. Credentials and env setup: [agent/README_CREDENTIALS.md](agent/README_CREDENTIALS.md).

---

## Architecture

High-level: a **FastAPI** server exposes webhook endpoints; a **pipeline** orchestrates clone → map → plan → implement → validate → deliver (commit/push/PR). Git and LLM are abstracted behind services.