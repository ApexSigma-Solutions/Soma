# --- Stage 1: The Builder ---
# CRITICAL: Use 3.12-slim. Do NOT use 'latest' or '3-slim' (maps to 3.13).
FROM python:3.12-slim AS builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency definition
COPY pyproject.toml poetry.lock ./

# Install dependencies
# CRITICAL: Re-lock to sync with container environment
RUN poetry config virtualenvs.in-project true && \
    poetry lock && \
    poetry install --only main --no-root

# --- Stage 2: The Runtime ---
FROM python:3.12-slim

# Install basics
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 soma && \
    useradd --uid 1000 --gid soma --shell /bin/bash --create-home soma

WORKDIR /app

# Copy venv from builder
COPY --from=builder --chown=soma:soma /app/.venv /app/.venv

# Copy code
COPY --chown=soma:soma . .

USER soma

ENV PATH="/app/.venv/bin:$PATH"

# Dagster Default Port
EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/dagster_home || exit 1

# Default Entrypoint
ENTRYPOINT ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]