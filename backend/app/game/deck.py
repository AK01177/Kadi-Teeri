"""
Deck creation, card balancing, shuffling, and hand sorting.
"""

from __future__ import annotations

import random

from app.models.game import (
    RANKS,
    REMOVAL_PRIORITY_1DECK,
    REMOVAL_PRIORITY_2DECK,
    SUITS,
    Card,
    rank_index,
)


def make_deck(deck_count: int = 1) -> list[Card]:
    """Create a full deck (or double deck) of cards."""
    deck: list[Card] = []
    for d in range(deck_count):
        for s in SUITS:
            for r in RANKS:
                deck.append(Card(rank=r, suit=s, deck_index=d))
    return deck


def balance_deck(deck: list[Card], num_players: int, deck_count: int = 1) -> list[Card]:
    """Remove lowest-ranked cards so total cards divide evenly among num_players."""
    total = len(deck)
    remainder = total % num_players
    if remainder == 0:
        return list(deck)

    priority = REMOVAL_PRIORITY_1DECK if deck_count == 1 else REMOVAL_PRIORITY_2DECK
    removed_count = 0
    balanced = list(deck)

    for item in priority:
        if removed_count >= remainder:
            break
        if deck_count == 1:
            r, s = item
            d_idx = 0
        else:
            r, s, d_idx = item

        target = Card(rank=r, suit=s, deck_index=d_idx)
        if target in balanced:
            balanced.remove(target)
            removed_count += 1

    return balanced


def shuffle_deck(deck: list[Card]) -> list[Card]:
    """Return a new shuffled copy of the deck."""
    shuffled = list(deck)
    random.shuffle(shuffled)
    return shuffled


def deal_cards(deck: list[Card], num_players: int) -> dict[int, list[Card]]:
    """Deal cards equally to all players by seat index."""
    cards_per_player = len(deck) // num_players
    hands: dict[int, list[Card]] = {}
    for i in range(num_players):
        start = i * cards_per_player
        end = start + cards_per_player
        hands[i] = sort_hand(deck[start:end])
    return hands


def sort_hand(hand: list[Card]) -> list[Card]:
    """Sort a hand by suit priority (S, H, D, C) and rank descending."""
    suit_order = {"S": 0, "H": 1, "D": 2, "C": 3}
    return sorted(
        hand,
        key=lambda c: (suit_order.get(c.suit, 4), -rank_index(c.rank), c.deck_index),
    )
