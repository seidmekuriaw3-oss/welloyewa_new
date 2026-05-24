# ============================
# WOLLOYEWA STORE BOT - DOCKERFILE
# ============================
# Multi-stage build for production optimization
# Base Python image: 3.11-slim for smaller size

# ============================
# STAGE 1: Builder
# ============================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libmagic1 \
    libjpeg-dev \
    zlib1g-dev \
    libxml2-dev \
    libxslt-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==${POETRY_VERSION}"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies to a virtual environment
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root --only main

# ============================
# STAGE 2: Development
# ============================
FROM python:3.11-slim as development

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for development
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libmagic1 \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    git \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Add virtual environment to PATH
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs media static backups

# Expose ports
EXPOSE 8000 5678

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (overridable)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================
# STAGE 3: Production
# ============================
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ENVIRONMENT=production \
    DEBUG=False

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libmagic1 \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Add virtual environment to PATH
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories with proper permissions
RUN mkdir -p logs media static backups && \
    chown -R appuser:appgroup logs media static backups

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]

# ============================
# STAGE 4: Worker (Celery)
# ============================
FROM production as worker

# Set environment variables for worker
ENV CELERY_WORKER=true

# Switch back to root for additional installations
USER root

# Install additional tools for worker
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER appuser

# Celery worker command
CMD ["celery", "-A", "infrastructure.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]

# ============================
# STAGE 5: Beat (Scheduled Tasks)
# ============================
FROM production as beat

# Set environment variables for beat
ENV CELERY_BEAT=true

# Celery beat command
CMD ["celery", "-A", "infrastructure.workers.celery_app", "beat", "--loglevel=info", "--pidfile=/tmp/celerybeat.pid"]

# ============================
# STAGE 6: Flower (Monitoring)
# ============================
FROM production as flower

# Set environment variables for flower
ENV FLOWER=true

# Expose flower port
EXPOSE 5555

# Flower command
CMD ["celery", "-A", "infrastructure.workers.celery_app", "flower", "--port=5555", "--url_prefix=flower"]

# ============================
# LABELS
# ============================
LABEL maintainer="Wolloyewa Team" \
      version="1.0.0" \
      description="Wolloyewa Store Bot - Ethiopian E-commerce Telegram Bot" \
      com.docker.compose.project="wolloyewa" \
      org.opencontainers.image.title="Wolloyewa Store Bot" \
      org.opencontainers.image.description="Multi-vendor e-commerce bot for Ethiopian market" \
      org.opencontainers.image.version="1.0.0"