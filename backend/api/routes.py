"""
Kadi Teeri Online — API & WebSocket Routes

Contains REST endpoints for health checks, room creation, room inspection,
LAN discovery, and the main real-time WebSocket protocol router.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import socket
import subprocess
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from core.room_manager import room_manager
from core.ws_manager import ws_manager
from game_engine import (
    _determine_trick_winner,
    accept_challenge,
    assign_bherus,
    expire_trump_challenge,
    pass_bid,
    pass_challenge_bid,
    place_bid,
    place_challenge_bid,
    play_card,
    resolve_trick,
    sanitize_game_state,
    select_trump,
    validate_bheru_calls,
    validate_bid,
    validate_challenge_accept,
    validate_challenge_bid,
    validate_challenge_pass,
    validate_play,
    validate_trump,
)
from models import (
    Card,
    ClientMessage,
    GameState,
    GameStatus,
)

logger = logging.getLogger("kadi_teeri.api")
router = APIRouter()

# ──────────────────────────── Request / Response Schemas ────────────────────────────


class CreateRoomRequest(BaseModel):
    """Payload for creating a new game room."""
    player_name: str


class CreateRoomResponse(BaseModel):
    """Response returned upon successful room creation."""
    room_id: str
    player_id: str


class RoomInfoResponse(BaseModel):
    """Room metadata returned for the pre-join lobby check."""
    exists: bool
    status: Optional[str] = None
    player_count: int = 0
    max_players: int = 4
    can_join: bool = False


class NetworkInfoResponse(BaseModel):
    """LAN IP addresses and host configuration for local network multiplayer."""
    lan_ips: list[str]
    port: int
    hostname: str


# ──────────────────────────── REST Endpoints ────────────────────────────


@router.get("/api/health")
async def health():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "ok", "game": "Kadi Teeri"}


@router.post("/api/rooms", response_model=CreateRoomResponse)
async def create_room(req: CreateRoomRequest):
    """Create a new room and return the unique room ID and player ID."""
    player_id = str(uuid.uuid4())
    name = req.player_name.strip()[:18]
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")

    room_id, _ = room_manager.create_room(player_id, name)
    return CreateRoomResponse(room_id=room_id, player_id=player_id)


@router.get("/api/rooms/{room_id}", response_model=RoomInfoResponse)
async def get_room_info(room_id: str):
    """Inspect basic room info to validate join code before connecting."""
    room_id = room_id.upper()
    game = room_manager.get_room(room_id)
    if not game:
        return RoomInfoResponse(exists=False)
    return RoomInfoResponse(
        exists=True,
        status=game.status.value,
        player_count=len(game.players),
        max_players=game.config.player_count,
        can_join=game.status == GameStatus.LOBBY and len(game.players) < game.config.player_count,
    )


@router.get("/api/network-info", response_model=NetworkInfoResponse)
async def get_network_info():
    """Discover server LAN IP addresses for local network host connections."""
    lan_ips = set()
    hostname = socket.gethostname()

    # 1. Standard DNS addrinfo resolution
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                lan_ips.add(ip)
    except Exception:
        pass

    # 2. UDP socket routing probes to common gateways
    dummy_ips = ["8.8.8.8", "192.168.1.1", "10.0.0.1", "172.16.0.1", "192.168.43.1"]
    for test_ip in dummy_ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.2)
            s.connect((test_ip, 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                lan_ips.add(ip)
            s.close()
        except Exception:
            pass

    # 3. System command fallbacks for POSIX systems
    if platform.system() != "Windows":
        try:
            output = subprocess.check_output(["hostname", "-I"], stderr=subprocess.DEVNULL).decode("utf-8")
            for ip in output.split():
                if ip and not ip.startswith("127."):
                    lan_ips.add(ip)
        except Exception:
            pass

    return NetworkInfoResponse(
        lan_ips=list(lan_ips),
        port=int(os.environ.get("PORT", 8000)),
        hostname=hostname,
    )


# ──────────────────────────── Real-Time WebSocket Handler ────────────────────────────


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str):
    """Primary WebSocket connection handler managing game actions and broadcasts."""
    room_id = room_id.upper()
    await ws.accept()

    player_id: Optional[str] = None

    try:
        # Initial authentication handshake (join or rejoin message required)
        raw = await ws.receive_text()
        msg = ClientMessage.model_validate_json(raw)

        if msg.type == "join":
            name = (msg.name or "").strip()[:18]
            if not name:
                await ws.send_json({"type": "error", "error": "Name is required."})
                await ws.close()
                return

            raw_data = json.loads(raw)
            provided_player_id = raw_data.get("player_id")
            player_id = provided_player_id if provided_player_id else str(uuid.uuid4())

            error, game = room_manager.join_room(room_id, player_id, name)
            if error:
                await ws.send_json({"type": "error", "error": error})
                await ws.close()
                return

            ws_manager.add(room_id, player_id, ws)
            player = next((p for p in game.players if p.id == player_id), None)

            await ws.send_json({
                "type": "welcome",
                "player_id": player_id,
                "room_id": room_id,
                "seat": player.seat if player else 0,
                "is_host": player.is_host if player else False,
            })
            await _broadcast_full_state(room_id, game)

        elif msg.type == "rejoin":
            raw_data = json.loads(raw)
            player_id = raw_data.get("player_id")
            if not player_id:
                await ws.send_json({"type": "error", "error": "Player ID required for rejoin."})
                await ws.close()
                return

            error, game = room_manager.join_room(room_id, player_id, msg.name or "Player")
            if error:
                await ws.send_json({"type": "error", "error": error})
                await ws.close()
                return

            ws_manager.add(room_id, player_id, ws)
            player = next((p for p in game.players if p.id == player_id), None)

            await ws.send_json({
                "type": "welcome",
                "player_id": player_id,
                "room_id": room_id,
                "seat": player.seat if player else 0,
                "is_host": player.is_host if player else False,
            })
            await _broadcast_full_state(room_id, game)

        else:
            await ws.send_json({"type": "error", "error": "First message must be 'join' or 'rejoin'."})
            await ws.close()
            return

        # Main action loop
        while True:
            raw = await ws.receive_text()
            try:
                msg = ClientMessage.model_validate_json(raw)
                raw_data = json.loads(raw)
            except Exception as e:
                await ws.send_json({"type": "error", "error": f"Invalid message: {e}"})
                continue

            if msg.type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            await handle_message(ws, room_id, player_id, msg, raw_data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: player={player_id}, room={room_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        if player_id:
            ws_manager.remove(player_id)
            rid, game, deleted = room_manager.disconnect_player(player_id)
            if game and not deleted:
                await _broadcast_full_state(rid, game)


async def handle_message(
    ws: WebSocket,
    room_id: str,
    player_id: str,
    msg: ClientMessage,
    raw_data: dict,
):
    """Route client actions to game engine logic and broadcast resulting state."""
    game = room_manager.get_room(room_id)
    if not game:
        await ws.send_json({"type": "error", "error": "Room not found."})
        return

    player = next((p for p in game.players if p.id == player_id), None)
    if not player:
        await ws.send_json({"type": "error", "error": "You are not in this room."})
        return

    seat = player.seat

    if msg.type == "configure":
        error = room_manager.configure_room(
            room_id,
            player_id,
            player_count=msg.player_count,
            deck_count=msg.deck_count,
        )
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        await _broadcast_full_state(room_id, game)

    elif msg.type == "start_game":
        error = room_manager.start_game(room_id, player_id)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        await _broadcast_full_state(room_id, game)

    elif msg.type == "bid":
        if msg.amount is None:
            await ws.send_json({"type": "error", "error": "Bid amount required."})
            return
        error = validate_bid(game, seat, msg.amount)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        place_bid(game, seat, msg.amount)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "pass":
        if game.status != GameStatus.BIDDING or game.turn_seat != seat:
            await ws.send_json({"type": "error", "error": "Cannot pass right now."})
            return
        pass_bid(game, seat)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "select_trump":
        if not msg.suit:
            await ws.send_json({"type": "error", "error": "Suit required."})
            return
        error = validate_trump(game, seat, msg.suit)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        select_trump(game, seat, msg.suit)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

        # Handle automatic challenge expiration timer
        if game.status == GameStatus.TRUMP_CHALLENGE:
            async def _auto_expire_challenge():
                await asyncio.sleep(10)
                g = room_manager.get_room(room_id)
                if g and g.status == GameStatus.TRUMP_CHALLENGE and g.challenge_duel_seats is None:
                    expire_trump_challenge(g)
                    room_manager.save_room(room_id)
                    await _broadcast_full_state(room_id, g)
            asyncio.create_task(_auto_expire_challenge())

    elif msg.type == "challenge_accept":
        error = validate_challenge_accept(game, seat)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        accept_challenge(game, seat)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "challenge_bid":
        error = validate_challenge_bid(game, seat)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        place_challenge_bid(game, seat)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "challenge_pass":
        error = validate_challenge_pass(game, seat)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        pass_challenge_bid(game, seat)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "select_bherus":
        calls = msg.calls or []
        error = validate_bheru_calls(game, seat, calls)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        assign_bherus(game, seat, calls)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "play_card":
        if not msg.rank or not msg.suit:
            await ws.send_json({"type": "error", "error": "Card rank and suit required."})
            return
        card = Card(
            rank=msg.rank,
            suit=msg.suit,
            deck_index=raw_data.get("deck_index", 0),
        )
        error = validate_play(game, seat, card)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return

        trick_completed = play_card(game, seat, card, auto_resolve=False)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

        if trick_completed and game.trick:
            await asyncio.sleep(2.0)
            cards_played = game.trick.cards_played
            lead_suit = game.trick.lead_suit
            trump = game.trump_suit
            winner_entry = _determine_trick_winner(cards_played, lead_suit, trump)
            winner_seat = winner_entry.seat
            winner_name = game.players[winner_seat].name
            points = sum(tp.card.points() for tp in cards_played)

            await ws_manager.broadcast(room_id, {
                "type": "trick_winner",
                "name": winner_name,
                "points": points,
            })
            await asyncio.sleep(2.0)
            resolve_trick(game)
            room_manager.save_room(room_id)
            await _broadcast_full_state(room_id, game)

    elif msg.type == "restart":
        error = room_manager.restart_game(room_id, player_id)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        await _broadcast_full_state(room_id, game)

    elif msg.type == "update_ping":
        if msg.ping_ms is not None:
            player.ping_ms = msg.ping_ms
            await ws_manager.broadcast(room_id, {
                "type": "ping_update",
                "player_id": player_id,
                "ping_ms": player.ping_ms,
            })

    elif msg.type == "remove_player":
        target_id = raw_data.get("target_player_id")
        if not target_id:
            await ws.send_json({"type": "error", "error": "Target player ID required."})
            return
        error = room_manager.remove_player(room_id, player_id, target_id)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return

        target_ws = ws_manager.get_ws(target_id)
        if target_ws:
            try:
                await target_ws.send_json({"type": "error", "error": "You have been kicked by the host."})
                await target_ws.close()
            except Exception:
                pass
            ws_manager.remove(target_id)

        await _broadcast_full_state(room_id, game)

    else:
        await ws.send_json({"type": "error", "error": f"Unknown message type: {msg.type}"})


async def _broadcast_full_state(room_id: str, game: GameState) -> None:
    """Sanitize and broadcast state updates privately to each connected room member."""
    sanitized = sanitize_game_state(game)
    hands = {s: cards for s, cards in game.hands.items()} if game.hands else {}
    await ws_manager.send_game_state_to_all(room_id, sanitized, hands)
