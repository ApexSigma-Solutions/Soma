# ============================================================================
# STAGE 1: Build Stage
# Use a full-featured base image to install build dependencies and compile the
# application environment.
# ============================================================================
FROM python:3.13-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_NO_INTERACTION=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry package manager
RUN pip install poetry

WORKDIR /app

# Configure Poetry to create the virtual environment inside the project directory
RUN poetry config virtualenvs.in-project true

# Copy only the dependency definition files
COPY pyproject.toml poetry.lock* ./

# The --no-root flag tells Poetry "Just install the dependencies from the lock
# file, don't try to install the project package itself." This is the fix for
# the "Readme not found" error.
RUN poetry install --with dev --no-root


# ============================================================================
# STAGE 2: Final Stage
# ============================================================================
FROM python:3.13-slim AS final

ENV DEBIAN_FRONTEND=noninteractive
ENV POETRY_NO_INTERACTION=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

WORKDIR /app

# Configure Poetry
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml poetry.lock* README.md ./

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/

# Install dependencies
RUN poetry install --with dev
COPY README.md .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.ingest_llm_as.main:app", "--host", "0.0.0.0", "--port", "8000"]