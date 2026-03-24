# SYSTVETAM — Central Dispatch Dockerfile
# Zentraux Group LLC
#
# Python 3.12 slim.
# Schema created by FastAPI lifespan (raw SQL, idempotent).
# No Alembic in CMD — tables guaranteed by startup sequence in main.py.

FROM python:3.12-slim AS base

# System deps for asyncpg
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

# Tables created by lifespan Block 1 (raw SQL, IF NOT EXISTS) — no Alembic in CMD.
CMD sh -c 'uvicorn dispatch.main:app --host 0.0.0.0 --port ${PORT:-8000} --ws-ping-interval 30 --ws-ping-timeout 10'
