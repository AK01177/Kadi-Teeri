"""
Kadi Teeri Online — FastAPI Application

Main entry point: REST endpoints + WebSocket handler.
The WebSocket handler processes all game actions.
"""

from __future__ import annotations

import os
import json
import logging
import uuid
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

from models import (
    GameStatus, Card, BheruCall, BheruCallMode,
    ClientMessage, ServerMessage,
)
from game_engine import (
    validate_bid, place_bid, pass_bid,
    validate_trump, select_trump,
    validate_challenge_accept, accept_challenge, expire_trump_challenge,
    validate_challenge_bid, place_challenge_bid,
    validate_challenge_pass, pass_challenge_bid,
    validate_bheru_calls, assign_bherus,
    validate_play, play_card, resolve_trick,
    deal_new_round, sanitize_game_state,
)
from room_manager import room_manager
from ws_manager import manager as ws_manager
from redis_client import redis_client

# Set for holding strong references to background tasks to prevent garbage collection
background_tasks = set()

# ──────────────────────────── Logging ────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("kadi_teeri")


# ──────────────────────────── App ────────────────────────────

from redis_client import init_redis, close_redis

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Kadi Teeri server starting...")
    await init_redis()
    yield
    await close_redis()
    logger.info("Kadi Teeri server shutting down.")


