"""
Kadi Teeri Online — Game Engine

All game logic: deck creation, card balancing, shuffling, dealing,
bidding, trump selection, bheru assignment, trick-taking, scoring.

The server is the single source of truth — every move is validated here.
"""

from __future__ import annotations

import random
from typing import Optional

from models import (
    RANKS, SUITS, SUIT_NAMES, SUIT_SYMBOLS,
    REMOVAL_PRIORITY_1DECK, REMOVAL_PRIORITY_2DECK,
    rank_index, card_points,
    Card, Player, GameState, GameStatus, RoomConfig,
    BiddingState, BidEntry, TrickState, TrickPlay,
    BheruCall, BheruCallMode, BheruInfo, RoundResult,
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
            r, s, di = p[0], p[1], p[2] # type: ignore
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
    # Sort each hand by suit then rank
    for seat in hands:
        hands[seat] = sort_hand(hands[seat])
    return hands


def sort_hand(hand: list[Card]) -> list[Card]:
    """Sort a hand by suit order (S, H, D, C) then by rank."""
    suit_order = {"S": 0, "H": 1, "D": 2, "C": 3}
    return sorted(hand, key=lambda c: (suit_order.get(c.suit, 4), rank_index(c.rank)))


def max_bherus(num_players: int) -> int:
    """Maximum number of bherus the bidder can call."""
    return (num_players // 2) - 1


def max_bid(deck_count: int) -> int:
    """Maximum possible bid."""
    return 250 * deck_count


# ──────────────────────────── Bidding ────────────────────────────


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
    game.add_log(f"— Round {game.rounds_played + 1} — {game.players[first].name} bids first.")


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
    game.add_log(f"{game.players[seat].name} bids {amount}.")
    advance_bidding_turn(game)


def pass_bid(game: GameState, seat: int) -> None:
    """Pass on bidding."""
    b = game.bidding
    b.passed[seat] = True
    b.history.append(BidEntry(seat=seat, action="pass"))
    game.add_log(f"{game.players[seat].name} passes.")
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
            game.add_log(
                f"{game.players[winner].name} is forced to take the minimum bid of 150 (everyone else passed)."
            )
        else:
            game.add_log(
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


# ──────────────────────────── Trump Selection ────────────────────────────


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
    import time
    game.trump_suit = suit
    game.add_log(f"{game.players[seat].name} names {SUIT_NAMES[suit]} as trump.")

    if not game.trump_challenge_used:
        # Enter the one-time challenge window
        game.status = GameStatus.TRUMP_CHALLENGE
        game.trump_challenge_used = True
        game.challenge_deadline = time.time() + 10  # 10 seconds
        game.challenge_duel_seats = None
        game.challenger_seat = None
        game.add_log("Other players have 10 seconds to challenge the bid!")
    else:
        # Challenge already used this round — go straight to bheru
        game.status = GameStatus.BHERU


# ──────────────────────────── Trump Challenge ────────────────────────────


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
    game.challenge_deadline = None  # Cancel the countdown
    game.turn_seat = original_bidder  # Original bidder responds first
    game.trump_suit = None  # Reset trump — duel winner picks new one
    game.add_log(
        f"{game.players[seat].name} challenges the bid at {new_amount}!"
    )


def expire_trump_challenge(game: GameState) -> None:
    """No one challenged within the time limit — proceed to bheru."""
    if game.status != GameStatus.TRUMP_CHALLENGE:
        return
    if game.challenge_duel_seats is not None:
        return  # Duel in progress, don't expire
    game.challenge_deadline = None
    game.status = GameStatus.BHERU
    game.add_log("No one challenged. Proceeding to partner selection.")


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
        # Can't raise further — auto-win for the other side
        pass_challenge_bid(game, seat)
        return
    game.bid_target = new_amount
    game.bidder_seat = seat
    # Switch turn to the other duelist
    other = [s for s in game.challenge_duel_seats if s != seat][0]
    game.turn_seat = other
    game.add_log(f"{game.players[seat].name} raises to {new_amount}.")


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
    # Winner must now pick a new trump suit
    game.status = GameStatus.TRUMP
    game.add_log(
        f"{game.players[seat].name} concedes. "
        f"{game.players[winner].name} wins the challenge at {game.bid_target} and will choose trump."
    )


# ──────────────────────────── Bheru Selection ────────────────────────────


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

        # Validate mode based on deck count
        if deck_count == 1 and call.mode != BheruCallMode.SIMPLE:
            return "Only 'simple' mode is allowed for 1-deck games."
        if deck_count == 2 and call.mode == BheruCallMode.SIMPLE:
            return "Use 'fix', 'both', or 'second' mode for 2-deck games."

        # For FIX mode: bidder must have one copy
        if call.mode == BheruCallMode.FIX:
            bidder_hand = game.hands.get(seat, [])
            has_copy = any(c.rank == call.rank and c.suit == call.suit for c in bidder_hand)
            if not has_copy:
                return f"FIX mode requires you to hold one copy of {call.rank}{SUIT_SYMBOLS[call.suit]}."

    return None


def assign_bherus(game: GameState, seat: int, calls: list[BheruCall]) -> None:
    """Assign bherus based on the calls."""
    n = len(game.players)
    game.bheru_calls = calls
    game.bherus = []

    if not calls:
        # Solo play
        game.is_solo = True
        game.add_log(f"{game.players[seat].name} chooses to play SOLO against the table!")
    else:
        game.is_solo = False
        for call in calls:
            bheru_info = BheruInfo(call=call, revealed=False)

            if call.mode == BheruCallMode.SIMPLE:
                # 1-deck: find who holds the card
                holder = _find_card_holder(game, call.rank, call.suit, exclude_seat=None)
                if holder == seat:
                    # Bidder holds it — this call is effectively solo for this bheru slot
                    game.add_log(
                        f"{game.players[seat].name} calls {call.rank}{SUIT_SYMBOLS[call.suit]} "
                        f"— they hold it themselves!"
                    )
                    bheru_info.holder_seat = seat
                    bheru_info.revealed = True
                else:
                    bheru_info.holder_seat = holder
                    game.add_log(
                        f"{game.players[seat].name} calls for {call.rank}{SUIT_SYMBOLS[call.suit]} "
                        f"— a secret partner has been chosen..."
                    )

            elif call.mode == BheruCallMode.FIX:
                # 2-deck: bidder has one, wants the other
                holder = _find_card_holder(game, call.rank, call.suit, exclude_seat=seat)
                bheru_info.holder_seat = holder
                game.add_log(
                    f"{game.players[seat].name} calls {call.rank}{SUIT_SYMBOLS[call.suit]} (fix) "
                    f"— the other copy holder is the secret partner..."
                )

            elif call.mode == BheruCallMode.BOTH:
                # 2-deck: wants both copy holders
                holders = _find_all_card_holders(game, call.rank, call.suit, exclude_seat=seat)
                # For "both" mode, the bheru_info represents one holder
                # We create two BheruInfo entries (handled below)
                if len(holders) == 0:
                    bheru_info.holder_seat = None
                elif len(holders) == 1:
                    bheru_info.holder_seat = holders[0]
                else:
                    # Two holders — create entries for both
                    bheru_info.holder_seat = holders[0]
                    game.bherus.append(bheru_info)
                    bheru_info2 = BheruInfo(call=call, holder_seat=holders[1], revealed=False)
                    game.bherus.append(bheru_info2)
                    game.add_log(
                        f"{game.players[seat].name} calls both {call.rank}{SUIT_SYMBOLS[call.suit]} "
                        f"— two secret partners have been chosen..."
                    )
                    continue  # Skip the append below since we already added both

                game.add_log(
                    f"{game.players[seat].name} calls both {call.rank}{SUIT_SYMBOLS[call.suit]} "
                    f"— secret partner(s) chosen..."
                )

            elif call.mode == BheruCallMode.SECOND:
                # 2-deck: whoever plays it second becomes the bheru
                bheru_info.holder_seat = None  # Unknown until play
                bheru_info.play_count = 0
                game.add_log(
                    f"{game.players[seat].name} calls {call.rank}{SUIT_SYMBOLS[call.suit]} (second play) "
                    f"— the partner will be revealed during play..."
                )

            game.bherus.append(bheru_info)

    # Check if all bherus are the bidder themselves (all solo)
    real_bherus = [b for b in game.bherus if b.holder_seat is not None and b.holder_seat != seat]
    if not calls or (calls and not real_bherus and not any(b.call.mode == BheruCallMode.SECOND for b in game.bherus)):
        game.is_solo = True

    # Move to playing phase
    _start_playing(game, seat)


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


def _start_playing(game: GameState, bidder_seat: int) -> None:
    """Initialize the playing phase."""
    n = len(game.players)
    game.status = GameStatus.PLAYING
    game.trick = TrickState(leader_seat=bidder_seat, lead_suit=None, cards_played=[])
    game.trick_number = 1
    game.turn_seat = bidder_seat
    game.captured = {i: [] for i in range(n)}


# ──────────────────────────── Playing ────────────────────────────


def legal_plays(hand: list[Card], lead_suit: Optional[str]) -> list[Card]:
    """Get legal cards to play from a hand."""
    if not lead_suit:
        return list(hand)
    following = [c for c in hand if c.suit == lead_suit]
    return following if following else list(hand)


def validate_play(game: GameState, seat: int, card: Card) -> Optional[str]:
    """Validate a card play."""
    if game.status != GameStatus.PLAYING:
        return "Not in playing phase."
    if game.turn_seat != seat:
        return "Not your turn."
    if game.trick is None:
        return "No trick in progress."

    hand = game.hands.get(seat, [])
    # Check card is in hand
    if not any(c.rank == card.rank and c.suit == card.suit and c.deck_index == card.deck_index for c in hand):
        return "You don't have that card."

    # Check card is a legal play
    legal = legal_plays(hand, game.trick.lead_suit)
    if not any(c.rank == card.rank and c.suit == card.suit and c.deck_index == card.deck_index for c in legal):
        return f"You must follow {SUIT_NAMES.get(game.trick.lead_suit, 'the led suit')} if you can."

    return None


def play_card(game: GameState, seat: int, card: Card, auto_resolve: bool = True) -> bool:
    """Play a card in the current trick. Returns True if the trick is complete."""
    n = len(game.players)
    hand = game.hands[seat]

    # Remove card from hand
    for i, c in enumerate(hand):
        if c.rank == card.rank and c.suit == card.suit and c.deck_index == card.deck_index:
            hand.pop(i)
            break

    # Add to trick
    game.trick.cards_played.append(TrickPlay(seat=seat, card=card))
    if len(game.trick.cards_played) == 1:
        game.trick.lead_suit = card.suit

    # Check bheru reveals
    _check_bheru_reveal(game, seat, card)

    game.add_log(f"{game.players[seat].name} plays {card.label()}.")

    # Check if trick is complete
    if len(game.trick.cards_played) == n:
        if auto_resolve:
            resolve_trick(game)
        return True
    else:
        # Next player's turn
        game.turn_seat = (seat + 1) % n
        return False


def _check_bheru_reveal(game: GameState, seat: int, card: Card) -> None:
    """Check if playing this card reveals a bheru."""
    for bheru in game.bherus:
        if bheru.revealed:
            continue

        call = bheru.call
        if card.rank != call.rank or card.suit != call.suit:
            continue

        if call.mode == BheruCallMode.SECOND:
            # Track play count
            bheru.play_count += 1
            if bheru.play_count == 2:
                # Second play — this player is the bheru
                bheru.holder_seat = seat
                bheru.revealed = True
                game.add_log(
                    f"The card falls for the second time — {game.players[seat].name} "
                    f"is revealed as the secret partner!"
                )
            elif bheru.play_count == 1:
                game.add_log(
                    f"{game.players[seat].name} plays {call.rank}{SUIT_SYMBOLS[call.suit]} "
                    f"first — not the partner yet..."
                )
        else:
            # Simple, Fix, Both — reveal when the called card is played
            if bheru.holder_seat == seat:
                bheru.revealed = True
                game.add_log(
                    f"The secret card falls — {game.players[seat].name} "
                    f"is revealed as the hidden partner!"
                )


# ──────────────────────────── Trick Resolution ────────────────────────────


def resolve_trick(game: GameState) -> None:
    """Determine who wins the trick and start next trick or finish round."""
    trick = game.trick
    trump = game.trump_suit
    n = len(game.players)

    cards_played = trick.cards_played
    lead_suit = trick.lead_suit

    # Determine winner
    winner_entry = _determine_trick_winner(cards_played, lead_suit, trump)
    winner_seat = winner_entry.seat

    # Capture cards
    for tp in cards_played:
        game.captured[winner_seat].append(tp.card)

    game.add_log(f"{game.players[winner_seat].name} takes the trick.")

    # Check if all cards have been played
    cards_per_player = len(game.hands.get(0, [])) if 0 in game.hands else 0
    all_played = all(len(game.hands.get(s, [])) == 0 for s in range(n))

    if all_played:
        finish_round(game)
    else:
        game.trick_number += 1
        game.trick = TrickState(leader_seat=winner_seat, lead_suit=None, cards_played=[])
        game.turn_seat = winner_seat


def _determine_trick_winner(
    cards_played: list[TrickPlay], lead_suit: str, trump: str
) -> TrickPlay:
    """
    Determine which card wins the trick.

    Rules:
    1. If any trump cards were played, highest trump wins.
    2. Otherwise, highest card of the lead suit wins.
    3. DUPLICATE RULE (2-deck): If two identical highest cards exist,
       the one played LATER (higher index) wins.
    """
    trumped = [tp for tp in cards_played if tp.card.suit == trump]

    if trumped:
        return _highest_card_last_wins(trumped)
    else:
        followed = [tp for tp in cards_played if tp.card.suit == lead_suit]
        return _highest_card_last_wins(followed)


def _highest_card_last_wins(entries: list[TrickPlay]) -> TrickPlay:
    """
    Find the entry with the highest rank.
    If tied (same rank, same suit — 2-deck duplicate), the LAST one wins.
    """
    best = entries[0]
    for entry in entries[1:]:
        if rank_index(entry.card.rank) >= rank_index(best.card.rank):
            best = entry
    return best


# ──────────────────────────── Scoring ────────────────────────────


def finish_round(game: GameState) -> None:
    """Calculate scores and determine winner for the round."""
    n = len(game.players)
    bidder = game.bidder_seat

    # Determine bidding team seats
    bidding_seats = [bidder]
    for bheru in game.bherus:
        if bheru.holder_seat is not None and bheru.holder_seat != bidder:
            if bheru.holder_seat not in bidding_seats:
                bidding_seats.append(bheru.holder_seat)

    # Reveal all unrevealed bherus at round end
    for bheru in game.bherus:
        if not bheru.revealed and bheru.holder_seat is not None:
            bheru.revealed = True

    defending_seats = [s for s in range(n) if s not in bidding_seats]

    # Calculate points per seat
    per_seat: dict[int, int] = {}
    for s in range(n):
        pts = sum(c.points() for c in game.captured.get(s, []))
        per_seat[s] = pts

    bidding_points = sum(per_seat.get(s, 0) for s in bidding_seats)
    total_points = 250 * game.config.deck_count
    defending_points = total_points - bidding_points
    bidding_won = bidding_points >= game.bid_target

    # Record wins
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
        game.add_log(
            f"Bidding side reaches {bidding_points}/{game.bid_target} — contract made!"
        )
    else:
        game.add_log(
            f"Bidding side only reaches {bidding_points}/{game.bid_target} — contract failed."
        )


# ──────────────────────────── Deal New Round ────────────────────────────


def deal_new_round(game: GameState, is_first: bool = False) -> None:
    """Shuffle, balance, deal, and start bidding for a new round."""
    n = len(game.players)
    if not is_first:
        game.dealer = (game.dealer + 1) % n

    # Create and balance deck
    deck = make_deck(game.config.deck_count)
    deck = balance_deck(deck, n, game.config.deck_count)
    deck = shuffle_deck(deck)

    # Deal
    game.hands = deal_cards(deck, n)

    # Initialize bidding
    init_bidding(game)


# ──────────────────────────── Sanitize State ────────────────────────────


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
        "log": game.log[-20:],  # Last 20 log entries
        # Trump challenge fields
        "trump_challenge_used": game.trump_challenge_used,
        "challenge_deadline": game.challenge_deadline,
        "challenge_duel_seats": game.challenge_duel_seats,
        "challenger_seat": game.challenger_seat,
    }

    # Bidding state
    if game.bidding:
        state["bidding"] = game.bidding.model_dump()

    # Trick state (cards in the trick are public)
    if game.trick:
        state["trick"] = {
            "leader_seat": game.trick.leader_seat,
            "lead_suit": game.trick.lead_suit,
            "cards_played": [
                {"seat": tp.seat, "card": tp.card.model_dump()}
                for tp in game.trick.cards_played
            ],
        }

    # Bheru info (only reveal what's appropriate)
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

    # Round result
    if game.round_result:
        state["round_result"] = game.round_result.model_dump()

    # Card counts per player (so UI can show how many cards each player has)
    state["hand_sizes"] = {s: len(game.hands.get(s, [])) for s in range(len(game.players))}

    # Captured card counts and points
    state["captured_counts"] = {s: len(game.captured.get(s, [])) for s in range(len(game.players))}
    state["captured_points"] = {
        s: sum(c.points() for c in game.captured.get(s, []))
        for s in range(len(game.players))
    }

    return state
