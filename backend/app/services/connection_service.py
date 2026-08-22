"""
Kadi Teeri Online — WebSocket Connection Manager Service

Manages per-room WebSocket connections, broadcasting, and private messaging
across multiple scalable instances using Redis Pub/Sub.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import WebSocket
from redis.asyncio.client import PubSub

from app.db.client import redis_client

logger = logging.getLogger("kadi_teeri.ws")


class ConnectionManager:
    """Manages WebSocket connections and Redis Pub/Sub."""

    def __init__(self) -> None:
        # Local connections: room_id -> {player_id -> WebSocket}
        self._rooms: dict[str, dict[str, WebSocket]] = {}
        # Reverse lookup: player_id -> room_id
        self._player_rooms: dict[str, str] = {}
        
        self._global_pubsub: PubSub | None = None
        self._global_listener_task: asyncio.Task | None = None
        self._listener_started = False

    async def _start_global_listener(self):
        if self._listener_started or not redis_client:
            return
        self._listener_started = True
        try:
            self._global_pubsub = redis_client.pubsub()
            await self._global_pubsub.psubscribe("room:events:*")
            self._global_listener_task = asyncio.create_task(self._listen_to_redis())
            logger.info("Started global Redis PubSub listener on 'room:events:*'")
        except Exception as e:
            logger.warning(f"Failed to start global Redis listener: {e}. Falling back to local mode.")
            self._listener_started = False

    async def add(self, room_id: str, player_id: str, ws: WebSocket) -> None:
        """Register a local WebSocket connection."""
        if not self._listener_started:
            await self._start_global_listener()
            
        if room_id not in self._rooms:
            self._rooms[room_id] = {}

        self._rooms[room_id][player_id] = ws
        self._player_rooms[player_id] = room_id
        logger.info(f"Player {player_id} connected locally to room {room_id}")

    def remove(self, player_id: str) -> str | None:
        """Remove a local player's connection."""
        room_id = self._player_rooms.pop(player_id, None)
        if room_id and room_id in self._rooms:
            self._rooms[room_id].pop(player_id, None)
            logger.info(f"Player {player_id} disconnected locally from room {room_id}")

            if not self._rooms[room_id]:
                # No more local players in this room
                del self._rooms[room_id]

        return room_id

    def get_ws(self, player_id: str) -> WebSocket | None:
        """Get local WebSocket for a player."""
        room_id = self._player_rooms.get(player_id)
        if room_id and room_id in self._rooms:
            return self._rooms[room_id].get(player_id)
        return None

    def get_room_connections(self, room_id: str) -> dict[str, WebSocket]:
        """Get all active WebSockets locally in a room."""
        return self._rooms.get(room_id, {})

    async def _listen_to_redis(self):
        """Listen for messages from Redis and forward them to local WebSockets."""
        if not self._global_pubsub:
            return
            
        try:
            async for message in self._global_pubsub.listen():
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")
                        
                    room_id = channel.split(":")[-1]
                    data = json.loads(message["data"])
                    await self._handle_redis_message(room_id, data)
        except asyncio.CancelledError:
            logger.info("Stopped global Redis listener")
        except Exception as e:
            logger.error(f"Global Redis listener error: {e}")
            self._listener_started = False

    async def _handle_redis_message(self, room_id: str, data: dict):
        """Process a message received from Redis Pub/Sub."""
        if room_id not in self._rooms:
            return

        if data.get("type") == "_internal_game_state":
            # This is a personalized game state broadcast
            game_state = data.get("game_state", {})
            hands = data.get("hands", {})
            exclude = data.get("exclude")

            # Parse seat string keys back to ints if necessary
            parsed_hands = {}
            for k, v in hands.items():
                parsed_hands[int(k)] = v

            for pid, ws in list(self._rooms[room_id].items()):
                if pid == exclude:
                    continue
                try:
                    # Find this player's seat
                    seat = None
                    for p in game_state.get("players", []):
                        if p.get("id") == pid:
                            seat = p.get("seat")
                            break

                    msg = {
                        "type": "game_state",
                        "game": game_state,
                    }

                    if seat is not None and seat in parsed_hands:
                        msg["hand"] = parsed_hands[seat]

                    await ws.send_json(msg)
                except Exception as e:
                    logger.warning(f"Failed to send local game state to {pid}: {e}")
                    self.remove(pid)
        else:
            # Standard broadcast message
            exclude = data.get("_exclude")
            # Create a clean payload to send to clients
            payload = {k: v for k, v in data.items() if k != "_exclude"}

            for pid, ws in list(self._rooms[room_id].items()):
                if pid == exclude:
                    continue
                try:
                    await ws.send_json(payload)
                except Exception as e:
                    logger.warning(f"Failed to broadcast local message to {pid}: {e}")
                    self.remove(pid)

    async def send_personal(self, player_id: str, message: dict) -> None:
        """Send a message to a specific player (assuming they are local)."""
        ws = self.get_ws(player_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to {player_id}: {e}")
                self.remove(player_id)
        else:
            # In a fully distributed system, we could publish a targeted message via Redis.
            pass

    async def broadcast(self, room_id: str, message: dict, exclude: str | None = None) -> None:
        """Broadcast a message to all players in a room via Redis."""
        if redis_client:
            payload = message.copy()
            if exclude:
                payload["_exclude"] = exclude
            channel_name = f"room:events:{room_id}"
            try:
                await redis_client.publish(channel_name, json.dumps(payload))
                return
            except Exception as e:
                logger.warning(f"Redis publish failed: {e}. Falling back to local.")

        # Fallback to local only
        await self._handle_redis_message(room_id, {**message, "_exclude": exclude})

    async def send_game_state_to_all(self, room_id: str, game_state: dict, hands: dict[int, list]) -> None:
        """Publish full game state to Redis for personalized local delivery."""
        # Serialize hands since we are putting it in JSON over Redis
        serialized_hands = {}
        for seat, cards in hands.items():
            hand_data = []
            for card in cards:
                if hasattr(card, "model_dump"):
                    hand_data.append(card.model_dump())
                elif isinstance(card, dict):
                    hand_data.append(card)
                else:
                    hand_data.append(card)
            serialized_hands[str(seat)] = hand_data

        payload = {
            "type": "_internal_game_state",
            "game_state": game_state,
            "hands": serialized_hands
        }

        if redis_client:
            channel_name = f"room:events:{room_id}"
            try:
                await redis_client.publish(channel_name, json.dumps(payload))
                return
            except Exception as e:
                logger.warning(f"Redis publish failed: {e}. Falling back to local.")

        # Fallback to local only
        await self._handle_redis_message(room_id, payload)


# Singleton instance
manager = ConnectionManager()
ws_manager = manager
