# SYSTVETAM — Central Dispatch Dockerfile
# Zentraux Group LLC
#
# Multi-stage build. Python 3.12 slim. No bloat.
# Runs on Railway (production) and Docker Compose (local dev).

FROM python:3.12-slim AS base

# System deps for asyncpg and Docker SDK
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/dispatch/

# Set PYTHONPATH so dispatch package resolves
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check for Docker + Railway
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "dispatch.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-ping-interval", "30", "--ws-ping-timeout", "10"]
