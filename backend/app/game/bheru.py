"""
Bheru (partner) call validation, assignment, and reveal logic.
"""

from __future__ import annotations

from collections.abc import Callable

from app.models.game import (
    RANKS,
    SUIT_NAMES,
    SUIT_SYMBOLS,
    SUITS,
    BheruCall,
    BheruCallMode,
    BheruInfo,
    Card,
    GameState,
    GameStatus,
)


def max_bherus(num_players: int) -> int:
    """Maximum number of bherus the bidder can call."""
    return (num_players // 2) - 1


def validate_bheru_calls(game: GameState, seat: int, calls: list[BheruCall]) -> str | None:
    """Validate bheru card calls."""
    if game.status != GameStatus.BHERU:
        return "Not in bheru selection phase."
    if game.bidder_seat != seat:
        return "Only the bidder can call bherus."

    max_allowed = max_bherus(len(game.players))
    if len(calls) == 0:
        return None  # Solo play is valid!
    if len(calls) > max_allowed:
        return f"Cannot call more than {max_allowed} bherus for {len(game.players)} players."

    unique_calls = {(c.rank, c.suit, c.mode) for c in calls}
    if len(unique_calls) != len(calls):
        return "Duplicate bheru calls are not allowed."

    bidder_hand = game.hands.get(seat, [])

    for c in calls:
        if c.rank not in RANKS:
            return f"Invalid rank: {c.rank}."
        if c.suit not in SUITS:
            return f"Invalid suit: {c.suit}."

        # Rule: cannot call the 3 of Spades
        if c.rank == "3" and c.suit == "S":
            return "Cannot call the 3 of Spades as a bheru."

        # 2-deck specific mode validation
        if game.config.deck_count == 2:
            my_copies = sum(1 for card in bidder_hand if card.rank == c.rank and card.suit == c.suit)

            if c.mode == BheruCallMode.FIX:
                if my_copies != 1:
                    return f"FIX mode requires owning exactly 1 copy of {c.rank}{SUIT_SYMBOLS.get(c.suit, c.suit)}."

            elif c.mode == BheruCallMode.BOTH:
                if my_copies != 0:
                    return f"BOTH mode requires owning 0 copies of {c.rank}{SUIT_SYMBOLS.get(c.suit, c.suit)}."

            elif c.mode == BheruCallMode.SECOND:
                pass  # SECOND mode has no ownership prerequisite

    return None


def assign_bherus(
    game: GameState,
    seat: int,
    calls: list[BheruCall],
    start_playing_fn: Callable[[GameState], None] | None = None,
) -> None:
    """Assign bherus based on calls, resolve card holders, and start playing phase."""
    game.bheru_calls = calls
    game.bherus = []

    if len(calls) == 0:
        game.is_solo = True
        game.log.append(f"{game.players[seat].name} decided to play SOLO!")
    else:
        game.is_solo = False
        for c in calls:
            info = BheruInfo(call=c, revealed=False)

            if c.mode == BheruCallMode.SIMPLE:
                holder = _find_card_holder(game, c.rank, c.suit)
                info.holder_seat = holder
                if holder == seat:
                    info.revealed = True  # Self-call is auto-revealed
            elif c.mode == BheruCallMode.FIX:
                holders = _find_all_card_holders(game, c.rank, c.suit)
                other = [h for h in holders if h != seat]
                info.holder_seat = other[0] if other else seat
            elif c.mode == BheruCallMode.BOTH:
                info.holder_seat = None  # Resolved when cards are played
            elif c.mode == BheruCallMode.SECOND:
                info.holder_seat = None  # Resolved when played 2nd time

            game.bherus.append(info)

            mode_str = f" ({c.mode.value})" if game.config.deck_count == 2 else ""
            card_str = f"{c.rank}{SUIT_SYMBOLS.get(c.suit, c.suit)}"
            game.log.append(f"{game.players[seat].name} called {card_str}{mode_str} as bheru.")

    if start_playing_fn is not None:
        start_playing_fn(game)
    else:
        from app.game.trick import _start_playing

        _start_playing(game)


def _find_card_holder(game: GameState, rank: str, suit: str) -> int | None:
    """Find which seat holds a specific card (for 1-deck games or first match)."""
    for seat, hand in game.hands.items():
        for card in hand:
            if card.rank == rank and card.suit == suit:
                return seat
    return None


def _find_all_card_holders(game: GameState, rank: str, suit: str) -> list[int]:
    """Find all seats holding matching cards (returns list of seats)."""
    holders: list[int] = []
    for seat, hand in game.hands.items():
        for card in hand:
            if card.rank == rank and card.suit == suit:
                holders.append(seat)
    return holders


def _check_bheru_reveal(game: GameState, seat: int, card: Card) -> None:
    """Check if playing `card` reveals or assigns a bheru partner."""
    for bheru in game.bherus:
        call = bheru.call
        if call.rank != card.rank or call.suit != card.suit:
            continue

        card_str = f"{card.rank}{SUIT_SYMBOLS.get(card.suit, card.suit)}"
        suit_str = SUIT_NAMES.get(card.suit, card.suit)

        if call.mode == BheruCallMode.SIMPLE or call.mode == BheruCallMode.FIX:
            if not bheru.revealed and bheru.holder_seat == seat:
                bheru.revealed = True
                game.log.append(f"🤝 BHERU REVEALED! {game.players[seat].name} played {card_str} and is a partner!")

        elif call.mode == BheruCallMode.BOTH:
            if not bheru.revealed:
                bheru.holder_seat = seat
                bheru.revealed = True
                game.log.append(f"🤝 BHERU REVEALED! {game.players[seat].name} played {card_str} (BOTH mode partner)!")

        elif call.mode == BheruCallMode.SECOND:
            bheru.play_count += 1
            if bheru.play_count == 2 and not bheru.revealed:
                bheru.holder_seat = seat
                bheru.revealed = True
                game.log.append(
                    f"🤝 BHERU REVEALED! {game.players[seat].name} played the second {card_str} of {suit_str}!"
                )
