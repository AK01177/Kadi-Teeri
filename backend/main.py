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
    validate_bheru_calls, assign_bherus,
    validate_play, play_card,
    deal_new_round, sanitize_game_state,
)
from room_manager import room_manager
from ws_manager import manager as ws_manager

# ──────────────────────────── Logging ────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("kadi_teeri")


# ──────────────────────────── App ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Kadi Teeri server starting...")
    yield
    logger.info("Kadi Teeri server shutting down.")


app = FastAPI(
    title="Kadi Teeri Online",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
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

    room_id, game = room_manager.create_room(player_id, name)
    return CreateRoomResponse(room_id=room_id, player_id=player_id)


@app.get("/api/rooms/{room_id}", response_model=RoomInfoResponse)
async def get_room_info(room_id: str):
    """Get basic room info (for the join page)."""
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
            # The client sends player_id in a custom field
            raw_data = json.loads(raw)
            provided_player_id = raw_data.get("player_id")

            if provided_player_id:
                player_id = provided_player_id
            else:
                player_id = str(uuid.uuid4())

            error, game = room_manager.join_room(room_id, player_id, name)
            if error:
                await ws.send_json({"type": "error", "error": error})
                await ws.close()
                return

            # Register WebSocket connection
            ws_manager.add(room_id, player_id, ws)

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

        # Main message loop
        while True:
            raw = await ws.receive_text()
            try:
                msg = ClientMessage.model_validate_json(raw)
                # Also parse raw for extra fields
                raw_data = json.loads(raw)
            except Exception as e:
                await ws.send_json({"type": "error", "error": f"Invalid message: {e}"})
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
    ws: WebSocket, room_id: str, player_id: str,
    msg: ClientMessage, raw_data: dict
):
    """Process a game action message from a client."""
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
            room_id, player_id,
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
        play_card(game, seat, card)
        room_manager.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "restart":
        error = room_manager.restart_game(room_id, player_id)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        await _broadcast_full_state(room_id, game)

    elif msg.type == "remove_player":
        target_id = raw_data.get("target_player_id")
        if not target_id:
            await ws.send_json({"type": "error", "error": "Target player ID required."})
            return
        error = room_manager.remove_player(room_id, player_id, target_id)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        await _broadcast_full_state(room_id, game)

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
