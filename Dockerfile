# ChemAgent Production Dockerfile
# Multi-stage build for optimized production image

# =============================================================================
# Build stage: Install dependencies
# =============================================================================
FROM python:3.12-slim as builder

LABEL stage=builder

# Install system dependencies for chemistry libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libglib2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir python-dotenv gunicorn

# =============================================================================
# Runtime stage: Minimal production image
# =============================================================================
FROM python:3.12-slim

LABEL maintainer="ChemAgent Team" \
      description="ChemAgent - AI-Powered Pharmaceutical Research Assistant" \
      version="1.0.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CHEMAGENT_PORT=8000 \
    CHEMAGENT_WORKERS=4 \
    CHEMAGENT_CACHE_ENABLED=true \
    CHEMAGENT_LOG_LEVEL=info

# Create non-root user for security
RUN useradd -m -u 1000 chemagent && \
    mkdir -p /app /app/data /app/logs /app/.cache && \
    chown -R chemagent:chemagent /app

# Switch to non-root user
USER chemagent
WORKDIR /app

# Copy application code
COPY --chown=chemagent:chemagent src/ ./src/
COPY --chown=chemagent:chemagent data/ ./data/
COPY --chown=chemagent:chemagent pyproject.toml README.md ./

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${CHEMAGENT_PORT}/health || exit 1

# Expose API port
EXPOSE ${CHEMAGENT_PORT}

# Default command: Run FastAPI with uvicorn
CMD uvicorn src.chemagent.api.server:app \
    --host 0.0.0.0 \
    --port ${CHEMAGENT_PORT} \
    --workers ${CHEMAGENT_WORKERS} \
    --log-level ${CHEMAGENT_LOG_LEVEL}
