# Deployment Guide

This document describes how to deploy **Kadi Teeri Online** to cloud hosting platforms like **Render** as a monolithic containerized application.

## 1. Architectural Model

Kadi Teeri Online is designed to deploy as a single service:
- Stage 1 builds the React SPA into static assets.
- Stage 2 copies the assets into `backend/static/` and runs FastAPI via Uvicorn.
- FastAPI serves both API routes (`/api/*`), WebSockets (`/ws/*`), and SPA index routing (`/*`).

No external frontend hosting service or separate web server (e.g. Nginx) is needed.

## 2. Render Deployment Configuration

### Option A: Web Service (Native Python)

1. **Build Command**:
   ```bash
   cd frontend && npm install && npm run build && cd ../backend && pip install -r requirements.txt
   ```
2. **Start Command**:
   ```bash
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### Option B: Web Service (Docker)

1. Set Environment variable: `PORT` (automatically assigned by Render, defaults to 8000).
2. Connect your Git repository.
3. Select **Docker** environment. Render uses the root `Dockerfile`.

## 3. Docker Containerization

The production `Dockerfile` uses multi-stage builds:

```dockerfile
# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve Backend + Static
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/uv
RUN /uv/bin/uv sync --frozen --no-dev
COPY backend/ ./backend/
COPY --from=frontend-builder /app/backend/static /app/backend/static
EXPOSE 8000
CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## 4. Environment Variables in Production

| Variable | Required | Description | Default |
|---|:---:|---|---|
| `PORT` | Optional | Port for Uvicorn server | `8000` |
| `SUPABASE_URL` | Optional | Supabase Postgres REST API URL | None (runs in-memory) |
| `SUPABASE_KEY` | Optional | Supabase anon or service key | None (runs in-memory) |
