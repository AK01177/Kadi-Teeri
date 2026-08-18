"""
Trick play, legal play validation, trick winner evaluation, and trick resolution.
"""

from __future__ import annotations

from collections.abc import Callable

from app.game.bheru import _check_bheru_reveal
from app.models.game import (
    SUIT_NAMES,
    Card,
    GameState,
    GameStatus,
    TrickPlay,
    TrickState,
    rank_index,
)


def _start_playing(game: GameState) -> None:
    """Transition game state to PLAYING phase."""
    game.status = GameStatus.PLAYING
    game.trick_number = 1

    # Dealer leads the very first trick of the round
    leader = game.dealer
    game.turn_seat = leader
    game.trick = TrickState(leader_seat=leader, lead_suit=None, cards_played=[])
    game.captured = {i: [] for i in range(len(game.players))}
    game.log.append(f"Round started! {game.players[leader].name} leads the first trick.")


def legal_plays(
    game: GameState | list[Card],
    seat: int | str | None = None,
    lead_suit: str | None = None,
) -> list[Card]:
    """Return list of legal cards a player can play from their hand."""
    if isinstance(game, list):
        hand = game
        lead = seat if isinstance(seat, str) else lead_suit
        if not lead:
            return list(hand)
        following = [c for c in hand if c.suit == lead]
        return following if following else list(hand)

    if game.status != GameStatus.PLAYING or seat is None or not isinstance(seat, int) or game.turn_seat != seat:
        return []
    hand = game.hands.get(seat, [])
    if not hand:
        return []
    if not game.trick or game.trick.lead_suit is None:
        return list(hand)

    lead = game.trick.lead_suit
    following = [c for c in hand if c.suit == lead]
    return following if following else list(hand)


def validate_play(game: GameState, seat: int, card: Card) -> str | None:
    """Validate a card play move."""
    if game.status != GameStatus.PLAYING:
        return "Not in playing phase."
    if game.turn_seat != seat:
        return "Not your turn."

    hand = game.hands.get(seat, [])
    if not any(c == card for c in hand):
        return f"You do not have {card.label()} in your hand."

    legals = legal_plays(game, seat)
    if not any(c == card for c in legals):
        lead_name = (
            SUIT_NAMES.get(game.trick.lead_suit, game.trick.lead_suit) if game.trick and game.trick.lead_suit else ""
        )
        return f"Must follow lead suit ({lead_name}) if you have it."

    return None


def play_card(
    game: GameState,
    seat: int,
    card: Card,
    auto_resolve: bool = True,
    finish_round_fn: Callable[[GameState], None] | None = None,
) -> bool:
    """Play a card into the current trick. Returns True if trick is complete (all players played)."""
    hand = game.hands.get(seat, [])
    matching = next((c for c in hand if c == card), None)
    if matching:
        hand.remove(matching)

    t = game.trick
    if not t:
        return False

    if t.lead_suit is None:
        t.lead_suit = card.suit

    t.cards_played.append(TrickPlay(seat=seat, card=card))
    _check_bheru_reveal(game, seat, card)

    n = len(game.players)
    if len(t.cards_played) == n:
        if auto_resolve:
            resolve_trick(game, finish_round_fn=finish_round_fn)
        return True
    else:
        game.turn_seat = (seat + 1) % n
        return False


def _determine_trick_winner(
    cards_played: list[TrickPlay],
    lead_suit: str | None = None,
    trump_suit: str | None = None,
    trump: str | None = None,
) -> TrickPlay:
    """Determine the winning TrickPlay entry from played cards.

    Rule for 2-deck duplicates:
    If two identical highest cards are played (e.g., two A♠), the card played
    LATER IN TIME (higher index in cards_played) wins the trick.
    """
    trump_suit = trump if trump is not None else trump_suit

    trumps = [tp for tp in cards_played if tp.card.suit == trump_suit]
    if trumps:
        best = trumps[0]
        for entry in trumps[1:]:
            if rank_index(entry.card.rank) >= rank_index(best.card.rank):
                best = entry
        return best

    leads = [tp for tp in cards_played if tp.card.suit == lead_suit]
    best = leads[0]
    for entry in leads[1:]:
        if rank_index(entry.card.rank) >= rank_index(best.card.rank):
            best = entry
    return best


def _highest_card_last_wins(cards_played: list[TrickPlay], lead_suit: str | None, trump_suit: str | None) -> TrickPlay:
    """Explicit helper for the duplicate card rule (later played card wins tie)."""
    return _determine_trick_winner(cards_played, lead_suit, trump_suit)


def resolve_trick(
    game: GameState,
    finish_round_fn: Callable[[GameState], None] | None = None,
) -> None:
    """Evaluate trick winner, award captured cards, advance to next trick or end round."""
    t = game.trick
    if not t or not t.cards_played:
        return

    winner_entry = _determine_trick_winner(t.cards_played, t.lead_suit, game.trump_suit)
    winner_seat = winner_entry.seat
    winner_name = game.players[winner_seat].name

    points = sum(tp.card.points() for tp in t.cards_played)
    card_objs = [tp.card for tp in t.cards_played]

    if winner_seat not in game.captured:
        game.captured[winner_seat] = []
    game.captured[winner_seat].extend(card_objs)

    pts_str = f" ({points} pts)" if points > 0 else ""
    game.log.append(f"🏆 {winner_name} won trick {game.trick_number}{pts_str}.")

    # Reset trick for next round
    game.turn_seat = winner_seat
    game.trick = TrickState(leader_seat=winner_seat, lead_suit=None, cards_played=[])
    game.trick_number += 1

    # Check if hands are empty -> Round is complete
    remaining = sum(len(h) for h in game.hands.values())
    if remaining == 0:
        if finish_round_fn is not None:
            finish_round_fn(game)
        else:
            from app.game.scoring import finish_round

            finish_round(game)
