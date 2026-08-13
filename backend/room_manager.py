"""
Kadi Teeri Online — Room Manager

Manages room lifecycle: creation, joining, leaving, host transfer,
configuration, and game start/restart.
"""

from __future__ import annotations

import random
import string
import logging
from typing import Optional

from db import supabase
from models import (
    Player, GameState, GameStatus, RoomConfig,
)
from game_engine import deal_new_round

logger = logging.getLogger("kadi_teeri.room")


class RoomManager:
    """Room management backed by Supabase with in-memory caching."""

    def __init__(self):
        # room_id -> GameState
        self._rooms: dict[str, GameState] = {}
        # player_id -> room_id (reverse lookup)
        self._player_rooms: dict[str, str] = {}
        self._load_from_db()

    def _load_from_db(self):
        if not supabase:
            logger.warning("Supabase client not available. Running purely in-memory.")
            return
        try:
            res = supabase.table("rooms").select("*").execute()
            for row in res.data:
                room_code = row["room_code"]
                try:
                    game = GameState.model_validate(row["game_state"])
                    self._rooms[room_code] = game
                    for p in game.players:
                        self._player_rooms[p.id] = room_code
                except Exception as e:
                    logger.error(f"Failed to load room {room_code}: {e}")
            logger.info(f"Loaded {len(self._rooms)} rooms from Supabase.")
        except Exception as e:
            logger.error(f"Supabase load error: {e}")

    def save_room(self, room_id: str):
        if not supabase:
            return
        game = self._rooms.get(room_id)
        if game:
            try:
                supabase.table("rooms").upsert({
                    "room_code": room_id,
                    "game_state": game.model_dump(mode="json")
                }).execute()
            except Exception as e:
                logger.error(f"Supabase save error for room {room_id}: {e}")

    def delete_room(self, room_id: str):
        if not supabase:
            return
        try:
            supabase.table("rooms").delete().eq("room_code", room_id).execute()
        except Exception as e:
            logger.error(f"Supabase delete error for room {room_id}: {e}")

    def _generate_room_id(self) -> str:
        """Generate a unique 6-character room code."""
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No I, O, 0, 1 to avoid confusion
        for _ in range(20):
            code = "".join(random.choice(chars) for _ in range(6))
            if code not in self._rooms:
                return code
        raise RuntimeError("Could not generate unique room code")

    def create_room(self, player_id: str, player_name: str) -> tuple[str, GameState]:
        """Create a new room and add the creator as host."""
        room_id = self._generate_room_id()

        game = GameState(
            status=GameStatus.LOBBY,
            config=RoomConfig(),
            players=[
                Player(id=player_id, name=player_name, seat=0, is_host=True)
            ],
        )
        game.log.append("Room created.")

        self._rooms[room_id] = game
        self._player_rooms[player_id] = room_id
        
        self.save_room(room_id)

        logger.info(f"Room {room_id} created by {player_name}")
        return room_id, game

    def get_room(self, room_id: str) -> Optional[GameState]:
        """Get a room's game state, falling back to DB if not in memory."""
        game = self._rooms.get(room_id)
        if not game and supabase:
            try:
                res = supabase.table("rooms").select("*").eq("room_code", room_id).execute()
                if res.data:
                    game = GameState.model_validate(res.data[0]["game_state"])
                    self._rooms[room_id] = game
                    for p in game.players:
                        self._player_rooms[p.id] = room_id
                    logger.info(f"Room {room_id} loaded from DB fallback.")
            except Exception as e:
                logger.error(f"Fallback DB load failed for room {room_id}: {e}")
        return game

    def room_exists(self, room_id: str) -> bool:
        """Check if a room exists."""
        return self.get_room(room_id) is not None

    def get_player_room(self, player_id: str) -> Optional[str]:
        """Get the room ID a player is in."""
        return self._player_rooms.get(player_id)

    def join_room(
        self, room_id: str, player_id: str, player_name: str
    ) -> tuple[Optional[str], Optional[GameState]]:
        """
        Join a room. Returns (error_message, game_state).
        error_message is None on success.
        """
        game = self.get_room(room_id)
        if not game:
            return "Room not found.", None

        # Check if player is already in this room (reconnecting)
        existing = next((p for p in game.players if p.id == player_id), None)
        if existing:
            existing.is_connected = True
            existing.name = player_name  # Allow name update on reconnect
            self._player_rooms[player_id] = room_id
            game.log.append(f"{player_name} reconnected.")
            logger.info(f"Player {player_name} reconnected to room {room_id}")
            return None, game

        if game.status != GameStatus.LOBBY:
            return "Game has already started.", None

        if len(game.players) >= game.config.player_count:
            return "Room is full.", None

        seat = len(game.players)
        player = Player(id=player_id, name=player_name, seat=seat, is_host=False)
        game.players.append(player)
        self._player_rooms[player_id] = room_id

        game.log.append(f"{player_name} joined the room.")
        logger.info(f"Player {player_name} joined room {room_id} at seat {seat}")
        
        self.save_room(room_id)

        return None, game

    def leave_room(self, player_id: str) -> tuple[Optional[str], Optional[GameState], bool]:
        """
        Remove a player from their room.
        Returns (room_id, game_state, room_deleted).
        """
        room_id = self._player_rooms.pop(player_id, None)
        if not room_id:
            return None, None, False

        game = self.get_room(room_id)
        if not game:
            return room_id, None, True

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return room_id, game, False

        if game.status == GameStatus.LOBBY:
            # In lobby: fully remove the player
            game.players = [p for p in game.players if p.id != player_id]
            # Reassign seats
            for i, p in enumerate(game.players):
                p.seat = i
            game.log.append(f"{player.name} left the room.")

            if not game.players:
                # Room is empty, delete it
                del self._rooms[room_id]
                logger.info(f"Room {room_id} deleted (empty)")
                return room_id, None, True

            # Transfer host if needed
            if player.is_host and game.players:
                game.players[0].is_host = True
                game.log.append(f"{game.players[0].name} is now the host.")
        else:
            # During game: mark as disconnected
            player.is_connected = False
            game.log.append(f"{player.name} disconnected.")

            # Transfer host if needed
            if player.is_host:
                self._transfer_host(game)

        self.save_room(room_id)
        return room_id, game, False

    def disconnect_player(self, player_id: str) -> tuple[Optional[str], Optional[GameState], bool]:
        """
        Handle a player disconnecting (WebSocket closed).
        In lobby: remove them. During game: mark disconnected.
        """
        room_id = self._player_rooms.get(player_id)
        if not room_id:
            return None, None, False

        game = self.get_room(room_id)
        if not game:
            self._player_rooms.pop(player_id, None)
            return room_id, None, True

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            self._player_rooms.pop(player_id, None)
            return room_id, game, False

        if game.status == GameStatus.LOBBY:
            return self.leave_room(player_id)
        else:
            player.is_connected = False
            game.log.append(f"{player.name} disconnected.")
            if player.is_host:
                self._transfer_host(game)
            return room_id, game, False

    def _transfer_host(self, game: GameState) -> None:
        """Transfer host to the oldest connected player."""
        for p in game.players:
            p.is_host = False
        for p in game.players:
            if p.is_connected:
                p.is_host = True
                game.log.append(f"{p.name} is now the host.")
                break

    def configure_room(
        self, room_id: str, player_id: str,
        player_count: Optional[int] = None,
        deck_count: Optional[int] = None,
    ) -> Optional[str]:
        """
        Update room configuration. Host only, lobby only.
        Returns error message or None.
        """
        game = self.get_room(room_id)
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

            # Auto-force 2 decks for 9+ players (1 deck gives too few cards)
            if player_count >= 9 and game.config.deck_count < 2:
                game.config.deck_count = 2
                game.log.append("Deck count auto-set to 2 (required for 9+ players).")

        if deck_count is not None:
            if deck_count not in (1, 2):
                return "Deck count must be 1 or 2."
            # Don't allow 1 deck for 9+ players
            if deck_count == 1 and game.config.player_count >= 9:
                return "2 decks required for 9+ players."
            game.config.deck_count = deck_count
            game.log.append(f"Deck count set to {deck_count}.")

        self.save_room(room_id)
        return None

    def start_game(self, room_id: str, player_id: str) -> Optional[str]:
        """
        Start the game. Host only.
        Returns error message or None.
        """
        game = self.get_room(room_id)
        if not game:
            return "Room not found."
        if game.status != GameStatus.LOBBY:
            return "Game has already started."

        player = next((p for p in game.players if p.id == player_id), None)
        if not player or not player.is_host:
            return "Only the host can start the game."

        if len(game.players) < game.config.player_count:
            return f"Need {game.config.player_count} players to start (currently {len(game.players)})."

        # Deal first round
        deal_new_round(game, is_first=True)
        logger.info(f"Game started in room {room_id}")

        self.save_room(room_id)
        return None

    def restart_game(self, room_id: str, player_id: str) -> Optional[str]:
        """
        Start a new round after the previous one ended.
        Returns error message or None.
        """
        game = self.get_room(room_id)
        if not game:
            return "Room not found."
        if game.status != GameStatus.ROUND_END:
            return "Can only restart after a round has ended."

        deal_new_round(game, is_first=False)
        logger.info(f"New round started in room {room_id}")

        self.save_room(room_id)
        return None

    def remove_player(self, room_id: str, host_id: str, target_player_id: str) -> Optional[str]:
        """Host removes a disconnected player."""
        game = self.get_room(room_id)
        if not game:
            return "Room not found."

        host = next((p for p in game.players if p.id == host_id), None)
        if not host or not host.is_host:
            return "Only the host can remove players."

        target = next((p for p in game.players if p.id == target_player_id), None)
        if not target:
            return "Player not found."
        if target.is_connected:
            return "Can only remove disconnected players."

        game.players = [p for p in game.players if p.id != target_player_id]
        self._player_rooms.pop(target_player_id, None)
        # Reassign seats
        for i, p in enumerate(game.players):
            p.seat = i
        game.log.append(f"{target.name} was removed by the host.")

        # If the game was active, it cannot continue with missing players.
        if game.status != GameStatus.LOBBY:
            game.status = GameStatus.LOBBY
            game.bidding = None
            game.trick = None
            game.hands = {}
            game.captured = {}
            game.bherus = []
            game.log.append("Game aborted because a player was removed.")

        self.save_room(room_id)
        return None


# Singleton instance
room_manager = RoomManager()
