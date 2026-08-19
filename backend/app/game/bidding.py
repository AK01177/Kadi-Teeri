"""
Bidding phase logic and validation.
"""

from __future__ import annotations

from app.models.game import (
    BiddingState,
    BidEntry,
    GameState,
    GameStatus,
)


def max_bid(deck_count: int) -> int:
    """Maximum possible bid."""
    return 250 * deck_count


def init_bidding(num_players: int | GameState) -> BiddingState:
    """Initialize a fresh bidding state for a round."""
    if isinstance(num_players, GameState):
        game = num_players
        n = len(game.players)
        b_state = BiddingState(
            highest_bid=0,
            highest_bidder_seat=None,
            passed=[False] * n,
            history=[],
        )
        game.bidding = b_state
        game.status = GameStatus.BIDDING
        game.turn_seat = (game.dealer + 1) % n if n > 0 else 0
        return b_state

    return BiddingState(
        highest_bid=0,
        highest_bidder_seat=None,
        passed=[False] * num_players,
        history=[],
    )


def validate_bid(game: GameState, seat: int, amount: int) -> str | None:
    """Validate a bid action."""
    if game.status != GameStatus.BIDDING:
        return "Not in bidding phase."
    if game.turn_seat != seat:
        return "Not your turn to bid."
    if not game.bidding:
        return "Bidding state uninitialized."

    b = game.bidding
    if b.passed[seat]:
        return "You have already passed."

    min_bid = 150 if b.highest_bid == 0 else b.highest_bid + 5
    maximum = max_bid(game.config.deck_count)

    if amount < min_bid:
        return f"Bid must be at least {min_bid}."
    if amount > maximum:
        return f"Bid cannot exceed {maximum}."
    if amount % 5 != 0:
        return "Bid must be a multiple of 5."

    return None


def place_bid(game: GameState, seat: int, amount: int) -> None:
    """Apply a valid bid."""
    b = game.bidding
    if not b:
        return
    b.highest_bid = amount
    b.highest_bidder_seat = seat
    b.history.append(BidEntry(seat=seat, action="bid", amount=amount))
    game.log.append(f"{game.players[seat].name} bid {amount}.")
    advance_bidding_turn(game)


def pass_bid(game: GameState, seat: int) -> None:
    """Apply a pass in bidding."""
    b = game.bidding
    if not b:
        return
    b.passed[seat] = True
    b.history.append(BidEntry(seat=seat, action="pass"))
    game.log.append(f"{game.players[seat].name} passed.")
    advance_bidding_turn(game)


def advance_bidding_turn(game: GameState) -> None:
    """Advance bidding turn or transition to trump phase if bidding complete."""
    b = game.bidding
    if not b:
        return

    n = len(game.players)
    active = [i for i, p in enumerate(b.passed) if not p]

    # Case 1: All passed without any bids -> redeal (status stays bidding, restart)
    if len(active) == 0:
        game.log.append("All players passed without bidding. Re-dealing round.")
        b.highest_bid = 0
        b.highest_bidder_seat = None
        b.passed = [False] * n
        b.history.clear()
        game.turn_seat = (game.dealer + 1) % n
        return

    # Case 2: Exactly 1 player left active and at least 1 bid was made -> Bidding won!
    if len(active) == 1 and b.highest_bid > 0:
        winner = active[0]
        game.bidder_seat = winner
        game.bid_target = b.highest_bid
        game.turn_seat = winner
        game.status = GameStatus.TRUMP
        game.log.append(f"{game.players[winner].name} won the bidding with {b.highest_bid}!")
        return

    # Case 3: Advance to next active seat
    curr = game.turn_seat if game.turn_seat is not None else game.dealer
    nxt = (curr + 1) % n
    while b.passed[nxt]:
        nxt = (nxt + 1) % n
    game.turn_seat = nxt
