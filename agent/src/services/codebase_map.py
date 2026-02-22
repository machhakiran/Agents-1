"""
Codebase semantic map (F2.4).
Builds a text map of repo: file tree + key symbols (classes, functions) for planning.
Lightweight: no aider dependency; regex-based extraction for common languages.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Ignore these dirs when building map
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".tox",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

# Extensions we consider source
SOURCE_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".rb", ".php"}

# Regex for top-level def/class (Python)
RE_PY_DEF = re.compile(r"^(?:async\s+)?def\s+(\w+)\s*\(", re.MULTILINE)
RE_PY_CLASS = re.compile(r"^class\s+(\w+)", re.MULTILINE)

# Regex for function/class (JS/TS)
RE_JS_FUNC = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE)
RE_JS_CLASS = re.compile(r"^(?:export\s+)?class\s+(\w+)", re.MULTILINE)
RE_JS_CONST_FN = re.compile(r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", re.MULTILINE)


def _should_skip_dir(name: str) -> bool:
    if name in SKIP_DIRS:
        return True
    if name.startswith(".") and name != ".github":
        return True
    return False


def _extract_symbols(content: str, ext: str) -> list[str]:
    symbols: list[str] = []
    if ext == ".py":
        symbols.extend(RE_PY_CLASS.findall(content))
        symbols.extend(RE_PY_DEF.findall(content))
    elif ext in (".ts", ".tsx", ".js", ".jsx"):
        symbols.extend(RE_JS_CLASS.findall(content))
        symbols.extend(RE_JS_FUNC.findall(content))
        symbols.extend(RE_JS_CONST_FN.findall(content))
    return symbols


def build_map(work_dir: Path, max_file_lines: int = 2000, max_map_chars: int = 30000) -> str:
    """
    Build a semantic map of the codebase under work_dir.
    Returns a single string: file tree + per-file symbols (classes, top-level functions).
    Truncates per-file content and total map size to stay within context limits.
    """
    work_dir = Path(work_dir)
    if not work_dir.is_dir():
        return ""

    lines: list[str] = []
    total_chars = 0

    def add(s: str) -> bool:
        nonlocal total_chars
        if total_chars + len(s) > max_map_chars:
            return False
        lines.append(s)
        total_chars += len(s)
        return True

    # File tree (relative paths only)
    tree_parts: list[str] = []
    for p in sorted(work_dir.rglob("*")):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(work_dir)
        except ValueError:
            continue
        parts = rel.parts
        if any(_should_skip_dir(parts[i]) for i in range(len(parts))):
            continue
        if p.suffix not in SOURCE_EXT and p.suffix not in (".md", ".json", ".yaml", ".yml", ".toml"):
            continue
        tree_parts.append(str(rel))
    add("## Repository structure\n")
    for f in sorted(tree_parts)[:500]:
        if not add(f + "\n"):
            break
    add("\n")

    # Per-file symbols for source files
    add("## Key symbols by file\n")
    for rel_str in sorted(tree_parts):
        if total_chars >= max_map_chars:
            break
        fpath = work_dir / rel_str
        if fpath.suffix not in SOURCE_EXT:
            continue
        try:
            raw = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug("Skip reading %s: %s", rel_str, e)
            continue
        symbols = _extract_symbols(raw, fpath.suffix)
        if not symbols:
            continue
        block = f"### {rel_str}\n  " + ", ".join(symbols) + "\n"
        if not add(block):
            break

    return "".join(lines)
