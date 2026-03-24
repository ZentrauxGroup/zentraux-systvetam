FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY mesh/ ./mesh/
COPY roles/ ./roles/
COPY main.py .

# Health check — Railway uses this
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8001}/health || exit 1

# Non-root execution
RUN useradd -m -r meshrunner && chown -R meshrunner:meshrunner /app
USER meshrunner

EXPOSE ${PORT:-8001}

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
