"""
Kadi Teeri Online — WebSocket Connection Manager

Manages per-room WebSocket connections, broadcasting, and private messaging.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import WebSocket

logger = logging.getLogger("kadi_teeri.ws")


class ConnectionManager:
    """Manages WebSocket connections grouped by room."""

    def __init__(self):
        # room_id -> {player_id -> WebSocket}
        self._rooms: dict[str, dict[str, WebSocket]] = {}
        # player_id -> room_id (reverse lookup)
        self._player_rooms: dict[str, str] = {}

    def add(self, room_id: str, player_id: str, ws: WebSocket):
        """Register a WebSocket connection for a player in a room."""
        if room_id not in self._rooms:
            self._rooms[room_id] = {}
        self._rooms[room_id][player_id] = ws
        self._player_rooms[player_id] = room_id
        logger.info(f"Player {player_id} connected to room {room_id}")

    def remove(self, player_id: str) -> Optional[str]:
        """Remove a player's connection. Returns the room_id they were in."""
        room_id = self._player_rooms.pop(player_id, None)
        if room_id and room_id in self._rooms:
            self._rooms[room_id].pop(player_id, None)
            if not self._rooms[room_id]:
                del self._rooms[room_id]
            logger.info(f"Player {player_id} disconnected from room {room_id}")
        return room_id

    def get_ws(self, player_id: str) -> Optional[WebSocket]:
        """Get the WebSocket for a specific player."""
        room_id = self._player_rooms.get(player_id)
        if room_id and room_id in self._rooms:
            return self._rooms[room_id].get(player_id)
        return None

    def get_room_players(self, room_id: str) -> list[str]:
        """Get all connected player IDs in a room."""
        if room_id in self._rooms:
            return list(self._rooms[room_id].keys())
        return []

    async def send_to(self, player_id: str, message: dict):
        """Send a message to a specific player."""
        ws = self.get_ws(player_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to {player_id}: {e}")
                self.remove(player_id)

    async def broadcast(self, room_id: str, message: dict, exclude: Optional[str] = None):
        """Broadcast a message to all players in a room."""
        if room_id not in self._rooms:
            return
        tasks = []
        disconnected = []
        for pid, ws in self._rooms[room_id].items():
            if pid == exclude:
                continue
            try:
                tasks.append(ws.send_json(message))
            except Exception:
                disconnected.append(pid)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Broadcast error: {result}")

        for pid in disconnected:
            self.remove(pid)

    async def send_game_state_to_all(self, room_id: str, game_state: dict, hands: dict[int, list]):
        """
        Send personalized game state to each player.
        Each player gets the full game state but only their own hand.
        """
        if room_id not in self._rooms:
            return

        for pid, ws in list(self._rooms[room_id].items()):
            try:
                # Find this player's seat from the game state
                seat = None
                for p in game_state.get("players", []):
                    if p.get("id") == pid:
                        seat = p.get("seat")
                        break

                # Build personalized message
                msg = {
                    "type": "game_state",
                    "game": game_state,
                }

                # Add their hand if they have one
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
