"""
Central APIRouter combining health, room, network, and WebSocket endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.network import router as network_router
from app.api.rooms import router as rooms_router
from app.api.websocket import router as ws_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(rooms_router)
api_router.include_router(network_router)
api_router.include_router(ws_router)
