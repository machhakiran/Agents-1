#!/usr/bin/env bash
# Validate config and test against machhakiran/Agents-1
# Run from agent/ with venv activated: ./scripts/validate_and_test.sh

set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="${PWD}"

echo "=== 1. Config check ==="
python3 -c "
from src.config import get_settings
s = get_settings()
assert s.github_token, 'GITHUB_TOKEN not set in .env'
assert s.anthropic_api_key, 'ANTHROPIC_API_KEY not set in .env'
print('OK: GITHUB_TOKEN and ANTHROPIC_API_KEY are set')
"

echo ""
echo "=== 2. App load ==="
python3 -c "
from src.main import app
print('OK: FastAPI app loaded')
"

echo ""
echo "=== 3. Start server (background) and test health + webhook ==="
uvicorn src.main:app --host 127.0.0.1 --port 8000 &
UVICORN_PID=$!
sleep 3

health=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health || true)
if [ "$health" = "200" ]; then
  echo "OK: Health check returned 200"
else
  echo "WARN: Health check returned $health"
fi

echo ""
echo "=== 4. Send task webhook for machhakiran/Agents-1 ==="
res=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/api/webhook/task \
  -H "Content-Type: application/json" \
  -d @scripts/sample_payloads/webhook_task_machhakiran_agents1.json 2>/dev/null || echo "000")
code=$(echo "$res" | tail -n1)
body=$(echo "$res" | sed '$d')
if [ "$code" = "201" ]; then
  echo "OK: Webhook accepted (201). Response: $body"
else
  echo "Response ($code): $body"
fi

kill $UVICORN_PID 2>/dev/null || true
echo ""
echo "Done. Check https://github.com/machhakiran/Agents-1 for new branch and PR after pipeline runs."
