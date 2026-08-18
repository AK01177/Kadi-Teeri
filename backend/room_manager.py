"""
Kadi Teeri Online — Room Manager Facade

Backward-compatibility entry point re-exporting RoomManager and room_manager
from the `core.room_manager` package.
"""

from __future__ import annotations

from core.room_manager import RoomManager, room_manager

__all__ = ["RoomManager", "room_manager"]
