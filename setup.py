"""
Convenience launcher: single command to bring up the AI Teammate server.

Usage (from repo root):

    python setup.py runserver

This will:
- Ensure a virtualenv exists in `agent/.venv`
- Install required dependencies (using trusted hosts to avoid SSL issues)
- Ensure a writable `WORKSPACE_BASE` is configured (defaults to `./workspaces` under `agent/`)
- Start the FastAPI server with the correct `PYTHONPATH`

Notes:
- Secrets (GITHUB_TOKEN, ANTHROPIC_API_KEY, etc.) must still be set in `agent/.env`
  as documented in `agent/README_CREDENTIALS.md`.
- `.env` is ignored by git via `.gitignore` so secrets are not committed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AGENT_DIR = ROOT / "agent"
VENV_DIR = AGENT_DIR / ".venv"


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command, raising on failure."""
    print(f"[setup] $ {' '.join(cmd)} (cwd={cwd or ROOT})")
    subprocess.check_call(cmd, cwd=str(cwd or ROOT))


def ensure_venv_and_deps() -> None:
    """Create venv in agent/.venv and install runtime dependencies."""
    python = sys.executable
    if not VENV_DIR.exists():
        print("[setup] Creating virtualenv at agent/.venv")
        _run([python, "-m", "venv", str(VENV_DIR)], cwd=AGENT_DIR)

    pip_bin = VENV_DIR / "bin" / "pip"
    if not pip_bin.exists():
        raise SystemExit("[setup] pip not found in agent/.venv; virtualenv creation may have failed.")

    print("[setup] Upgrading pip in venv")
    _run([str(pip_bin), "install", "--upgrade", "pip"], cwd=AGENT_DIR)

    req = AGENT_DIR / "requirements.txt"
    if req.exists():
        print("[setup] Installing dependencies from requirements.txt (with trusted-host to avoid SSL issues)")
        _run(
            [
                str(pip_bin),
                "install",
                "--trusted-host",
                "pypi.org",
                "--trusted-host",
                "pypi.python.org",
                "--trusted-host",
                "files.pythonhosted.org",
                "-r",
                str(req),
            ],
            cwd=AGENT_DIR,
        )
    else:
        # Fallback: direct install of core deps if requirements is missing
        print("[setup] requirements.txt not found; installing core deps directly")
        _run(
            [
                str(pip_bin),
                "install",
                "--trusted-host",
                "pypi.org",
                "--trusted-host",
                "pypi.python.org",
                "--trusted-host",
                "files.pythonhosted.org",
                "fastapi",
                "uvicorn[standard]",
                "pydantic",
                "pydantic-settings",
                "PyGithub",
                "python-gitlab",
                "anthropic",
            ],
            cwd=AGENT_DIR,
        )


def ensure_workspace_base() -> None:
    """
    Ensure WORKSPACE_BASE is writable.

    If WORKSPACE_BASE is not set in agent/.env, append:
        WORKSPACE_BASE=./workspaces
    and create the directory.
    """
    env_path = AGENT_DIR / ".env"
    workspace_dir = AGENT_DIR / "workspaces"

    existing = ""
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8")

    if "WORKSPACE_BASE" not in existing:
        print("[setup] Adding WORKSPACE_BASE=./workspaces to agent/.env (if secrets exist, they are preserved)")
        # Preserve existing content and append WORKSPACE_BASE
        new_content = (existing.rstrip() + "\n\nWORKSPACE_BASE=./workspaces\n").lstrip("\n")
        env_path.write_text(new_content, encoding="utf-8")

    if not workspace_dir.exists():
        print(f"[setup] Creating workspace directory at {workspace_dir}")
        workspace_dir.mkdir(parents=True, exist_ok=True)


def runserver() -> None:
    """Start the FastAPI server using the venv's uvicorn."""
    ensure_venv_and_deps()
    ensure_workspace_base()

    uvicorn_bin = VENV_DIR / "bin" / "uvicorn"
    if not uvicorn_bin.exists():
        raise SystemExit("[setup] uvicorn not found in venv; dependency installation may have failed.")

    # Ensure src/ is on PYTHONPATH
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(AGENT_DIR))

    cmd = [str(uvicorn_bin), "src.main:app", "--host", "0.0.0.0", "--port", os.getenv("PORT", "8000")]
    print(f"[setup] Starting server with: {' '.join(cmd)}")
    # Replace current process so logs stream normally
    os.execve(cmd[0], cmd, env)


if __name__ == "__main__":
    # Simple CLI: python setup.py runserver
    if len(sys.argv) >= 2 and sys.argv[1] == "runserver":
        runserver()
    else:
        print("Usage:")
        print("  python setup.py runserver")
        raise SystemExit(1)

