"""
Real-time WebSocket connection handler for Kadi Teeri game action processing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.game.bheru import assign_bherus, validate_bheru_calls
from app.game.bidding import pass_bid, place_bid, validate_bid
from app.game.scoring import sanitize_game_state
from app.game.trick import _determine_trick_winner, play_card, resolve_trick, validate_play
from app.game.trump import (
    accept_challenge,
    expire_trump_challenge,
    pass_challenge_bid,
    place_challenge_bid,
    select_trump,
    validate_challenge_accept,
    validate_challenge_bid,
    validate_challenge_pass,
    validate_trump,
)
from app.models.game import Card, ClientMessage, GameState, GameStatus
from app.services.connection_service import ws_manager
from app.services.room_service import room_service

logger = logging.getLogger("kadi_teeri.api.ws")
router = APIRouter(tags=["WebSocket"])

_last_nudge_times: dict[tuple[str, str], float] = {}
NUDGE_COOLDOWN_SECONDS = 5.0


@router.websocket("/ws/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str):
    """Main WebSocket endpoint for a game room."""
    room_id = room_id.upper()
    await ws.accept()

    player_id: str | None = None

    try:
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

            error, game = room_service.join_room(room_id, player_id, name)
            if error or not game:
                await ws.send_json({"type": "error", "error": error or "Failed to join room."})
                await ws.close()
                return

            await ws_manager.add(room_id, player_id, ws)
            player = next((p for p in game.players if p.id == player_id), None)

            await ws.send_json(
                {
                    "type": "welcome",
                    "player_id": player_id,
                    "room_id": room_id,
                    "seat": player.seat if player else 0,
                    "is_host": player.is_host if player else False,
                }
            )
            await _broadcast_full_state(room_id, game)

        elif msg.type == "rejoin":
            raw_data = json.loads(raw)
            player_id = raw_data.get("player_id")
            if not player_id:
                await ws.send_json({"type": "error", "error": "Player ID required for rejoin."})
                await ws.close()
                return

            error, game = room_service.join_room(room_id, player_id, msg.name or "Player")
            if error or not game:
                await ws.send_json({"type": "error", "error": error or "Failed to rejoin room."})
                await ws.close()
                return

            await ws_manager.add(room_id, player_id, ws)
            player = next((p for p in game.players if p.id == player_id), None)

            await ws.send_json(
                {
                    "type": "welcome",
                    "player_id": player_id,
                    "room_id": room_id,
                    "seat": player.seat if player else 0,
                    "is_host": player.is_host if player else False,
                }
            )
            await _broadcast_full_state(room_id, game)

        else:
            await ws.send_json({"type": "error", "error": "First message must be 'join' or 'rejoin'."})
            await ws.close()
            return

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
            rid, game, deleted = room_service.disconnect_player(player_id)
            if game and not deleted and rid:
                await _broadcast_full_state(rid, game)


async def handle_message(
    ws: WebSocket,
    room_id: str,
    player_id: str,
    msg: ClientMessage,
    raw_data: dict,
):
    """Process incoming WebSocket client action."""
    game = room_service.get_room(room_id)
    if not game:
        await ws.send_json({"type": "error", "error": "Room not found."})
        return

    player = next((p for p in game.players if p.id == player_id), None)
    if not player:
        await ws.send_json({"type": "error", "error": "You are not in this room."})
        return

    seat = player.seat

    if msg.type == "configure":
        error = room_service.configure_room(
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
        error = room_service.start_game(room_id, player_id)
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
        room_service.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "pass":
        if game.status != GameStatus.BIDDING or game.turn_seat != seat:
            await ws.send_json({"type": "error", "error": "Cannot pass right now."})
            return
        pass_bid(game, seat)
        room_service.save_room(room_id)
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
        room_service.save_room(room_id)
        await _broadcast_full_state(room_id, game)

        if game.status == GameStatus.TRUMP_CHALLENGE:

            async def _auto_expire_challenge():
                await asyncio.sleep(10)
                g = room_service.get_room(room_id)
                if g and g.status == GameStatus.TRUMP_CHALLENGE and g.challenge_duel_seats is None:
                    expire_trump_challenge(g)
                    room_service.save_room(room_id)
                    await _broadcast_full_state(room_id, g)

            asyncio.create_task(_auto_expire_challenge())

    elif msg.type == "challenge_accept":
        error = validate_challenge_accept(game, seat)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        accept_challenge(game, seat)
        room_service.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "challenge_bid":
        error = validate_challenge_bid(game, seat)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        place_challenge_bid(game, seat)
        room_service.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "challenge_pass":
        error = validate_challenge_pass(game, seat)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        pass_challenge_bid(game, seat)
        room_service.save_room(room_id)
        await _broadcast_full_state(room_id, game)

    elif msg.type == "select_bherus":
        calls = msg.calls or []
        error = validate_bheru_calls(game, seat, calls)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        assign_bherus(game, seat, calls)
        room_service.save_room(room_id)
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
        room_service.save_room(room_id)
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

            await ws_manager.broadcast(
                room_id,
                {
                    "type": "trick_winner",
                    "name": winner_name,
                    "points": points,
                },
            )
            await asyncio.sleep(2.0)
            resolve_trick(game)
            room_service.save_room(room_id)
            await _broadcast_full_state(room_id, game)

    elif msg.type == "restart":
        error = room_service.restart_game(room_id, player_id)
        if error:
            await ws.send_json({"type": "error", "error": error})
            return
        await _broadcast_full_state(room_id, game)

    elif msg.type == "update_ping":
        if msg.ping_ms is not None:
            player.ping_ms = msg.ping_ms
            await ws_manager.broadcast(
                room_id,
                {
                    "type": "ping_update",
                    "player_id": player_id,
                    "ping_ms": player.ping_ms,
                },
            )

    elif msg.type == "remove_player":
        target_id = raw_data.get("target_player_id")
        if not target_id:
            await ws.send_json({"type": "error", "error": "Target player ID required."})
            return
        error = room_service.remove_player(room_id, player_id, target_id)
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

    elif msg.type == "fetch_state":
        sanitized = sanitize_game_state(game)
        hands = dict(game.hands) if game.hands else {}
        player_hand = hands.get(seat, [])
        hand_data = [c.model_dump() if hasattr(c, "model_dump") else c for c in player_hand]
        await ws.send_json(
            {
                "type": "game_state",
                "game": sanitized,
                "hand": hand_data,
            }
        )

    elif msg.type == "nudge_player":
        target_id = msg.target_player_id or raw_data.get("target_player_id")
        if not target_id:
            await ws.send_json({"type": "error", "error": "Target player ID required."})
            return

        if target_id == player_id:
            await ws.send_json({"type": "error", "error": "You cannot nudge yourself."})
            return

        if game.status in (GameStatus.LOBBY, GameStatus.ROUND_END):
            await ws.send_json({"type": "error", "error": "Nudge is not available right now."})
            return

        if game.turn_seat is None:
            await ws.send_json({"type": "error", "error": "No active turn."})
            return

        target_player = next((p for p in game.players if p.id == target_id), None)
        if not target_player:
            await ws.send_json({"type": "error", "error": "Target player not in this room."})
            return

        if not target_player.is_connected:
            await ws.send_json({"type": "error", "error": "Target player is disconnected."})
            return

        if target_player.seat != game.turn_seat:
            await ws.send_json({"type": "error", "error": "It is not that player's turn."})
            return

        now = time.time()
        last_nudge = _last_nudge_times.get((room_id, player_id), 0.0)
        if now - last_nudge < NUDGE_COOLDOWN_SECONDS:
            remaining = int(NUDGE_COOLDOWN_SECONDS - (now - last_nudge)) + 1
            await ws.send_json({"type": "error", "error": f"Please wait {remaining}s before nudging again."})
            return

        _last_nudge_times[(room_id, player_id)] = now

        sender_player = next((p for p in game.players if p.id == player_id), None)
        sender_name = sender_player.name if sender_player else "A player"

        await ws_manager.send_personal(
            target_id,
            {
                "type": "nudge_received",
                "sender_id": player_id,
                "sender_name": sender_name,
            },
        )

    else:
        await ws.send_json({"type": "error", "error": f"Unknown message type: {msg.type}"})


async def _broadcast_full_state(room_id: str, game: GameState) -> None:
    """Sanitize and broadcast state updates privately to each connected room member."""
    sanitized = sanitize_game_state(game)
    hands = dict(game.hands) if game.hands else {}
    await ws_manager.send_game_state_to_all(room_id, sanitized, hands)
