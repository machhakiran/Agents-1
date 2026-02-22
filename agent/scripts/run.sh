#!/usr/bin/env bash
# Run from agent/ directory. Uses .venv if present.
set -e
cd "$(dirname "$0")/.."
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi
export PYTHONPATH="${PWD}"
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
