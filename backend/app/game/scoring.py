"""
Scoring, round completion, new round dealing, and state sanitization.
"""

from __future__ import annotations

from app.game.bidding import init_bidding
from app.game.deck import balance_deck, deal_cards, make_deck, shuffle_deck
from app.models.game import GameState, GameStatus, RoundResult


def finish_round(game: GameState) -> None:
    """Calculate scores and determine winner for the round."""
    n = len(game.players)
    bidder = game.bidder_seat
    if bidder is None:
        return

    bidding_seats = [bidder]
    for bheru in game.bherus:
        if bheru.holder_seat is not None and bheru.holder_seat != bidder and bheru.holder_seat not in bidding_seats:
            bidding_seats.append(bheru.holder_seat)

    defending_seats = [i for i in range(n) if i not in bidding_seats]

    per_seat: dict[int, int] = {}
    for i in range(n):
        captured_cards = game.captured.get(i, [])
        per_seat[i] = sum(c.points() for c in captured_cards)

    bidding_points = sum(per_seat[s] for s in bidding_seats)
    defending_points = sum(per_seat[s] for s in defending_seats)

    target = game.bid_target or 150
    bidding_won = bidding_points >= target

    game.round_result = RoundResult(
        bidding_points=bidding_points,
        defending_points=defending_points,
        bidding_won=bidding_won,
        bidding_seats=bidding_seats,
        defending_seats=defending_seats,
        target=target,
        per_seat=per_seat,
    )

    game.rounds_played += 1
    game.status = GameStatus.ROUND_END

    if bidding_won:
        game.log.append(f"🎉 Bidding team WON the round! Scored {bidding_points}/{target} pts.")
        for s in bidding_seats:
            pid = game.players[s].id
            game.wins[pid] = game.wins.get(pid, 0) + 1
    else:
        game.log.append(f"🛡️ Defending team WON the round! Bidding team got {bidding_points}/{target} pts.")
        for s in defending_seats:
            pid = game.players[s].id
            game.wins[pid] = game.wins.get(pid, 0) + 1


def deal_new_round(game: GameState) -> None:
    """Reset round state and deal new hands for the next round."""
    n = len(game.players)
    if n < 4:
        return

    # Rotate dealer clockwise
    if game.rounds_played > 0:
        game.dealer = (game.dealer + 1) % n

    deck = make_deck(game.config.deck_count)
    deck = balance_deck(deck, n, game.config.deck_count)
    deck = shuffle_deck(deck)
    hands = deal_cards(deck, n)

    game.hands = hands
    game.status = GameStatus.BIDDING
    game.bidding = init_bidding(n)
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
    game.captured = {i: [] for i in range(n)}
    game.round_result = None

    first_bidder = (game.dealer + 1) % n
    game.turn_seat = first_bidder
    game.log.append(f"Round {game.rounds_played + 1} dealt. {game.players[first_bidder].name} starts bidding.")


def sanitize_game_state(game: GameState) -> dict:
    """Convert GameState to a dict, hiding other players' secret hands and unrevealed bheru identities."""
    d = game.model_dump()
    d.pop("hands", None)

    hand_sizes: dict[int, int] = {}
    for seat, hand in game.hands.items():
        hand_sizes[seat] = len(hand)
    d["hand_sizes"] = hand_sizes

    captured_counts: dict[int, int] = {}
    captured_points: dict[int, int] = {}
    for seat, cards in game.captured.items():
        captured_counts[seat] = len(cards)
        captured_points[seat] = sum(c.points() for c in cards)
    d["captured_counts"] = captured_counts
    d["captured_points"] = captured_points

    sanitized_bherus = []
    for bheru in game.bherus:
        b_dict = bheru.model_dump()
        if not bheru.revealed:
            b_dict.pop("holder_seat", None)
        sanitized_bherus.append(b_dict)
    d["bherus"] = sanitized_bherus

    return d
