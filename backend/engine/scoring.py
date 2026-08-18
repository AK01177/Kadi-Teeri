"""
Scoring, round completion, new round dealing, and state sanitization.
"""

from __future__ import annotations

from engine.bidding import init_bidding
from engine.deck import balance_deck, deal_cards, make_deck, shuffle_deck
from models import GameState, GameStatus, RoundResult


def finish_round(game: GameState) -> None:
    """Calculate scores and determine winner for the round."""
    n = len(game.players)
    bidder = game.bidder_seat

    bidding_seats = [bidder]
    for bheru in game.bherus:
        if bheru.holder_seat is not None and bheru.holder_seat != bidder:
            if bheru.holder_seat not in bidding_seats:
                bidding_seats.append(bheru.holder_seat)

    for bheru in game.bherus:
        if not bheru.revealed and bheru.holder_seat is not None:
            bheru.revealed = True

    defending_seats = [s for s in range(n) if s not in bidding_seats]

    per_seat: dict[int, int] = {}
    for s in range(n):
        pts = sum(c.points() for c in game.captured.get(s, []))
        per_seat[s] = pts

    bidding_points = sum(per_seat.get(s, 0) for s in bidding_seats)
    total_points = 250 * game.config.deck_count
    defending_points = total_points - bidding_points
    bidding_won = bidding_points >= game.bid_target

    winners = bidding_seats if bidding_won else defending_seats
    for s in winners:
        pid = game.players[s].id
        game.wins[pid] = game.wins.get(pid, 0) + 1

    game.round_result = RoundResult(
        bidding_points=bidding_points,
        defending_points=defending_points,
        bidding_won=bidding_won,
        bidding_seats=bidding_seats,
        defending_seats=defending_seats,
        target=game.bid_target,
        per_seat=per_seat,
    )
    game.status = GameStatus.ROUND_END
    game.rounds_played += 1

    if bidding_won:
        game.log.append(
            f"Bidding side reaches {bidding_points}/{game.bid_target} — contract made!"
        )
    else:
        game.log.append(
            f"Bidding side only reaches {bidding_points}/{game.bid_target} — contract failed."
        )


def deal_new_round(game: GameState, is_first: bool = False) -> None:
    """Shuffle, balance, deal, and start bidding for a new round."""
    n = len(game.players)
    if not is_first:
        game.dealer = (game.dealer + 1) % n

    deck = make_deck(game.config.deck_count)
    deck = balance_deck(deck, n, game.config.deck_count)
    deck = shuffle_deck(deck)

    game.hands = deal_cards(deck, n)
    init_bidding(game)


def sanitize_game_state(game: GameState) -> dict:
    """
    Create a sanitized version of the game state that can be sent to clients.
    Removes sensitive information (other players' hands).
    """
    state = {
        "status": game.status.value,
        "config": game.config.model_dump(),
        "players": [p.model_dump() for p in game.players],
        "dealer": game.dealer,
        "turn_seat": game.turn_seat,
        "trump_suit": game.trump_suit,
        "bid_target": game.bid_target,
        "bidder_seat": game.bidder_seat,
        "is_solo": game.is_solo,
        "trick_number": game.trick_number,
        "rounds_played": game.rounds_played,
        "wins": game.wins,
        "log": game.log[-20:],
        "trump_challenge_used": game.trump_challenge_used,
        "challenge_deadline": game.challenge_deadline,
        "challenge_duel_seats": game.challenge_duel_seats,
        "challenger_seat": game.challenger_seat,
    }

    if game.bidding:
        state["bidding"] = game.bidding.model_dump()

    if game.trick:
        state["trick"] = {
            "leader_seat": game.trick.leader_seat,
            "lead_suit": game.trick.lead_suit,
            "cards_played": [
                {"seat": tp.seat, "card": tp.card.model_dump()}
                for tp in game.trick.cards_played
            ],
        }

    bheru_public = []
    for bheru in game.bherus:
        info = {
            "call": bheru.call.model_dump(),
            "revealed": bheru.revealed,
        }
        if bheru.revealed:
            info["holder_seat"] = bheru.holder_seat
        bheru_public.append(info)
    state["bherus"] = bheru_public

    if game.round_result:
        state["round_result"] = game.round_result.model_dump()

    state["hand_sizes"] = {s: len(game.hands.get(s, [])) for s in range(len(game.players))}
    state["captured_counts"] = {s: len(game.captured.get(s, [])) for s in range(len(game.players))}
    state["captured_points"] = {
        s: sum(c.points() for c in game.captured.get(s, []))
        for s in range(len(game.players))
    }

    return state
