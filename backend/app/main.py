"""
Kadi Teeri Online — FastAPI Application Entrypoint

FastAPI server initialization, CORS middleware configuration, API routing,
and single-process React SPA static asset serving.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Ensure backend and backend/app directories are in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.api import api_router
from app.config import settings

# ──────────────────────────── Logging Configuration ────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("kadi_teeri")

# ──────────────────────────── Lifespan & Application Setup ────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for startup and shutdown logging."""
    logger.info("Kadi Teeri server starting...")
    yield
    logger.info("Kadi Teeri server shutting down.")


app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API and WebSocket routes
app.include_router(api_router)

# ──────────────────────────── Static Files (React SPA) ────────────────────────────

static_dir = backend_dir / "static"


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all route to serve static assets and fallback to index.html for SPA routing."""
    potential_path = static_dir / full_path
    if full_path and potential_path.is_file():
        return FileResponse(potential_path)

    index_path = static_dir / "index.html"
    if index_path.is_file():
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    return {"error": "Frontend build assets not found. Run 'npm run build' in the frontend directory."}


# ──────────────────────────── Local Execution ────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
