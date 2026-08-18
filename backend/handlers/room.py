import logging
from fastapi import WebSocket
from models import ClientMessage, GameState
from room_manager import room_manager
from ws_manager import ws_manager

logger = logging.getLogger("kadi_teeri.handlers.room")

async def handle_configure(ws: WebSocket, room_id: str, player_id: str, msg: ClientMessage, game: GameState, broadcast_fn):
    error = await room_manager.configure_room(
        room_id, player_id,
        player_count=msg.player_count,
        deck_count=msg.deck_count,
    )
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    updated = await room_manager.get_room(room_id)
    if updated:
        await broadcast_fn(room_id, updated)

async def handle_start_game(ws: WebSocket, room_id: str, player_id: str, msg: ClientMessage, game: GameState, broadcast_fn):
    error = await room_manager.start_game(room_id, player_id)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    updated = await room_manager.get_room(room_id)
    if updated:
        await broadcast_fn(room_id, updated)

async def handle_restart(ws: WebSocket, room_id: str, player_id: str, msg: ClientMessage, game: GameState, broadcast_fn):
    error = await room_manager.restart_game(room_id, player_id)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    updated = await room_manager.get_room(room_id)
    if updated:
        await broadcast_fn(room_id, updated)

async def handle_remove_player(ws: WebSocket, room_id: str, player_id: str, msg: ClientMessage, game: GameState, broadcast_fn):
    target_id = msg.target_player_id
    if not target_id:
        await ws.send_json({"type": "error", "error": "Target player ID required."})
        return
    error = await room_manager.remove_player(room_id, player_id, target_id)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    updated = await room_manager.get_room(room_id)
    if updated:
        await broadcast_fn(room_id, updated)

async def handle_update_ping(ws: WebSocket, room_id: str, player_id: str, msg: ClientMessage, game: GameState):
    player = next((p for p in game.players if p.id == player_id), None)
    if player and msg.ping_ms is not None:
        player.ping_ms = msg.ping_ms
        await ws_manager.broadcast(room_id, {
            "type": "ping_update",
            "player_id": player_id,
            "ping_ms": player.ping_ms
        })
