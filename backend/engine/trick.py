"""
Trick play, legal play validation, trick winner evaluation, and trick resolution.
"""

from __future__ import annotations

from typing import Optional

from engine.bheru import _check_bheru_reveal
from models import (
    SUIT_NAMES,
    Card,
    GameState,
    GameStatus,
    TrickPlay,
    TrickState,
    rank_index,
)


def _start_playing(game: GameState, bidder_seat: int) -> None:
    """Initialize the playing phase."""
    n = len(game.players)
    game.status = GameStatus.PLAYING
    game.trick = TrickState(leader_seat=bidder_seat, lead_suit=None, cards_played=[])
    game.trick_number = 1
    game.turn_seat = bidder_seat
    game.captured = {i: [] for i in range(n)}


def legal_plays(hand: list[Card], lead_suit: Optional[str]) -> list[Card]:
    """Get legal cards to play from a hand."""
    if not lead_suit:
        return list(hand)
    following = [c for c in hand if c.suit == lead_suit]
    return following if following else list(hand)


def validate_play(game: GameState, seat: int, card: Card) -> Optional[str]:
    """Validate a card play."""
    if game.status != GameStatus.PLAYING:
        return "Not in playing phase."
    if game.turn_seat != seat:
        return "Not your turn."
    if game.trick is None:
        return "No trick in progress."

    hand = game.hands.get(seat, [])
    if not any(c.rank == card.rank and c.suit == card.suit and c.deck_index == card.deck_index for c in hand):
        return "You don't have that card."

    legal = legal_plays(hand, game.trick.lead_suit)
    if not any(c.rank == card.rank and c.suit == card.suit and c.deck_index == card.deck_index for c in legal):
        return f"You must follow {SUIT_NAMES.get(game.trick.lead_suit, 'the led suit')} if you can."

    return None


def play_card(game: GameState, seat: int, card: Card, auto_resolve: bool = True, finish_round_fn = None) -> bool:
    """Play a card in the current trick. Returns True if the trick is complete."""
    n = len(game.players)
    hand = game.hands[seat]

    for i, c in enumerate(hand):
        if c.rank == card.rank and c.suit == card.suit and c.deck_index == card.deck_index:
            hand.pop(i)
            break

    game.trick.cards_played.append(TrickPlay(seat=seat, card=card))
    if len(game.trick.cards_played) == 1:
        game.trick.lead_suit = card.suit

    _check_bheru_reveal(game, seat, card)
    game.log.append(f"{game.players[seat].name} plays {card.label()}.")

    if len(game.trick.cards_played) == n:
        if auto_resolve and finish_round_fn:
            resolve_trick(game, finish_round_fn)
        return True
    else:
        game.turn_seat = (seat + 1) % n
        return False


def resolve_trick(game: GameState, finish_round_fn = None) -> None:
    """Determine who wins the trick and start next trick or finish round."""
    trick = game.trick
    trump = game.trump_suit
    n = len(game.players)

    cards_played = trick.cards_played
    lead_suit = trick.lead_suit

    winner_entry = _determine_trick_winner(cards_played, lead_suit, trump)
    winner_seat = winner_entry.seat

    for tp in cards_played:
        game.captured[winner_seat].append(tp.card)

    game.log.append(f"{game.players[winner_seat].name} takes the trick.")

    all_played = all(len(game.hands.get(s, [])) == 0 for s in range(n))

    if all_played:
        if finish_round_fn:
            finish_round_fn(game)
    else:
        game.trick_number += 1
        game.trick = TrickState(leader_seat=winner_seat, lead_suit=None, cards_played=[])
        game.turn_seat = winner_seat


def _determine_trick_winner(
    cards_played: list[TrickPlay], lead_suit: str, trump: str
) -> TrickPlay:
    """
    Determine which card wins the trick.

    Rules:
    1. If any trump cards were played, highest trump wins.
    2. Otherwise, highest card of the lead suit wins.
    3. DUPLICATE RULE (2-deck): If two identical highest cards exist,
       the one played LATER (higher index) wins.
    """
    trumped = [tp for tp in cards_played if tp.card.suit == trump]

    if trumped:
        return _highest_card_last_wins(trumped)
    else:
        followed = [tp for tp in cards_played if tp.card.suit == lead_suit]
        return _highest_card_last_wins(followed)


def _highest_card_last_wins(entries: list[TrickPlay]) -> TrickPlay:
    """
    Find the entry with the highest rank.
    If tied (same rank, same suit — 2-deck duplicate), the LAST one wins.
    """
    best = entries[0]
    for entry in entries[1:]:
        if rank_index(entry.card.rank) >= rank_index(best.card.rank):
            best = entry
    return best
