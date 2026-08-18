"""
Kadi Teeri Online — Game Engine Facade

All game logic: deck creation, card balancing, shuffling, dealing,
bidding, trump selection, bheru assignment, trick-taking, scoring.

This file serves as a backward-compatible entry point re-exporting
all functions from the modular engine package (`backend/engine`).
"""

from __future__ import annotations

from engine.bheru import (
    _check_bheru_reveal,
    _find_all_card_holders,
    _find_card_holder,
    max_bherus,
    validate_bheru_calls,
)
from engine.bheru import (
    assign_bherus as _assign_bherus,
)
from engine.bidding import (
    advance_bidding_turn,
    init_bidding,
    max_bid,
    pass_bid,
    place_bid,
    validate_bid,
)
from engine.deck import (
    balance_deck,
    deal_cards,
    make_deck,
    shuffle_deck,
    sort_hand,
)
from engine.scoring import (
    deal_new_round,
    finish_round,
    sanitize_game_state,
)
from engine.trick import (
    _determine_trick_winner,
    _highest_card_last_wins,
    _start_playing,
    legal_plays,
    validate_play,
)
from engine.trick import (
    play_card as _play_card,
)
from engine.trick import (
    resolve_trick as _resolve_trick,
)
from engine.trump import (
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
from models import BheruCall, Card, GameState


def assign_bherus(game: GameState, seat: int, calls: list[BheruCall]) -> None:
    """Wrapper around assign_bherus supplying _start_playing callback."""
    _assign_bherus(game, seat, calls, start_playing_fn=_start_playing)


def play_card(game: GameState, seat: int, card: Card, auto_resolve: bool = True) -> bool:
    """Wrapper around play_card supplying finish_round callback."""
    return _play_card(game, seat, card, auto_resolve=auto_resolve, finish_round_fn=finish_round)


def resolve_trick(game: GameState) -> None:
    """Wrapper around resolve_trick supplying finish_round callback."""
    _resolve_trick(game, finish_round_fn=finish_round)


__all__ = [
    "make_deck", "balance_deck", "shuffle_deck", "deal_cards", "sort_hand",
    "max_bid", "init_bidding", "validate_bid", "place_bid", "pass_bid", "advance_bidding_turn",
    "validate_trump", "select_trump", "validate_challenge_accept", "accept_challenge",
    "expire_trump_challenge", "validate_challenge_bid", "place_challenge_bid",
    "validate_challenge_pass", "pass_challenge_bid",
    "max_bherus", "validate_bheru_calls", "assign_bherus",
    "_find_card_holder", "_find_all_card_holders", "_check_bheru_reveal",
    "legal_plays", "validate_play", "play_card", "resolve_trick",
    "_determine_trick_winner", "_highest_card_last_wins", "_start_playing",
    "finish_round", "deal_new_round", "sanitize_game_state",
]
