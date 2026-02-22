"""
Validation and self-correction (F5.1–F5.6).
Run repo linter and tests; format output as structured feedback for the LLM.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ValidationResult(NamedTuple):
    success: bool
    feedback: str
    linter_code: int | None
    linter_out: str
    linter_err: str
    test_code: int | None
    test_out: str
    test_err: str


def _run_cmd(cwd: Path, cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
    """Run command; return (exit_code, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


def _detect_commands(work_dir: Path) -> tuple[list[str] | None, list[str] | None]:
    """
    Detect lint and test commands by convention (F5.1, F5.2).
    Returns (lint_cmd, test_cmd); each is argv or None if not detected.
    """
    work_dir = Path(work_dir)

    # Node: package.json scripts
    pkg = work_dir / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts") or {}
            lint_cmd = None
            if "lint" in scripts:
                lint_cmd = ["npm", "run", "lint"]
            elif "lint:fix" in scripts:
                lint_cmd = ["npm", "run", "lint:fix"]
            test_cmd = None
            if "test" in scripts:
                test_cmd = ["npm", "test"]
            elif "test:ci" in scripts:
                test_cmd = ["npm", "run", "test:ci"]
            return lint_cmd, test_cmd
        except Exception as e:
            logger.debug("Could not parse package.json: %s", e)

    # Python: pyproject.toml or setup.cfg, pytest
    pyproject = work_dir / "pyproject.toml"
    setup_cfg = work_dir / "setup.cfg"
    if pyproject.is_file() or setup_cfg.is_file() or (work_dir / "setup.py").is_file():
        lint_cmd = None
        if (work_dir / "pyproject.toml").is_file():
            lint_cmd = ["ruff", "check", "."]
            code, _, _ = _run_cmd(work_dir, ["ruff", "--version"], timeout=5)
            if code != 0:
                lint_cmd = ["python", "-m", "pyflakes", "."]
                code2, _, _ = _run_cmd(work_dir, ["python", "-m", "pyflakes", "--version"], timeout=5)
                if code2 != 0:
                    lint_cmd = None
        test_cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
        code, _, _ = _run_cmd(work_dir, ["python", "-m", "pytest", "--version"], timeout=5)
        if code != 0:
            test_cmd = ["python", "-m", "unittest", "discover", "-v"]
        return lint_cmd, test_cmd

    # Makefile
    makefile = work_dir / "Makefile"
    if makefile.is_file():
        lint_cmd = None
        test_cmd = None
        content = makefile.read_text(encoding="utf-8", errors="replace")
        if "lint" in content:
            lint_cmd = ["make", "lint"]
        if "test" in content:
            test_cmd = ["make", "test"]
        return lint_cmd, test_cmd

    return None, None


def run_validation(work_dir: Path, timeout: int = 300) -> ValidationResult:
    """
    Run linter and tests; return success and formatted feedback (F5.1, F5.2, F5.3).
    Success only when both lint and test pass (or are skipped).
    """
    work_dir = Path(work_dir)
    lint_cmd, test_cmd = _detect_commands(work_dir)

    linter_code, linter_out, linter_err = None, "", ""
    if lint_cmd:
        linter_code, linter_out, linter_err = _run_cmd(work_dir, lint_cmd, timeout=timeout)
    else:
        logger.debug("No linter command detected; skipping lint")

    test_code, test_out, test_err = None, "", ""
    if test_cmd:
        test_code, test_out, test_err = _run_cmd(work_dir, test_cmd, timeout=timeout)
    else:
        logger.debug("No test command detected; skipping tests")

    # Success: no command run (skip) or both passed
    lint_ok = linter_code is None or linter_code == 0
    test_ok = test_code is None or test_code == 0
    success = lint_ok and test_ok

    feedback = _format_feedback(
        linter_code, linter_out, linter_err,
        test_code, test_out, test_err,
        lint_cmd, test_cmd,
    )
    return ValidationResult(
        success=success,
        feedback=feedback,
        linter_code=linter_code,
        linter_out=linter_out,
        linter_err=linter_err,
        test_code=test_code,
        test_out=test_out,
        test_err=test_err,
    )


def _format_feedback(
    linter_code: int | None,
    linter_out: str,
    linter_err: str,
    test_code: int | None,
    test_out: str,
    test_err: str,
    lint_cmd: list[str] | None,
    test_cmd: list[str] | None,
) -> str:
    """Format validation output for the LLM (F5.3)."""
    parts: list[str] = ["## Validation feedback (fix these issues)\n"]
    if lint_cmd and linter_code is not None and linter_code != 0:
        parts.append("### Linter failed")
        parts.append(f"Command: {' '.join(lint_cmd)}")
        parts.append("Exit code: " + str(linter_code))
        if linter_out.strip():
            parts.append("Stdout:\n" + linter_out.strip()[:8000])
        if linter_err.strip():
            parts.append("Stderr:\n" + linter_err.strip()[:8000])
        parts.append("")
    if test_cmd and test_code is not None and test_code != 0:
        parts.append("### Tests failed")
        parts.append(f"Command: {' '.join(test_cmd)}")
        parts.append("Exit code: " + str(test_code))
        if test_out.strip():
            parts.append("Stdout:\n" + test_out.strip()[:8000])
        if test_err.strip():
            parts.append("Stderr:\n" + test_err.strip()[:8000])
    if len(parts) == 1:
        return "All checks passed."
    return "\n".join(parts)
