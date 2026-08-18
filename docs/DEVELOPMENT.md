# Local Development Guide

This guide describes how to set up, develop, and test **Kadi Teeri Online** locally.

## Prerequisites

- **Python** (3.10+) with `uv` installed (`pip install uv` or official `uv` installer)
- **Node.js** (v18+) and `npm`

## 1. Quick Start

### Backend Setup (with `uv`)

```bash
# From repository root:
uv sync

# Run backend development server
uv run uvicorn backend.main:app --reload --port 8000
```

The backend server runs on `http://localhost:8000`.

### Frontend Setup

```bash
cd frontend
npm install

# Run frontend development server (with proxy to backend port 8000)
npm run dev
```

Open `http://localhost:5173` in your browser.

## 2. Combined Production-Style Local Run

To test the application exactly as it runs in production on Render:

```bash
# 1. Build frontend static bundle into backend/static
cd frontend
npm run build
cd ..

# 2. Run backend (serves both API/WS and React SPA from backend/static)
uv run uvicorn backend.main:app --port 8000
```

Access `http://localhost:8000`.

## 3. Environment Variables

Create `.env` in the project root if using Supabase or custom ports:

```env
PORT=8000
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

Optional frontend environment variables (in `frontend/.env`):
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 4. Linting and Formatting

```bash
# Python linting
uv run ruff check .

# Frontend linting
cd frontend
npm run lint
```
