FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first to leverage Docker layer cache
COPY pyproject.toml README.md requirements.lock ./

# Install pinned runtime dependencies first, then install the package itself.
RUN pip install --no-cache-dir -r requirements.lock

# Copy project source code
COPY maverickj/ ./maverickj/
COPY config.yaml ./

RUN pip install --no-cache-dir --no-deps -e .

# Interactive CLI entrypoint
CMD ["python", "-m", "maverickj.cli"]
