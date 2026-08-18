"""
Kadi Teeri Online — Main Application Entrypoint

FastAPI server initialization, CORS middleware configuration, API routing,
and single-process React SPA static asset serving.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager

# Ensure backend directory is in sys.path for both root and sub-dir execution
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes import router as api_router

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
    title="Kadi Teeri Online",
    description="Multiplayer Indian Trick-Taking Card Game Server",
    version="0.1.0",
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

# Include REST & WebSocket Routes
app.include_router(api_router)

# ──────────────────────────── Static Files (React SPA) ────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all route to serve static assets and fallback to index.html for SPA routing."""
    potential_path = os.path.join(static_dir, full_path)
    if full_path and os.path.isfile(potential_path):
        return FileResponse(potential_path)

    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
