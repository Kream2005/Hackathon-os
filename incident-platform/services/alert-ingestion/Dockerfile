# ── Stage 1: dependency install ─────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: production runtime ─────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="team@hackathon" \
      service="alert-ingestion" \
      version="1.0.0"

WORKDIR /app

# curl for Docker HEALTHCHECK; clean apt caches in same layer
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN adduser --disabled-password --no-create-home --gecos "" appuser

# Copy installed dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
