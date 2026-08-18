"""
Bidding phase logic and validation.
"""

from __future__ import annotations

from typing import Optional
from models import (
    GameState, GameStatus, BiddingState, BidEntry,
)


def max_bid(deck_count: int) -> int:
    """Maximum possible bid."""
    return 250 * deck_count


def init_bidding(game: GameState) -> None:
    """Initialize the bidding phase."""
    n = len(game.players)
    first = (game.dealer + 1) % n
    game.status = GameStatus.BIDDING
    game.turn_seat = first
    game.bidding = BiddingState(
        highest_bid=0,
        highest_bidder_seat=None,
        passed=[False] * n,
        history=[],
    )
    game.trump_suit = None
    game.bid_target = None
    game.bidder_seat = None
    game.trump_challenge_used = False
    game.challenge_deadline = None
    game.challenge_duel_seats = None
    game.challenger_seat = None
    game.bheru_calls = []
    game.bherus = []
    game.is_solo = False
    game.trick = None
    game.trick_number = 0
    game.captured = {}
    game.round_result = None
    game.log.append(f"— Round {game.rounds_played + 1} — {game.players[first].name} bids first.")


def validate_bid(game: GameState, seat: int, amount: int) -> Optional[str]:
    """Validate a bid. Returns error message or None if valid."""
    if game.status != GameStatus.BIDDING:
        return "Not in bidding phase."
    if game.turn_seat != seat:
        return "Not your turn to bid."
    if game.bidding is None:
        return "Bidding not initialized."
    b = game.bidding
    if b.passed[seat]:
        return "You already passed."
    min_req = max(150, b.highest_bid + 5)
    max_allowed = max_bid(game.config.deck_count)
    if amount < min_req:
        return f"Bid must be at least {min_req}."
    if amount > max_allowed:
        return f"Bid cannot exceed {max_allowed}."
    if amount % 5 != 0:
        return "Bid must be in increments of 5."
    return None


def place_bid(game: GameState, seat: int, amount: int) -> None:
    """Place a bid."""
    b = game.bidding
    b.highest_bid = amount
    b.highest_bidder_seat = seat
    b.history.append(BidEntry(seat=seat, action="bid", amount=amount))
    game.log.append(f"{game.players[seat].name} bids {amount}.")
    advance_bidding_turn(game)


def pass_bid(game: GameState, seat: int) -> None:
    """Pass on bidding."""
    b = game.bidding
    b.passed[seat] = True
    b.history.append(BidEntry(seat=seat, action="pass"))
    game.log.append(f"{game.players[seat].name} passes.")
    advance_bidding_turn(game)


def advance_bidding_turn(game: GameState) -> None:
    """Advance to the next bidder or end bidding."""
    b = game.bidding
    n = len(game.players)
    active = [s for s in range(n) if not b.passed[s]]

    if len(active) == 1:
        winner = active[0]
        if b.highest_bidder_seat is None:
            # Everyone passed, force minimum bid
            b.highest_bid = 150
            b.highest_bidder_seat = winner
            game.log.append(
                f"{game.players[winner].name} is forced to take the minimum bid of 150 (everyone else passed)."
            )
        else:
            game.log.append(
                f"{game.players[winner].name} wins the bid at {b.highest_bid} and will choose trump."
            )
        game.bidder_seat = winner
        game.bid_target = b.highest_bid
        game.turn_seat = winner
        game.status = GameStatus.TRUMP
        return

    # Find next active player
    next_seat = game.turn_seat
    for _ in range(n):
        next_seat = (next_seat + 1) % n
        if not b.passed[next_seat]:
            game.turn_seat = next_seat
            break
