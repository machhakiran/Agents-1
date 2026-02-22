# Production-grade multi-stage build. Run from repo root: docker build -f agent/Dockerfile agent/
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runtime

# Non-root user
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app
WORKDIR /app

COPY --from=builder /root/.local /home/app/.local
# Build context should be agent/ e.g. docker build -f agent/Dockerfile agent/
COPY . .
ENV PATH=/home/app/.local/bin:$PATH

# Workspace dir for clones (must be writable)
RUN mkdir -p /tmp/ai_agent_workspaces && chown -R app:app /tmp/ai_agent_workspaces /app

USER app
EXPOSE 8000
ENV PYTHONPATH=/app
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
