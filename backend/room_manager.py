"""
Kadi Teeri Online — Room Manager

Manages room lifecycle using Redis for distributed state, falling back to Supabase.
"""

from __future__ import annotations

import random
import logging
import json
from typing import Optional

from db import supabase
from models import (
    Player, GameState, GameStatus, RoomConfig,
)
from game_engine import deal_new_round
import redis_client

logger = logging.getLogger("kadi_teeri.room")


class RoomManager:
    """Room management backed by Redis for fast distributed state."""

    async def _generate_room_id(self) -> str:
        """Generate a unique 6-character room code."""
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        
        for _ in range(20):
            code = "".join(random.choice(chars) for _ in range(6))
            if redis_client.redis_client:
                exists = await redis_client.redis_client.exists(f"room:{code}")
                if not exists:
                    return code
            else:
                return code
        raise RuntimeError("Could not generate unique room code")

    async def get_room(self, room_id: str) -> Optional[GameState]:
        """Get a room's game state from Redis, fallback to DB."""
        if redis_client.redis_client:
            raw_data = await redis_client.redis_client.get(f"room:{room_id}")
            if raw_data:
                try:
                    return GameState.model_validate_json(raw_data)
                except Exception as e:
                    logger.error(f"Failed to parse room {room_id} from Redis: {e}")
        
        if supabase:
            try:
                res = supabase.table("rooms").select("*").eq("room_code", room_id).execute()
                if res.data:
                    game = GameState.model_validate(res.data[0]["game_state"])
                    if redis_client.redis_client:
                        await redis_client.redis_client.set(f"room:{room_id}", game.model_dump_json(), ex=86400)
                    return game
            except Exception as e:
                logger.error(f"Fallback DB load failed for room {room_id}: {e}")
                
        return None

    async def room_exists(self, room_id: str) -> bool:
        """Check if a room exists."""
        return await self.get_room(room_id) is not None

    async def save_room(self, room_id: str, game: GameState):
        """Save room state to Redis and Supabase."""
        if redis_client.redis_client:
            await redis_client.redis_client.set(f"room:{room_id}", game.model_dump_json(), ex=86400)
            
        if supabase:
            try:
                # In production you'd use a background task for Supabase saving to avoid blocking
                supabase.table("rooms").upsert({
                    "room_code": room_id,
                    "game_state": game.model_dump(mode="json")
                }).execute()
            except Exception as e:
                logger.error(f"Supabase save error for room {room_id}: {e}")

    async def delete_room(self, room_id: str):
        if redis_client.redis_client:
            await redis_client.redis_client.delete(f"room:{room_id}")
        if supabase:
            try:
                supabase.table("rooms").delete().eq("room_code", room_id).execute()
            except Exception as e:
                logger.error(f"Supabase delete error for room {room_id}: {e}")

    async def get_player_room(self, player_id: str) -> Optional[str]:
        """Get the room ID a player is in from Redis."""
        if redis_client.redis_client:
            return await redis_client.redis_client.get(f"player_room:{player_id}")
        return None

    async def set_player_room(self, player_id: str, room_id: str):
        if redis_client.redis_client:
            await redis_client.redis_client.set(f"player_room:{player_id}", room_id, ex=86400)

    async def clear_player_room(self, player_id: str):
        if redis_client.redis_client:
            await redis_client.redis_client.delete(f"player_room:{player_id}")

    async def create_room(self, player_id: str, player_name: str) -> tuple[str, GameState]:
        """Create a new room and add the creator as host."""
        room_id = await self._generate_room_id()

        game = GameState(
            status=GameStatus.LOBBY,
            config=RoomConfig(),
            players=[
                Player(id=player_id, name=player_name, seat=0, is_host=True)
            ],
        )
        game.log.append("Room created.")

        await self.save_room(room_id, game)
        await self.set_player_room(player_id, room_id)

        logger.info(f"Room {room_id} created by {player_name}")
        return room_id, game

    async def join_room(
        self, room_id: str, player_id: str, player_name: str
    ) -> tuple[Optional[str], Optional[GameState]]:
        """Join a room."""
        game = await self.get_room(room_id)
        if not game:
            return "Room not found.", None

        existing = next((p for p in game.players if p.id == player_id), None)
        if existing:
            existing.is_connected = True
            existing.name = player_name
            await self.set_player_room(player_id, room_id)
            game.log.append(f"{player_name} reconnected.")
            logger.info(f"Player {player_name} reconnected to room {room_id}")
            await self.save_room(room_id, game)
            return None, game

        if game.status != GameStatus.LOBBY:
            return "Game has already started.", None

        if len(game.players) >= game.config.player_count:
            return "Room is full.", None

        seat = len(game.players)
        player = Player(id=player_id, name=player_name, seat=seat, is_host=False)
        game.players.append(player)
        await self.set_player_room(player_id, room_id)

        game.log.append(f"{player_name} joined the room.")
        logger.info(f"Player {player_name} joined room {room_id} at seat {seat}")
        
        await self.save_room(room_id, game)
        return None, game

    async def leave_room(self, player_id: str) -> tuple[Optional[str], Optional[GameState], bool]:
        """Remove a player from their room."""
        room_id = await self.get_player_room(player_id)
        if not room_id:
            return None, None, False

        game = await self.get_room(room_id)
        if not game:
            await self.clear_player_room(player_id)
            return room_id, None, True

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            await self.clear_player_room(player_id)
            return room_id, game, False

        if game.status == GameStatus.LOBBY:
            game.players = [p for p in game.players if p.id != player_id]
            for i, p in enumerate(game.players):
                p.seat = i
            game.log.append(f"{player.name} left the room.")

            if not game.players:
                await self.delete_room(room_id)
                await self.clear_player_room(player_id)
                logger.info(f"Room {room_id} deleted (empty)")
                return room_id, None, True

            if player.is_host and game.players:
                game.players[0].is_host = True
                game.log.append(f"{game.players[0].name} is now the host.")
        else:
            player.is_connected = False
            game.log.append(f"{player.name} disconnected.")
            if player.is_host:
                self._transfer_host(game)

        await self.clear_player_room(player_id)
        await self.save_room(room_id, game)
        return room_id, game, False

    async def disconnect_player(self, player_id: str) -> tuple[Optional[str], Optional[GameState], bool]:
        """Handle a player disconnecting."""
        return await self.leave_room(player_id)

    def _transfer_host(self, game: GameState) -> None:
        """Transfer host to the oldest connected player."""
        for p in game.players:
            p.is_host = False
        for p in game.players:
            if p.is_connected:
                p.is_host = True
                game.log.append(f"{p.name} is now the host.")
                break

    async def configure_room(
        self, room_id: str, player_id: str,
        player_count: Optional[int] = None,
        deck_count: Optional[int] = None,
    ) -> Optional[str]:
        game = await self.get_room(room_id)
        if not game:
            return "Room not found."
        if game.status != GameStatus.LOBBY:
            return "Cannot configure after game has started."

        player = next((p for p in game.players if p.id == player_id), None)
        if not player or not player.is_host:
            return "Only the host can configure the room."

        if player_count is not None:
            if player_count < 4 or player_count > 12:
                return "Player count must be between 4 and 12."
            if player_count < len(game.players):
                return f"Cannot reduce below current player count ({len(game.players)})."
            game.config.player_count = player_count
            game.log.append(f"Player count set to {player_count}.")

            if player_count >= 9 and game.config.deck_count < 2:
                game.config.deck_count = 2
                game.log.append("Deck count auto-set to 2 (required for 9+ players).")

        if deck_count is not None:
            if deck_count not in (1, 2):
                return "Deck count must be 1 or 2."
            if deck_count == 1 and game.config.player_count >= 9:
                return "2 decks required for 9+ players."
            game.config.deck_count = deck_count
            game.log.append(f"Deck count set to {deck_count}.")

        await self.save_room(room_id, game)
        return None

    async def start_game(self, room_id: str, player_id: str) -> Optional[str]:
        game = await self.get_room(room_id)
        if not game:
            return "Room not found."
        if game.status != GameStatus.LOBBY:
            return "Game has already started."

        player = next((p for p in game.players if p.id == player_id), None)
        if not player or not player.is_host:
            return "Only the host can start the game."

        if len(game.players) < game.config.player_count:
            return f"Need {game.config.player_count} players to start (currently {len(game.players)})."

        deal_new_round(game, is_first=True)
        logger.info(f"Game started in room {room_id}")

        await self.save_room(room_id, game)
        return None

    async def restart_game(self, room_id: str, player_id: str) -> Optional[str]:
        game = await self.get_room(room_id)
        if not game:
            return "Room not found."
        if game.status != GameStatus.ROUND_END:
            return "Can only restart after a round has ended."

        deal_new_round(game, is_first=False)
        logger.info(f"New round started in room {room_id}")

        await self.save_room(room_id, game)
        return None

    async def remove_player(self, room_id: str, host_id: str, target_player_id: str) -> Optional[str]:
        game = await self.get_room(room_id)
        if not game:
            return "Room not found."

        host = next((p for p in game.players if p.id == host_id), None)
        if not host or not host.is_host:
            return "Only the host can remove players."

        target = next((p for p in game.players if p.id == target_player_id), None)
        if not target:
            return "Player not found."

        game.players = [p for p in game.players if p.id != target_player_id]
        await self.clear_player_room(target_player_id)
        
        for i, p in enumerate(game.players):
            p.seat = i
        game.log.append(f"{target.name} was removed by the host.")

        if game.status != GameStatus.LOBBY:
            game.status = GameStatus.LOBBY
            game.bidding = None
            game.trick = None
            game.hands = {}
            game.captured = {}
            game.bherus = []
            game.log.append("Game aborted because a player was removed.")

        await self.save_room(room_id, game)
        return None


# Singleton instance
room_manager = RoomManager()
