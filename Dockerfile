FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first to leverage Docker layer cache
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy project source code
COPY maverickj/ ./maverickj/
COPY config.yaml ./

# Interactive CLI entrypoint
CMD ["python", "-m", "maverickj.cli"]
