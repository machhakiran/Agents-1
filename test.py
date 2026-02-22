"""
End-to-end test runner for the AI Teammate agent.

Run from the repo root:

    python test.py

It will:
1. Locate `agent/.venv` and `uvicorn` (expects deps already installed, e.g. via `python setup.py runserver` once).
2. Start the FastAPI server on 127.0.0.1:8000 with:
   - PYTHONPATH set to `agent/`
   - WORKSPACE_BASE pointing to `agent/workspaces` (created if missing)
3. Hit:
   - GET  /api/health
   - POST /api/webhook/task          (using the machhakiran/Agents-1 sample payload)
   - POST /api/webhook/pr-comment    (stub)
4. Print a short PASS/FAIL summary and stop the server.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AGENT_DIR = ROOT / "agent"
VENV_DIR = AGENT_DIR / ".venv"


def _http_request(method: str, url: str, data: dict | None = None) -> tuple[int, str]:
    body: bytes | None = None
    headers = {"Content-Type": "application/json"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # type: ignore[arg-type]
            status = resp.getcode() or 0
            text = resp.read().decode("utf-8", errors="replace")
            return status, text
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        return e.code, text
    except Exception as e:  # noqa: BLE001
        return 0, f"ERROR: {e}"


def main() -> int:
    python = sys.executable
    uvicorn_bin = VENV_DIR / "bin" / "uvicorn"
    if not uvicorn_bin.exists():
        print("[test] ERROR: uvicorn not found in agent/.venv.")
        print("       Run once:  python setup.py runserver  (then Ctrl+C) to create venv and install deps.")
        return 1

    # Ensure a writable workspace (without touching .env)
    workspace_dir = AGENT_DIR / "workspaces"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(AGENT_DIR))
    env.setdefault("WORKSPACE_BASE", str(workspace_dir))

    cmd = [str(uvicorn_bin), "src.main:app", "--host", "127.0.0.1", "--port", "8000"]
    print(f"[test] Starting server: {' '.join(cmd)}")
    server = subprocess.Popen(cmd, cwd=str(AGENT_DIR), env=env)  # noqa: S603

    try:
        # Wait for health to pass
        ok = False
        for i in range(15):
            time.sleep(1)
            status, text = _http_request("GET", "http://127.0.0.1:8000/api/health")
            if status == 200:
                print(f"[test] Health check OK (attempt {i+1}/15):", text)
                ok = True
                break
        if not ok:
            print("[test] ERROR: Health check never returned 200.")
            return 1

        # Load sample payload for machhakiran/Agents-1
        payload_path = AGENT_DIR / "scripts" / "sample_payloads" / "webhook_task_machhakiran_agents1.json"
        if not payload_path.exists():
            print(f"[test] ERROR: Sample payload not found: {payload_path}")
            return 1
        body = json.loads(payload_path.read_text(encoding="utf-8"))

        # POST /api/webhook/task
        status, text = _http_request("POST", "http://127.0.0.1:8000/api/webhook/task", data=body)
        print("[test] POST /api/webhook/task →", status, text)
        if status != 201:
            print("[test] ERROR: Expected 201 from /api/webhook/task")
            return 1

        # Wait for pipeline to complete (clone → map → plan → implement → validate → PR)
        wait_sec = int(os.environ.get("TEST_PIPELINE_WAIT", "90"))
        print(f"[test] Waiting {wait_sec}s for pipeline (clone→map→plan→implement→validate→PR)...")
        time.sleep(wait_sec)

        # POST /api/webhook/pr-comment (stub)
        status, text = _http_request(
            "POST",
            "http://127.0.0.1:8000/api/webhook/pr-comment",
            data={
                "comment": {"body": "Please add a test"},
                "repository": {"full_name": "machhakiran/Agents-1"},
                "pull_request": {"number": 1},
            },
        )
        print("[test] POST /api/webhook/pr-comment →", status, text)
        if status != 202:
            print("[test] ERROR: Expected 202 from /api/webhook/pr-comment")
            return 1

        print("\n[test] SUCCESS: End-to-end HTTP flow passed.")
        print("       Pipeline (clone → map → plan → implement → validate → PR) runs in the background.")
        print("       Check logs and GitHub (machhakiran/Agents-1) for branch/PR once the pipeline completes.")
        return 0

    finally:
        print("[test] Stopping server...")
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())

