"""
Kadi Teeri Online — WebSocket Connection Manager Service

Manages per-room WebSocket connections, broadcasting, and private messaging.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger("kadi_teeri.ws")


class ConnectionManager:
    """Manages WebSocket connections grouped by room."""

    def __init__(self) -> None:
        # room_id -> {player_id -> WebSocket}
        self._rooms: dict[str, dict[str, WebSocket]] = {}
        # player_id -> room_id (reverse lookup)
        self._player_rooms: dict[str, str] = {}

    def add(self, room_id: str, player_id: str, ws: WebSocket) -> None:
        """Register a WebSocket connection for a player in a room."""
        if room_id not in self._rooms:
            self._rooms[room_id] = {}
        self._rooms[room_id][player_id] = ws
        self._player_rooms[player_id] = room_id
        logger.info(f"Player {player_id} connected to room {room_id}")

    def remove(self, player_id: str) -> str | None:
        """Remove a player's connection. Returns the room_id they were in."""
        room_id = self._player_rooms.pop(player_id, None)
        if room_id and room_id in self._rooms:
            self._rooms[room_id].pop(player_id, None)
            if not self._rooms[room_id]:
                del self._rooms[room_id]
        logger.info(f"Player {player_id} removed from room {room_id}")
        return room_id

    def get_ws(self, player_id: str) -> WebSocket | None:
        """Get the WebSocket connection for a specific player."""
        room_id = self._player_rooms.get(player_id)
        if room_id and room_id in self._rooms:
            return self._rooms[room_id].get(player_id)
        return None

    def get_room_connections(self, room_id: str) -> dict[str, WebSocket]:
        """Get all active WebSockets in a room."""
        return self._rooms.get(room_id, {})

    async def send_personal(self, player_id: str, message: dict) -> None:
        """Send a JSON message to a single player."""
        ws = self.get_ws(player_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to {player_id}: {e}")

    async def broadcast(self, room_id: str, message: dict) -> None:
        """Broadcast a JSON message to all connected players in a room."""
        connections = self.get_room_connections(room_id)
        if not connections:
            return

        disconnected: list[str] = []
        for pid, ws in connections.items():
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to {pid} in room {room_id}: {e}")
                disconnected.append(pid)

        for pid in disconnected:
            self.remove(pid)

    async def send_game_state_to_all(self, room_id: str, game_state: dict, hands: dict[int, list]) -> None:
        """Send game state to each connected player in a room, including their private hand."""
        if room_id not in self._rooms:
            return

        for pid, ws in list(self._rooms[room_id].items()):
            try:
                seat = None
                for p in game_state.get("players", []):
                    if p.get("id") == pid:
                        seat = p.get("seat")
                        break

                msg = {
                    "type": "game_state",
                    "game": game_state,
                }

                if seat is not None and seat in hands:
                    hand_data = []
                    for card in hands[seat]:
                        if hasattr(card, "model_dump"):
                            hand_data.append(card.model_dump())
                        elif isinstance(card, dict):
                            hand_data.append(card)
                        else:
                            hand_data.append(card)
                    msg["hand"] = hand_data

                await ws.send_json(msg)
            except Exception as e:
                logger.warning(f"Failed to send game state to {pid}: {e}")


# Singleton instance
manager = ConnectionManager()
ws_manager = manager
