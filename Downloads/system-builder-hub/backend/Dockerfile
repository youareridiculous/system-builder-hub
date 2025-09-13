# SBH Backend Dockerfile - Phase 1 Cloud Migration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY backend/ .

# Create necessary directories
RUN mkdir -p /app/db /app/logs /app/backups /app/workspace

# Expose Flask server on port 8000 (standardized for cloud)
EXPOSE 8000

# Use gunicorn for production with proper configuration
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "wsgi:app"]
