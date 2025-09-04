# Multi-stage build for System Builder Hub
ARG APP_VERSION=0.1.0
ARG BUILD_DATE
ARG BUILD_ID

# Multi-stage build for System Builder Hub
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r sbh && useradd -r -g sbh sbh

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/sbh/.local

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/db /app/logs /app/backups /app/instance/uploads && \
    chown -R sbh:sbh /app

# Switch to non-root user
USER sbh

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH=/home/sbh/.local/bin:$PATH
ENV APP_VERSION=${APP_VERSION}
ENV BUILD_DATE=${BUILD_DATE}
ENV BUILD_ID=${BUILD_ID}

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/healthz || exit 1

# Production command using Gunicorn
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
