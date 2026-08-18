import asyncio
import logging
from fastapi import WebSocket
from models import ClientMessage, GameState, Card
from game_engine import validate_play, play_card, _determine_trick_winner, resolve_trick
from room_manager import room_manager
from ws_manager import ws_manager

logger = logging.getLogger("kadi_teeri.handlers.playing")

async def handle_play_card(
    ws: WebSocket, room_id: str, seat: int, msg: ClientMessage, game: GameState, broadcast_fn
):
    if not msg.rank or not msg.suit:
        await ws.send_json({"type": "error", "error": "Card rank and suit required."})
        return
        
    card = Card(
        rank=msg.rank,
        suit=msg.suit,
        deck_index=msg.deck_index or 0,
    )
    
    error = validate_play(game, seat, card)
    if error:
        await ws.send_json({"type": "error", "error": error})
        return
        
    trick_completed = play_card(game, seat, card, auto_resolve=False)
    await room_manager.save_room(room_id, game)
    
    # Broadcast the full state including the newly played card
    await broadcast_fn(room_id, game)
    
    if trick_completed:
        # Snapshot trick data before background task runs
        trick_cards = list(game.trick.cards_played)
        trick_lead_suit = game.trick.lead_suit
        trick_trump = game.trump_suit

        async def _delayed_trick_resolve():
            """Run the trick reveal + resolution without blocking the WS handler."""
            from main import background_tasks
            try:
                # First 2s delay: cards sit on the table
                await asyncio.sleep(2.0)

                # Evaluate winner
                winner_entry = _determine_trick_winner(trick_cards, trick_lead_suit, trick_trump)
                winner_seat = winner_entry.seat
                
                # We need to fetch the room state without the room lock, since this is a background task
                # and we don't want to deadlock if someone else is mutating.
                g = await room_manager.get_room(room_id)
                if g is None:
                    return
                winner_name = g.players[winner_seat].name
                points = sum(tp.card.points() for tp in trick_cards)

                # Broadcast the popup
                await ws_manager.broadcast(room_id, {
                    "type": "trick_winner",
                    "name": winner_name,
                    "points": points
                })

                # Second 2s delay: popup shows
                await asyncio.sleep(2.0)

                # Acquire lock for state mutation
                lock = await room_manager.get_lock(room_id)
                async with lock:
                    g = await room_manager.get_room(room_id)
                    if g is None:
                        return
                    resolve_trick(g)
                    await room_manager.save_room(room_id, g)
                    await broadcast_fn(room_id, g)
            except Exception as e:
                logger.error(f"Error in delayed trick resolve for room {room_id}: {e}", exc_info=True)

        task = asyncio.create_task(_delayed_trick_resolve())
        from main import background_tasks
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
