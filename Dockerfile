# TermiVoxed - Dockerfile
# Author: Santhosh T
#
# Multi-stage build for optimized image size

# Stage 1: Build stage
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Runtime stage
FROM python:3.11-slim

# Set metadata
LABEL maintainer="Santhosh T"
LABEL description="TermiVoxed - AI-powered video editing with voice-over and subtitles"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install runtime dependencies (FFmpeg and system libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsdl2-mixer-2.0-0 \
    libsdl2-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p storage/{projects,temp,cache,output,fonts} logs

# Copy .env.example to .env if not exists
RUN cp .env.example .env || true

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose volume for persistent storage
VOLUME ["/app/storage", "/app/logs"]

# Set entrypoint
ENTRYPOINT ["python", "main.py"]

# Health check (optional - checks if Python is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1
