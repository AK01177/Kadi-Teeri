"""
Kadi Teeri Online — API Package

Includes HTTP endpoints and WebSocket action handler routes.
"""

from __future__ import annotations

from api.routes import router as api_router

__all__ = ["api_router"]
