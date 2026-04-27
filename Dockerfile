FROM python:3.12-slim

WORKDIR /app

# Build tools only if a wheel is missing (numpy / etc. usually ship manylinux wheels).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Reproducible installs from the repo lockfile (uv), not requirements.lock.
RUN pip install --no-cache-dir "uv>=0.5"

COPY pyproject.toml README.md uv.lock ./

COPY maverickj/ ./maverickj/
COPY config.yaml ./

ENV UV_COMPILE_BYTECODE=1
RUN uv sync --frozen --no-dev

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

CMD ["python", "-m", "maverickj.cli"]
