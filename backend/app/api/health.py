"""
Health check endpoints for load balancers and system monitoring.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "game": "Kadi Teeri"}
