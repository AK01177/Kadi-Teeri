"""
Deck creation, card balancing, shuffling, and hand sorting.
"""

from __future__ import annotations

import random

from models import (
    RANKS,
    REMOVAL_PRIORITY_1DECK,
    REMOVAL_PRIORITY_2DECK,
    SUITS,
    Card,
    rank_index,
)


def make_deck(deck_count: int = 1) -> list[Card]:
    """Create a full deck (or double deck) of cards."""
    cards = []
    for di in range(deck_count):
        for suit in SUITS:
            for rank in RANKS:
                cards.append(Card(rank=rank, suit=suit, deck_index=di))
    return cards


def balance_deck(cards: list[Card], num_players: int, deck_count: int) -> list[Card]:
    """
    Remove 2-cards until the deck divides evenly among players.
    Removal priority: 2♣, 2♦, 2♥, 2♠ (repeat for second deck).
    """
    if deck_count == 1:
        priority = [(r, s) for r, s in REMOVAL_PRIORITY_1DECK]
    else:
        priority = [(r, s, di) for r, s, di in REMOVAL_PRIORITY_2DECK]

    result = list(cards)
    removal_idx = 0

    while len(result) % num_players != 0 and removal_idx < len(priority):
        if deck_count == 1:
            p = priority[removal_idx]
            r, s = p[0], p[1]
            result = [c for c in result if not (c.rank == r and c.suit == s)]
        else:
            p = priority[removal_idx]
            r, s, di = p[0], p[1], p[2]
            result = [c for c in result if not (c.rank == r and c.suit == s and c.deck_index == di)]
        removal_idx += 1

    return result


def shuffle_deck(cards: list[Card]) -> list[Card]:
    """Fisher-Yates shuffle."""
    deck = list(cards)
    random.shuffle(deck)
    return deck


def deal_cards(deck: list[Card], num_players: int) -> dict[int, list[Card]]:
    """Deal cards equally to all players. Returns seat -> list of cards."""
    hands: dict[int, list[Card]] = {i: [] for i in range(num_players)}
    for i, card in enumerate(deck):
        hands[i % num_players].append(card)
    for seat in hands:
        hands[seat] = sort_hand(hands[seat])
    return hands


def sort_hand(hand: list[Card]) -> list[Card]:
    """Sort a hand by suit order (S, H, D, C) then by rank."""
    suit_order = {"S": 0, "H": 1, "D": 2, "C": 3}
    return sorted(hand, key=lambda c: (suit_order.get(c.suit, 4), rank_index(c.rank)))
