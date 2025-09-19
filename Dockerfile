# syntax=docker/dockerfile:1.7
# Multi-stage build for smaller runtime image and supply chain clarity

FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    PORT=8000 \
    HOST=0.0.0.0 \
    ENV=production \
    DEBUG=false

# Create a non-root user early (so site-packages perms are correct)
RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR ${APP_HOME}

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gdal-bin \
    libgdal-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements separately for layer caching
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application source
COPY . .

# Ensure non-root execution
USER app:app

# Expose MCP default port
EXPOSE 8000

# Health check for Azure App Service
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default command for Azure App Service
# Note: Azure App Service will set WEBSITES_PORT environment variable
# The application will use HOST and PORT environment variables
CMD ["python", "main.py"]
