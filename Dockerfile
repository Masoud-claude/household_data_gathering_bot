# ─────────────────────────────────────────────────────────────────────────────
#  Canadian Household Financial Data Bot — Dockerfile
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Metadata
LABEL maintainer="your-email@example.com"
LABEL description="Canadian Household Financial Data Telegram Bot"

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Working directory
WORKDIR /app

# Install system dependencies (lxml needs libxml2)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache optimisation)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY bot/ ./bot/
COPY main.py .

# Create data directory (Railway volume mount will overlay this at runtime)
RUN mkdir -p /app/data

CMD ["python", "main.py"]
