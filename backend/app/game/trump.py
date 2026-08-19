"""
Trump selection and challenge duel logic.
"""

from __future__ import annotations

import time

from app.game.bidding import max_bid
from app.models.game import SUIT_NAMES, SUITS, GameState, GameStatus


def validate_trump(game: GameState, seat: int, suit: str) -> str | None:
    """Validate trump selection."""
    if game.status != GameStatus.TRUMP:
        return "Not in trump selection phase."
    if game.bidder_seat != seat:
        return "Only the bid winner can choose trump."
    if suit not in SUITS:
        return f"Invalid suit: {suit}."
    return None


def select_trump(game: GameState, seat: int, suit: str) -> None:
    """Apply trump selection and initiate the challenge countdown if not already used."""
    game.trump_suit = suit
    suit_name = SUIT_NAMES.get(suit, suit)
    game.log.append(f"{game.players[seat].name} selected {suit_name} as trump.")

    if game.trump_challenge_used:
        game.status = GameStatus.BHERU
        game.turn_seat = game.bidder_seat
    else:
        game.status = GameStatus.TRUMP_CHALLENGE
        game.trump_challenge_used = True
        game.challenge_deadline = time.time() + 10.0
        game.challenge_duel_seats = None
        game.challenger_seat = None


def validate_challenge_accept(game: GameState, seat: int) -> str | None:
    """Validate a player accepting/initiating a trump challenge."""
    if game.status != GameStatus.TRUMP_CHALLENGE:
        return "Not in trump challenge phase."
    if game.challenge_duel_seats is not None:
        return "Challenge duel already in progress."
    if seat == game.bidder_seat:
        return "The bidder cannot challenge their own trump."
    return None


def accept_challenge(game: GameState, seat: int) -> None:
    """Initiate a 1-vs-1 challenge duel against the bidder."""
    bidder = game.bidder_seat
    if bidder is None:
        return
    if game.bid_target is not None:
        game.bid_target += 20
    game.challenger_seat = seat
    game.bidder_seat = seat
    game.challenge_duel_seats = [bidder, seat]
    game.turn_seat = bidder  # Original bidder responds first
    game.log.append(f"{game.players[seat].name} challenged {game.players[bidder].name}'s trump!")


def expire_trump_challenge(game: GameState) -> None:
    """Called when the 10-second challenge timer expires without anyone challenging."""
    if game.status == GameStatus.TRUMP_CHALLENGE and game.challenge_duel_seats is None:
        game.log.append("No player challenged. Proceeding to Bheru selection.")
        game.status = GameStatus.BHERU
        game.turn_seat = game.bidder_seat


def validate_challenge_bid(game: GameState, seat: int) -> str | None:
    """Validate a raise bid during a challenge duel."""
    if game.status != GameStatus.TRUMP_CHALLENGE or game.challenge_duel_seats is None:
        return "Not in challenge duel."
    if game.turn_seat != seat:
        return "Not your turn in the challenge duel."
    maximum = max_bid(game.config.deck_count)
    if game.bid_target is not None and game.bid_target >= maximum:
        return "Bid is already at maximum possible value."
    return None


def place_challenge_bid(game: GameState, seat: int) -> None:
    """Raise the bid target in a challenge duel and pass turn to opponent."""
    if game.bid_target is None:
        return
    game.bid_target += 20
    game.bidder_seat = seat  # The person who bids higher becomes bidder
    game.log.append(f"{game.players[seat].name} raised bid to {game.bid_target}.")

    duel = game.challenge_duel_seats
    if not duel:
        return
    other_seat = duel[1] if seat == duel[0] else duel[0]
    game.turn_seat = other_seat


def validate_challenge_pass(game: GameState, seat: int) -> str | None:
    """Validate passing in a challenge duel."""
    if game.status != GameStatus.TRUMP_CHALLENGE or game.challenge_duel_seats is None:
        return "Not in challenge duel."
    if game.turn_seat != seat:
        return "Not your turn in the challenge duel."
    return None


def pass_challenge_bid(game: GameState, seat: int) -> None:
    """Pass in duel -> the other player wins duel and becomes final bidder."""
    duel = game.challenge_duel_seats
    if not duel:
        return
    winner_seat = duel[1] if seat == duel[0] else duel[0]
    game.bidder_seat = winner_seat
    game.log.append(
        f"{game.players[seat].name} conceded the challenge. "
        f"{game.players[winner_seat].name} wins bidding at {game.bid_target}!"
    )
    game.challenge_duel_seats = None
    game.status = GameStatus.TRUMP
    game.turn_seat = winner_seat
