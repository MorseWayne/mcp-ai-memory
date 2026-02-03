# Mem0 Local MCP Server Dockerfile
# Supports both SSE (HTTP) and stdio transport modes

FROM python:3.12-slim

# Build arguments
ARG PORT=8050

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=${PORT}

# Create non-root user for security
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for better caching)
COPY pyproject.toml ./

# Install uv for faster package installation
RUN pip install uv

# Install project dependencies
RUN uv pip install --system -e .

# Copy source code
COPY src/ ./src/

# Create data directory for local Qdrant storage
RUN mkdir -p /app/mem0_data && chown -R app:app /app

# Switch to non-root user
USER app

# Expose port for SSE transport
EXPOSE ${PORT}

# Health check for SSE mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default command - can be overridden for stdio mode
CMD ["python", "-m", "mcp_ai_memory.server"]
