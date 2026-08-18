"""
Kadi Teeri Online — WebSocket Connection Manager Facade

Backward-compatibility entry point re-exporting ConnectionManager and ws_manager
from the `core.ws_manager` package.
"""

from __future__ import annotations

from core.ws_manager import ConnectionManager, manager, ws_manager

__all__ = ["ConnectionManager", "ws_manager", "manager"]
