# ──────────────────────────── Stage 1: Build Frontend ────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies using lockfile for deterministic builds
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build static bundle into ../backend/static
COPY frontend/ ./
RUN npm run build

# ──────────────────────────── Stage 2: Serve Backend + Static ────────────────────────────
FROM python:3.12-slim AS runtime

# Install uv for fast, reproducible dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv

ENV PORT=8000 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency definition files to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install python dependencies with uv into /app/.venv
RUN /uv/bin/uv sync --frozen --no-dev

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend static files from builder stage
COPY --from=frontend-builder /app/backend/static /app/backend/static

# Create non-root system user for security
RUN useradd -m -u 10001 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Start Uvicorn server, respecting PORT environment variable for Render compatibility
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
