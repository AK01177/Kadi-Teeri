"""
Trump selection and challenge duel logic.
"""

from __future__ import annotations

import time
from typing import Optional

from engine.bidding import max_bid
from models import SUIT_NAMES, SUITS, GameState, GameStatus


def validate_trump(game: GameState, seat: int, suit: str) -> Optional[str]:
    """Validate trump selection."""
    if game.status != GameStatus.TRUMP:
        return "Not in trump selection phase."
    if game.bidder_seat != seat:
        return "Only the bid winner can choose trump."
    if suit not in SUITS:
        return f"Invalid suit: {suit}"
    return None


def select_trump(game: GameState, seat: int, suit: str) -> None:
    """Set the trump suit. If challenge hasn't been used yet, enter challenge phase."""
    game.trump_suit = suit
    game.log.append(f"{game.players[seat].name} names {SUIT_NAMES[suit]} as trump.")

    if not game.trump_challenge_used:
        game.status = GameStatus.TRUMP_CHALLENGE
        game.trump_challenge_used = True
        game.challenge_deadline = time.time() + 10
        game.challenge_duel_seats = None
        game.challenger_seat = None
        game.log.append("Other players have 10 seconds to challenge the bid!")
    else:
        game.status = GameStatus.BHERU


def validate_challenge_accept(game: GameState, seat: int) -> Optional[str]:
    """Validate that a player can accept the trump challenge."""
    if game.status != GameStatus.TRUMP_CHALLENGE:
        return "Not in trump challenge phase."
    if game.challenge_duel_seats is not None:
        return "Challenge duel already in progress."
    if seat == game.bidder_seat:
        return "You are the current bidder — you cannot challenge yourself."
    return None


def accept_challenge(game: GameState, seat: int) -> None:
    """A player accepts the challenge, starting a mini-bid duel."""
    original_bidder = game.bidder_seat
    new_amount = game.bid_target + 20
    game.bid_target = new_amount
    game.bidder_seat = seat
    game.challenger_seat = seat
    game.challenge_duel_seats = [original_bidder, seat]
    game.challenge_deadline = None
    game.turn_seat = original_bidder
    game.trump_suit = None
    game.log.append(
        f"{game.players[seat].name} challenges the bid at {new_amount}!"
    )


def expire_trump_challenge(game: GameState) -> None:
    """No one challenged within the time limit — proceed to bheru."""
    if game.status != GameStatus.TRUMP_CHALLENGE:
        return
    if game.challenge_duel_seats is not None:
        return
    game.challenge_deadline = None
    game.status = GameStatus.BHERU
    game.log.append("No one challenged. Proceeding to partner selection.")


def validate_challenge_bid(game: GameState, seat: int) -> Optional[str]:
    """Validate a raise in the mini-bid duel."""
    if game.status != GameStatus.TRUMP_CHALLENGE:
        return "Not in trump challenge phase."
    if game.challenge_duel_seats is None:
        return "No challenge duel in progress."
    if seat not in game.challenge_duel_seats:
        return "You are not part of this challenge duel."
    if game.turn_seat != seat:
        return "Not your turn in the duel."
    return None


def place_challenge_bid(game: GameState, seat: int) -> None:
    """Raise in the challenge duel (+20 from current bid)."""
    new_amount = game.bid_target + 20
    max_allowed = max_bid(game.config.deck_count)
    if new_amount > max_allowed:
        pass_challenge_bid(game, seat)
        return
    game.bid_target = new_amount
    game.bidder_seat = seat
    other = [s for s in game.challenge_duel_seats if s != seat][0]
    game.turn_seat = other
    game.log.append(f"{game.players[seat].name} raises to {new_amount}.")


def validate_challenge_pass(game: GameState, seat: int) -> Optional[str]:
    """Validate passing in the mini-bid duel."""
    if game.status != GameStatus.TRUMP_CHALLENGE:
        return "Not in trump challenge phase."
    if game.challenge_duel_seats is None:
        return "No challenge duel in progress."
    if seat not in game.challenge_duel_seats:
        return "You are not part of this challenge duel."
    if game.turn_seat != seat:
        return "Not your turn in the duel."
    return None


def pass_challenge_bid(game: GameState, seat: int) -> None:
    """Pass in the challenge duel — the other player wins."""
    winner = [s for s in game.challenge_duel_seats if s != seat][0]
    game.bidder_seat = winner
    game.turn_seat = winner
    game.challenge_duel_seats = None
    game.challenger_seat = None
    game.challenge_deadline = None
    game.status = GameStatus.TRUMP
    game.log.append(
        f"{game.players[seat].name} concedes. "
        f"{game.players[winner].name} wins the challenge at {game.bid_target} and will choose trump."
    )
