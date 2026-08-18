import logging
from fastapi import WebSocket
from models import ClientMessage, GameState, GameStatus
from game_engine import (
    validate_bid, place_bid, pass_bid,
    validate_trump, select_trump,
    validate_challenge_accept, accept_challenge,
    validate_challenge_bid, place_challenge_bid,
    validate_challenge_pass, pass_challenge_bid, expire_trump_challenge,
    validate_bheru_calls, assign_bherus
)
from room_manager import room_manager
from ws_manager import ws_manager

logger = logging.getLogger("kadi_teeri.handlers.bidding")

async def handle_bid(ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn):
    if msg.amount is None:
        await ws.send_json({"type": "error", "error": "Bid amount required."})
        return
    error = validate_bid(game, seat, msg.amount)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    place_bid(game, seat, msg.amount)
    await room_manager.save_room(room_id, game)
    await broadcast_fn(room_id, game)

async def handle_pass(ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn):
    if game.status != GameStatus.BIDDING or game.turn_seat != seat:
        await ws.send_json({"type": "error", "error": "Cannot pass right now."})
        return
    pass_bid(game, seat)
    await room_manager.save_room(room_id, game)
    await broadcast_fn(room_id, game)

async def handle_select_trump(ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn):
    if not msg.suit:
        await ws.send_json({"type": "error", "error": "Suit required."})
        return
    error = validate_trump(game, seat, msg.suit)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    select_trump(game, seat, msg.suit)
    await room_manager.save_room(room_id, game)
    await broadcast_fn(room_id, game)

    # If we entered challenge phase, start auto-expire timer
    if game.status == GameStatus.TRUMP_CHALLENGE:
        import asyncio
        async def _auto_expire_challenge():
            from main import background_tasks
            await asyncio.sleep(10)
            
            # Acquire lock to mutate state
            lock = await room_manager.get_lock(room_id)
            async with lock:
                g = await room_manager.get_room(room_id)
                if g is None:
                    return
                if g.status == GameStatus.TRUMP_CHALLENGE and g.challenge_duel_seats is None:
                    expire_trump_challenge(g)
                    await room_manager.save_room(room_id, g)
                    await broadcast_fn(room_id, g)
                    
        task = asyncio.create_task(_auto_expire_challenge())
        from main import background_tasks
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

async def handle_challenge_accept(ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn):
    error = validate_challenge_accept(game, seat)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    accept_challenge(game, seat)
    await room_manager.save_room(room_id, game)
    await broadcast_fn(room_id, game)

async def handle_challenge_bid(ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn):
    error = validate_challenge_bid(game, seat)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    place_challenge_bid(game, seat)
    await room_manager.save_room(room_id, game)
    await broadcast_fn(room_id, game)

async def handle_challenge_pass(ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn):
    error = validate_challenge_pass(game, seat)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    pass_challenge_bid(game, seat)
    await room_manager.save_room(room_id, game)
    await broadcast_fn(room_id, game)

async def handle_select_bherus(ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn):
    calls = msg.calls or []
    error = validate_bheru_calls(game, seat, calls)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
    assign_bherus(game, seat, calls)
    await room_manager.save_room(room_id, game)
    await broadcast_fn(room_id, game)
