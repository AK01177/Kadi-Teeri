"""
Bot logic for auto-playing cards when a player is disconnected.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from app.game.trick import _determine_trick_winner, legal_plays, play_card, resolve_trick
from app.models.game import Card, GameState, GameStatus, rank_index

logger = logging.getLogger("kadi_teeri.game.bot")


def _pick_best_bot_card(game: GameState, turn_seat: int) -> Card | None:
    """Select the lowest priority valid card for the disconnected player."""
    legals = legal_plays(game, turn_seat)
    if not legals:
        return None

    trump = game.trump_suit

    # Separate non-trumps and trumps
    non_trumps = [c for c in legals if c.suit != trump]
    trumps = [c for c in legals if c.suit == trump]

    # Rule: Pick the lowest rank valid card.
    # Prefer lowest non-trump. If no non-trump available, pick lowest trump.
    if non_trumps:
        return min(non_trumps, key=lambda c: rank_index(c.rank))
    elif trumps:
        return min(trumps, key=lambda c: rank_index(c.rank))
    else:
        # Fallback (shouldn't happen with correct legal_plays logic)
        return legals[0]


async def process_bot_turns(
    game: GameState,
    room_id: str,
    broadcast_state_fn: Callable[[str, GameState], Awaitable[None]],
    broadcast_msg_fn: Callable[[str, dict], Awaitable[None]],
) -> None:
    """
    Continually check if the current turn belongs to a disconnected player,
    and automatically play their turn until it's a human's turn or the game is over.
    """
    # Import locally to avoid circular dependencies
    from app.services.room_service import room_service

    while game.status == GameStatus.PLAYING:
        turn_seat = game.turn_seat
        if turn_seat is None:
            break

        player = game.players[turn_seat]
        if player.is_connected:
            break

        logger.info(f"Bot taking turn for disconnected player {player.name} in room {room_id}")

        # Simulate "thinking" and give clients time to animate the previous card
        await asyncio.sleep(1.5)

        card_to_play = _pick_best_bot_card(game, turn_seat)
        if not card_to_play:
            logger.warning(f"Bot could not find a legal card for {player.name}")
            break

        logger.info(f"Bot plays {card_to_play.label()} for {player.name}")

        trick_completed = play_card(game, turn_seat, card_to_play, auto_resolve=False)
        room_service.save_room(room_id)

        # Broadcast the play event
        await broadcast_state_fn(room_id, game)

        if trick_completed and game.trick:
            await asyncio.sleep(2.0)
            
            cards_played = game.trick.cards_played
            lead_suit = game.trick.lead_suit
            winner_entry = _determine_trick_winner(cards_played, lead_suit, game.trump_suit)
            winner_seat = winner_entry.seat
            winner_name = game.players[winner_seat].name
            points = sum(tp.card.points() for tp in cards_played)
            
            await broadcast_msg_fn(
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
            await broadcast_state_fn(room_id, game)
