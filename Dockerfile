# Mem0 Local MCP Server Dockerfile
# Supports both SSE (HTTP) and stdio transport modes

FROM python:3.12-slim

# Build arguments
ARG PORT=8050
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG ALL_PROXY
ARG NO_PROXY

# Set environment variables (including proxy for build stage)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=${PORT} \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    ALL_PROXY=${ALL_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${HTTP_PROXY} \
    https_proxy=${HTTPS_PROXY} \
    all_proxy=${ALL_PROXY} \
    no_proxy=${NO_PROXY}

# Create non-root user for security
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and source code
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install uv for faster package installation
RUN pip install uv

# Install project dependencies
RUN uv pip install --system -e .

# Create data directory for local Qdrant storage
RUN mkdir -p /app/mem0_data && chown -R app:app /app

# Switch to non-root user
USER app

# Expose port for SSE transport
EXPOSE ${PORT}

# Health check for SSE mode (TCP check since /health endpoint may not exist)
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD timeout 1 bash -c "</dev/tcp/localhost/${PORT}" || exit 1

# Default command - can be overridden for stdio mode
CMD ["python", "-m", "mcp_ai_memory.server"]
