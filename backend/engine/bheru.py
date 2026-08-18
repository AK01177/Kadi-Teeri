"""
Bheru (partner) call validation, assignment, and reveal logic.
"""

from __future__ import annotations

from typing import Optional

from models import (
    RANKS,
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


def validate_bheru_calls(
    game: GameState, seat: int, calls: list[BheruCall]
) -> Optional[str]:
    """Validate bheru card calls."""
    if game.status != GameStatus.BHERU:
        return "Not in bheru selection phase."
    if game.bidder_seat != seat:
        return "Only the bid winner can call bherus."

    n = len(game.players)
    max_b = max_bherus(n)
    total_requested = sum(2 if c.mode == BheruCallMode.BOTH else 1 for c in calls)

    if total_requested != max_b and total_requested != 0:
        return f"You must call exactly {max_b} bheru(s), or go Solo."

    deck_count = game.config.deck_count
    seen = set()

    for call in calls:
        if (call.rank, call.suit) in seen:
            return f"Duplicate bheru call: {call.rank}{SUIT_SYMBOLS.get(call.suit, call.suit)}"
        seen.add((call.rank, call.suit))

        if call.rank not in RANKS:
            return f"Invalid rank: {call.rank}"
        if call.suit not in SUITS:
            return f"Invalid suit: {call.suit}"

        if deck_count == 1 and call.mode != BheruCallMode.SIMPLE:
            return "Only 'simple' mode is allowed for 1-deck games."
        if deck_count == 2 and call.mode == BheruCallMode.SIMPLE:
            return "Use 'fix', 'both', or 'second' mode for 2-deck games."

        if call.mode == BheruCallMode.FIX:
            bidder_hand = game.hands.get(seat, [])
            has_copy = any(c.rank == call.rank and c.suit == call.suit for c in bidder_hand)
            if not has_copy:
                return f"FIX mode requires you to hold one copy of {call.rank}{SUIT_SYMBOLS[call.suit]}."

    return None


def assign_bherus(game: GameState, seat: int, calls: list[BheruCall], start_playing_fn) -> None:
    """Assign bherus based on the calls."""
    game.bheru_calls = calls
    game.bherus = []

    if not calls:
        game.is_solo = True
        game.log.append(f"{game.players[seat].name} chooses to play SOLO against the table!")
    else:
        game.is_solo = False
        for call in calls:
            bheru_info = BheruInfo(call=call, revealed=False)

            if call.mode == BheruCallMode.SIMPLE:
                holder = _find_card_holder(game, call.rank, call.suit, exclude_seat=None)
                if holder == seat:
                    game.log.append(
                        f"{game.players[seat].name} calls {call.rank}{SUIT_SYMBOLS[call.suit]} "
                        f"— they hold it themselves!"
                    )
                    bheru_info.holder_seat = seat
                    bheru_info.revealed = True
                else:
                    bheru_info.holder_seat = holder
                    game.log.append(
                        f"{game.players[seat].name} calls for {call.rank}{SUIT_SYMBOLS[call.suit]} "
                        f"— a secret partner has been chosen..."
                    )

            elif call.mode == BheruCallMode.FIX:
                holder = _find_card_holder(game, call.rank, call.suit, exclude_seat=seat)
                bheru_info.holder_seat = holder
                game.log.append(
                    f"{game.players[seat].name} calls {call.rank}{SUIT_SYMBOLS[call.suit]} (fix) "
                    f"— the other copy holder is the secret partner..."
                )

            elif call.mode == BheruCallMode.BOTH:
                holders = _find_all_card_holders(game, call.rank, call.suit, exclude_seat=seat)
                if len(holders) == 0:
                    bheru_info.holder_seat = None
                elif len(holders) == 1:
                    bheru_info.holder_seat = holders[0]
                else:
                    bheru_info.holder_seat = holders[0]
                    game.bherus.append(bheru_info)
                    bheru_info2 = BheruInfo(call=call, holder_seat=holders[1], revealed=False)
                    game.bherus.append(bheru_info2)
                    game.log.append(
                        f"{game.players[seat].name} calls both {call.rank}{SUIT_SYMBOLS[call.suit]} "
                        f"— two secret partners have been chosen..."
                    )
                    continue

                game.log.append(
                    f"{game.players[seat].name} calls both {call.rank}{SUIT_SYMBOLS[call.suit]} "
                    f"— secret partner(s) chosen..."
                )

            elif call.mode == BheruCallMode.SECOND:
                bheru_info.holder_seat = None
                bheru_info.play_count = 0
                game.log.append(
                    f"{game.players[seat].name} calls {call.rank}{SUIT_SYMBOLS[call.suit]} (second play) "
                    f"— the partner will be revealed during play..."
                )

            game.bherus.append(bheru_info)

    real_bherus = [b for b in game.bherus if b.holder_seat is not None and b.holder_seat != seat]
    if not calls or (calls and not real_bherus and not any(b.call.mode == BheruCallMode.SECOND for b in game.bherus)):
        game.is_solo = True

    start_playing_fn(game, seat)


def _find_card_holder(game: GameState, rank: str, suit: str, exclude_seat: Optional[int]) -> Optional[int]:
    """Find which seat holds a card (first match)."""
    for s, hand in game.hands.items():
        if s == exclude_seat:
            continue
        for c in hand:
            if c.rank == rank and c.suit == suit:
                return s
    return None


def _find_all_card_holders(game: GameState, rank: str, suit: str, exclude_seat: Optional[int]) -> list[int]:
    """Find all seats holding copies of a card."""
    holders = []
    for s, hand in game.hands.items():
        if s == exclude_seat:
            continue
        for c in hand:
            if c.rank == rank and c.suit == suit:
                if s not in holders:
                    holders.append(s)
    return holders


def _check_bheru_reveal(game: GameState, seat: int, card: Card) -> None:
    """Check if playing this card reveals a bheru."""
    for bheru in game.bherus:
        if bheru.revealed:
            continue

        call = bheru.call
        if card.rank != call.rank or card.suit != call.suit:
            continue

        if call.mode == BheruCallMode.SECOND:
            bheru.play_count += 1
            if bheru.play_count == 2:
                bheru.holder_seat = seat
                bheru.revealed = True
                game.log.append(
                    f"The card falls for the second time — {game.players[seat].name} "
                    f"is revealed as the secret partner!"
                )
            elif bheru.play_count == 1:
                game.log.append(
                    f"{game.players[seat].name} plays {call.rank}{SUIT_SYMBOLS[call.suit]} "
                    f"first — not the partner yet..."
                )
        else:
            if bheru.holder_seat == seat:
                bheru.revealed = True
                game.log.append(
                    f"The secret card falls — {game.players[seat].name} "
                    f"is revealed as the hidden partner!"
                )