app = FastAPI(
    title="Kadi Teeri Online",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────── REST Endpoints ────────────────────────────


class CreateRoomRequest(BaseModel):
    player_name: str


class CreateRoomResponse(BaseModel):
    room_id: str
    player_id: str


class RoomInfoResponse(BaseModel):
    exists: bool
    status: str | None = None
    player_count: int = 0
    max_players: int = 4
    can_join: bool = False


@app.get("/api/health")
async def health():
    return {"status": "ok", "game": "Kadi Teeri"}


@app.post("/api/rooms", response_model=CreateRoomResponse)
async def create_room(req: CreateRoomRequest):
    """Create a new room and return the room ID and player ID."""
    player_id = str(uuid.uuid4())
    name = req.player_name.strip()[:18]
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")

    room_id, game = await room_manager.create_room(player_id, name)
    return CreateRoomResponse(room_id=room_id, player_id=player_id)


@app.get("/api/rooms/{room_id}", response_model=RoomInfoResponse)
async def get_room_info(room_id: str):
    """Get basic room info (for the join page)."""
    room_id = room_id.upper()
    game = await room_manager.get_room(room_id)
    if not game:
        return RoomInfoResponse(exists=False)
    return RoomInfoResponse(
        exists=True,
        status=game.status.value,
        player_count=len(game.players),
        max_players=game.config.player_count,
        can_join=game.status == GameStatus.LOBBY and len(game.players) < game.config.player_count,
    )


class NetworkInfoResponse(BaseModel):
    lan_ips: list[str]
    port: int
    hostname: str


@app.get("/api/network-info", response_model=NetworkInfoResponse)
async def get_network_info():
    """Return the server's LAN IP addresses for local play."""
    import socket
    import subprocess
    import platform
    
    lan_ips = set()
    hostname = socket.gethostname()
    
    # 1. Try standard getaddrinfo
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                lan_ips.add(ip)
    except Exception:
        pass

    # 2. Try dummy UDP connections (works even if default gateway is missing for some subnets)
    # We try both a public IP and common private gateways
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

    # 3. If on Linux/Mac, try hostname -I or ifconfig as a highly reliable fallback
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


# ──────────────────────────── WebSocket Handler ────────────────────────────


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str):
    """Main WebSocket endpoint for a room."""
    room_id = room_id.upper()
    await ws.accept()

    player_id: str | None = None

    try:
        # Wait for the join message
        raw = await ws.receive_text()
        msg = ClientMessage.model_validate_json(raw)

        if msg.type == "join":
            name = (msg.name or "").strip()[:18]
            if not name:
                await ws.send_json({"type": "error", "error": "Name is required."})
                await ws.close()
                return

            # Check if they're providing a player_id (reconnecting)
            provided_player_id = msg.player_id

            if provided_player_id:
                player_id = provided_player_id
            else:
                player_id = str(uuid.uuid4())

            error, game = await room_manager.join_room(room_id, player_id, name)
            if error:
                await ws.send_json({"type": "error", "error": error})
                await ws.close()
                return

            # Register WebSocket connection
            await ws_manager.add(room_id, player_id, ws)

            # Find this player's seat and host status
            player = next((p for p in game.players if p.id == player_id), None)

            # Send welcome message
            await ws.send_json({
                "type": "welcome",
                "player_id": player_id,
                "room_id": room_id,
                "seat": player.seat if player else 0,
                "is_host": player.is_host if player else False,
            })

            # Broadcast updated state to everyone
            await _broadcast_full_state(room_id, game)

        elif msg.type == "rejoin":
            # Reconnecting with existing player_id
            player_id = msg.player_id
            if not player_id:
                await ws.send_json({"type": "error", "error": "Player ID required for rejoin."})
                await ws.close()
                return

            error, game = await room_manager.join_room(room_id, player_id, msg.name or "Player")
            if error:
                await ws.send_json({"type": "error", "error": error})
                await ws.close()
                return

            await ws_manager.add(room_id, player_id, ws)
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

        # Main message loop
        while True:
            raw = await ws.receive_text()
            try:
                msg = ClientMessage.model_validate_json(raw)
            except Exception as e:
                await ws.send_json({"type": "error", "error": f"Invalid message: {e}"})
                continue

            if msg.type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            await handle_message(ws, room_id, player_id, msg)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: player={player_id}, room={room_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        if player_id:
            ws_manager.remove(player_id)
            rid, game, deleted = await room_manager.disconnect_player(player_id)
            if game and not deleted:
                await _broadcast_full_state(rid, game)


async def handle_message(
    ws: WebSocket, room_id: str, player_id: str,
    msg: ClientMessage,
):
    """Process a game action message from a client."""
    # Acquire per-room lock to prevent concurrent state mutations
    lock = await room_manager.get_lock(room_id)
    async with lock:
        await _handle_message_inner(ws, room_id, player_id, msg)


async def _handle_message_inner(
    ws: WebSocket, room_id: str, player_id: str,
    msg: ClientMessage,
):
    """Inner message handler, called under the room lock."""
    from handlers.playing import handle_play_card
    from handlers.bidding import (
        handle_bid, handle_pass, handle_select_trump,
        handle_challenge_accept, handle_challenge_bid,
        handle_challenge_pass, handle_select_bherus
    )
    from handlers.room import (
        handle_configure, handle_start_game, handle_restart,
        handle_remove_player, handle_update_ping
    )

    game = await room_manager.get_room(room_id)
    if not game:
        await ws.send_json({"type": "error", "error": "Room not found."})
        return

    player = next((p for p in game.players if p.id == player_id), None)
    if not player:
        await ws.send_json({"type": "error", "error": "You are not in this room."})
        return

    seat = player.seat

    if msg.type == "configure":
        await handle_configure(ws, room_id, player_id, msg, game, _broadcast_full_state)
    elif msg.type == "start_game":
        await handle_start_game(ws, room_id, player_id, msg, game, _broadcast_full_state)
    elif msg.type == "bid":
        await handle_bid(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "pass":
        await handle_pass(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "select_trump":
        await handle_select_trump(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "challenge_accept":
        await handle_challenge_accept(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "challenge_bid":
        await handle_challenge_bid(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "challenge_pass":
        await handle_challenge_pass(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "select_bherus":
        await handle_select_bherus(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "play_card":
        await handle_play_card(ws, room_id, seat, msg, game, _broadcast_full_state)
    elif msg.type == "restart":
        await handle_restart(ws, room_id, player_id, msg, game, _broadcast_full_state)
    elif msg.type == "remove_player":
        await handle_remove_player(ws, room_id, player_id, msg, game, _broadcast_full_state)
    elif msg.type == "update_ping":
        await handle_update_ping(ws, room_id, player_id, msg, game)
    elif msg.type == "leave":
        rid, updated_game, deleted = await room_manager.leave_room(player_id, intentional=True)
        if updated_game and not deleted:
            await _broadcast_full_state(room_id, updated_game)
    else:
        await ws.send_json({"type": "error", "error": f"Unknown message type: {msg.type}"})

async def _broadcast_full_state(room_id: str, game) -> None:
    """Send personalized game state to all players in the room."""
    sanitized = sanitize_game_state(game)
    hands = {s: cards for s, cards in game.hands.items()} if game.hands else {}
    await ws_manager.send_game_state_to_all(room_id, sanitized, hands)


# ──────────────────────────── Static Files (React SPA) ────────────────────────────

static_dir = os.path.join(os.path.dirname(__file__), "static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all route to serve the React SPA and its static assets."""
    # First, try to serve an actual file in the static directory (e.g. assets, favicon)
    potential_path = os.path.join(static_dir, full_path)
    if full_path and os.path.isfile(potential_path):
        return FileResponse(potential_path)
    
    # Otherwise, return index.html for React Router to handle
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
        
    return {"error": "Frontend not built. Run 'npm run build' in the frontend directory."}


# ──────────────────────────── Run ────────────────────────────

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
