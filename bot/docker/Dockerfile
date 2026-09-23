FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.23 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY bot/pyproject.toml bot/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --package bot

COPY backend/ backend/
COPY bot/ bot/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --package bot

FROM python:3.13-slim AS runtime

ARG UID=1000
ARG GID=1000

RUN groupadd --gid "${GID}" appgroup \
    && useradd --uid "${UID}" --gid appgroup --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend
COPY --from=builder /app/bot /app/bot

RUN chown -R appuser:appgroup /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app/backend:/app/bot"
WORKDIR /app/bot

USER appuser

CMD ["python", "-m", "app.main"]