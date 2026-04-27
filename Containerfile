# OCI image for local runs and CI (Podman- and Docker-compatible).
# Build:  podman build -f Containerfile -t maverickj:local .
# Run:    podman run --rm -e ANTHROPIC_API_KEY -v "$PWD/config.yaml:/app/config.yaml:ro" maverickj:local \
#            python examples/fusion_phase6_smoke.py

FROM docker.io/library/python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY maverickj ./maverickj
COPY examples ./examples
COPY config.yaml ./config.yaml

RUN pip install --upgrade pip && pip install .

# Default: phase 6 smoke (override CMD to run full debate, pytest, etc.)
CMD ["python", "examples/fusion_phase6_smoke.py"]
