# syntax=docker/dockerfile:1.9
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the installer script
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && mv /root/.local/bin/uv /usr/local/bin/uv && rm /uv-installer.sh

# Configure uv for optimal Docker usage
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1


# Create non-root user
RUN groupadd -r app && useradd -r -d /app -g app app

# Copy project files for dependency installation (better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies first (better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy application code
COPY quantconnect_mcp/ ./quantconnect_mcp/


# Change ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

ENV MCP_TRANSPORT=streamable-http

# Run the application
CMD ["uv", "run", "-m", "quantconnect_mcp.main"]
