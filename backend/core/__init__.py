"""
Kadi Teeri Online — Core Management Package

Contains room state management (`RoomManager`) and WebSocket connection lifecycle (`ConnectionManager`).
"""

from __future__ import annotations

from core.room_manager import RoomManager, room_manager
from core.ws_manager import ConnectionManager
from core.ws_manager import manager as ws_manager

__all__ = [
    "RoomManager",
    "room_manager",
    "ConnectionManager",
    "ws_manager",
]
