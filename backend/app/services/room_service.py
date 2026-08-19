"""
Kadi Teeri Online — Room Manager Service

Manages room lifecycle: creation, joining, leaving, host transfer,
configuration, and game start/restart with Supabase persistence.
"""

from __future__ import annotations

import logging
import random

from app.db import supabase
from app.game.scoring import deal_new_round
from app.models.game import (
    GameState,
    GameStatus,
    Player,
    RoomConfig,
)

logger = logging.getLogger("kadi_teeri.room")


class RoomManager:
    """Room management backed by Supabase with in-memory caching."""

    def __init__(self) -> None:
        self._rooms: dict[str, GameState] = {}
        self._player_rooms: dict[str, str] = {}
        self._load_from_db()

    def _load_from_db(self) -> None:
        if not supabase:
            logger.warning("Supabase client not available. Running purely in-memory.")
            return
        try:
            res = supabase.table("rooms").select("*").execute()
            for row in res.data:
                rid = row["id"]
                state_dict = row["state"]
                try:
                    game = GameState.model_validate(state_dict)
                    self._rooms[rid] = game
                    for p in game.players:
                        self._player_rooms[p.id] = rid
                except Exception as parse_err:
                    logger.error(f"Failed to parse room {rid} state from DB: {parse_err}")
            logger.info(f"Loaded {len(self._rooms)} rooms from Supabase.")
        except Exception as e:
            logger.error(f"Failed to load rooms from Supabase: {e}")

    def save_room(self, room_id: str) -> None:
        """Persist a room's state to Supabase."""
        if not supabase:
            return
        game = self._rooms.get(room_id)
        if not game:
            return
        try:
            payload = {
                "id": room_id,
                "state": game.model_dump(),
                "updated_at": "now()",
            }
            supabase.table("rooms").upsert(payload).execute()
        except Exception as e:
            logger.error(f"Failed to save room {room_id} to Supabase: {e}")

    def _delete_room_from_db(self, room_id: str) -> None:
        if not supabase:
            return
        try:
            supabase.table("rooms").delete().eq("id", room_id).execute()
        except Exception as e:
            logger.error(f"Failed to delete room {room_id} from Supabase: {e}")

    def _generate_code(self) -> str:
        """Generate a 6-letter room code (uppercase)."""
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        while True:
            code = "".join(random.choices(chars, k=6))
            if code not in self._rooms:
                return code

    def create_room(self, host_player_id: str, host_name: str) -> tuple[str, GameState]:
        """Create a new room with host as player 0."""
        room_id = self._generate_code()

        host = Player(
            id=host_player_id,
            name=host_name,
            seat=0,
            is_host=True,
            is_connected=True,
        )

        game = GameState(
            status=GameStatus.LOBBY,
            config=RoomConfig(),
            players=[host],
            dealer=0,
            log=[f"Room created by {host_name}."],
        )

        self._rooms[room_id] = game
        self._player_rooms[host_player_id] = room_id
        self.save_room(room_id)
        logger.info(f"Room {room_id} created by {host_name} ({host_player_id})")
        return room_id, game

    def get_room(self, room_id: str) -> GameState | None:
        """Get GameState for a room."""
        return self._rooms.get(room_id.upper())

    def get_player_room(self, player_id: str) -> tuple[str | None, GameState | None]:
        """Find room by player ID."""
        rid = self._player_rooms.get(player_id)
        if rid:
            return rid, self._rooms.get(rid)
        return None, None

    def join_room(self, room_id: str, player_id: str, player_name: str) -> tuple[str | None, GameState | None, str | None]:
        """Join an existing room or reconnect. Returns (error, game, final_player_id)."""
        room_id = room_id.upper()
        game = self._rooms.get(room_id)
        if not game:
            return "Room not found.", None, None

        existing = next((p for p in game.players if p.id == player_id), None)
        if existing:
            existing.is_connected = True
            existing.name = player_name
            self._player_rooms[player_id] = room_id
            game.log.append(f"{player_name} reconnected.")
            self.save_room(room_id)
            return None, game, player_id

        # Allow reclaiming a disconnected seat by exact name match
        disconnected_match = next((p for p in game.players if p.name.lower() == player_name.lower() and not p.is_connected), None)
        if disconnected_match:
            disconnected_match.is_connected = True
            disconnected_match.name = player_name  # Ensure exact case matches their new input
            self._player_rooms[disconnected_match.id] = room_id
            game.log.append(f"{player_name} reconnected to their seat.")
            self.save_room(room_id)
            return None, game, disconnected_match.id

        if game.status != GameStatus.LOBBY:
            return "Game already in progress.", None, None

        if len(game.players) >= game.config.player_count:
            return "Room is full.", None, None

        taken_seats = {p.seat for p in game.players}
        seat = 0
        for s in range(game.config.player_count):
            if s not in taken_seats:
                seat = s
                break

        new_player = Player(
            id=player_id,
            name=player_name,
            seat=seat,
            is_host=False,
            is_connected=True,
        )

        game.players.append(new_player)
        game.players.sort(key=lambda p: p.seat)
        self._player_rooms[player_id] = room_id
        game.log.append(f"{player_name} joined the room.")
        self.save_room(room_id)

        logger.info(f"Player {player_name} ({player_id}) joined room {room_id} at seat {seat}")
        return None, game, player_id

    def disconnect_player(self, player_id: str) -> tuple[str | None, GameState | None, bool]:
        """Handle a player disconnection. Returns (room_id, game, deleted_flag)."""
        rid = self._player_rooms.get(player_id)
        if not rid:
            return None, None, False

        game = self._rooms.get(rid)
        if not game:
            self._player_rooms.pop(player_id, None)
            return None, None, False

        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return rid, game, False

        player.is_connected = False
        game.log.append(f"{player.name} disconnected.")

        all_dc = all(not p.is_connected for p in game.players)
        if all_dc and game.status == GameStatus.LOBBY:
            for p in game.players:
                self._player_rooms.pop(p.id, None)
            self._rooms.pop(rid, None)
            self._delete_room_from_db(rid)
            logger.info(f"Room {rid} deleted (all players disconnected).")
            return rid, None, True

        if player.is_host:
            connected = [p for p in game.players if p.is_connected]
            if connected:
                new_host = connected[0]
                player.is_host = False
                new_host.is_host = True
                game.log.append(f"{new_host.name} is now the host.")
            else:
                other = [p for p in game.players if p.id != player_id]
                if other:
                    player.is_host = False
                    other[0].is_host = True

        self.save_room(rid)
        return rid, game, False

    def remove_player(self, room_id: str, host_id: str, target_player_id: str) -> str | None:
        """Host kicks a player from lobby or inactive room."""
        room_id = room_id.upper()
        game = self._rooms.get(room_id)
        if not game:
            return "Room not found."

        host = next((p for p in game.players if p.id == host_id), None)
        if not host or not host.is_host:
            return "Only the host can remove players."

        if target_player_id == host_id:
            return "You cannot remove yourself."

        target = next((p for p in game.players if p.id == target_player_id), None)
        if not target:
            return "Player not found in room."

        game.players.remove(target)
        self._player_rooms.pop(target_player_id, None)
        game.log.append(f"{target.name} was removed by host.")

        for i, p in enumerate(sorted(game.players, key=lambda x: x.seat)):
            p.seat = i

        self.save_room(room_id)
        logger.info(f"Player {target_player_id} removed from room {room_id} by host {host_id}")
        return None

    def configure_room(
        self,
        room_id: str,
        player_id: str,
        player_count: int | None = None,
        deck_count: int | None = None,
    ) -> str | None:
        """Update room config (host only, lobby phase only)."""
        room_id = room_id.upper()
        game = self._rooms.get(room_id)
        if not game:
            return "Room not found."

        player = next((p for p in game.players if p.id == player_id), None)
        if not player or not player.is_host:
            return "Only the host can configure room settings."

        if game.status != GameStatus.LOBBY:
            return "Room can only be configured in lobby."

        if player_count is not None:
            if player_count < 4 or player_count > 12:
                return "Player count must be between 4 and 12."
            if player_count < len(game.players):
                return f"Cannot set player limit below current player count ({len(game.players)})."
            game.config.player_count = player_count

        if deck_count is not None:
            if deck_count not in (1, 2):
                return "Deck count must be 1 or 2."
            game.config.deck_count = deck_count

        game.log.append(f"Room configured: {game.config.player_count} players, {game.config.deck_count} deck(s).")
        self.save_room(room_id)
        return None

    def start_game(self, room_id: str, player_id: str) -> str | None:
        """Start the game from lobby phase."""
        room_id = room_id.upper()
        game = self._rooms.get(room_id)
        if not game:
            return "Room not found."

        player = next((p for p in game.players if p.id == player_id), None)
        if not player or not player.is_host:
            return "Only the host can start the game."

        if game.status != GameStatus.LOBBY:
            return "Game has already started."

        if len(game.players) < game.config.player_count:
            return f"Need {game.config.player_count} players to start (currently {len(game.players)})."

        game.dealer = 0
        game.rounds_played = 0
        game.wins = {p.id: 0 for p in game.players}
        deal_new_round(game)
        self.save_room(room_id)

        logger.info(f"Game started in room {room_id}")
        return None

    def restart_game(self, room_id: str, player_id: str) -> str | None:
        """Restart for another round after round end."""
        room_id = room_id.upper()
        game = self._rooms.get(room_id)
        if not game:
            return "Room not found."

        player = next((p for p in game.players if p.id == player_id), None)
        if not player or not player.is_host:
            return "Only the host can start the next round."

        if game.status != GameStatus.ROUND_END:
            return "Round is not over yet."

        deal_new_round(game)
        self.save_room(room_id)
        return None


# Singleton instance
room_service = RoomManager()
room_manager = room_service
