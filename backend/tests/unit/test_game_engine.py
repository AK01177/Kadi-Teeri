from app.game.bidding import init_bidding, pass_bid, place_bid, validate_bid
from app.game.deck import balance_deck, make_deck
from app.game.trick import _determine_trick_winner
from app.models.game import Card, GameState, GameStatus, Player, RoomConfig, TrickPlay


def test_make_deck():
    deck1 = make_deck(1)
    assert len(deck1) == 52
    deck2 = make_deck(2)
    assert len(deck2) == 104


def test_balance_deck():
    deck = make_deck(1)
    balanced = balance_deck(deck, 5, 1)
    # 52 % 5 = 2. We need to remove 2 cards to get 50.
    assert len(balanced) == 50
    # The first 2 cards in removal priority are 2C, 2D
    removed_cards = [c for c in deck if c not in balanced]
    assert len(removed_cards) == 2
    assert any(c.rank == "2" and c.suit == "C" for c in removed_cards)
    assert any(c.rank == "2" and c.suit == "D" for c in removed_cards)


def test_bidding_logic():
    game = GameState(
        players=[
            Player(id="1", name="P1", seat=0),
            Player(id="2", name="P2", seat=1),
            Player(id="3", name="P3", seat=2),
            Player(id="4", name="P4", seat=3),
        ],
        config=RoomConfig(player_count=4, deck_count=1),
    )
    init_bidding(game)
    assert game.status == GameStatus.BIDDING
    assert game.turn_seat == 1  # (dealer + 1) % n. Dealer is 0

    # P2 bids 150
    err = validate_bid(game, 1, 150)
    assert err is None
    place_bid(game, 1, 150)

    # P3 bids 160
    assert validate_bid(game, 2, 160) is None
    place_bid(game, 2, 160)

    # P4 passes
    pass_bid(game, 3)

    # P1 bids 165
    assert validate_bid(game, 0, 165) is None
    place_bid(game, 0, 165)

    # P2 passes
    pass_bid(game, 1)

    # P3 passes
    pass_bid(game, 2)

    # Now P1 should win the bid
    assert game.status == GameStatus.TRUMP
    assert game.bidder_seat == 0
    assert game.bid_target == 165
    assert game.turn_seat == 0


def test_trick_winner_duplicate_rule():
    # 2-deck rule: If two identical highest cards exist, the one played LATER wins.
    cards_played = [
        TrickPlay(seat=0, card=Card(rank="A", suit="S", deck_index=0)),
        TrickPlay(seat=1, card=Card(rank="K", suit="S", deck_index=0)),
        TrickPlay(seat=2, card=Card(rank="A", suit="S", deck_index=1)),  # Duplicate highest
        TrickPlay(seat=3, card=Card(rank="Q", suit="S", deck_index=0)),
    ]
    winner = _determine_trick_winner(cards_played, lead_suit="S", trump="H")
    assert winner.seat == 2  # The later one wins


def test_kali_teeri_hierarchy():
    # If Trump is Spades, does 3 of Spades beat Ace of Spades?
    cards_played = [
        TrickPlay(seat=0, card=Card(rank="A", suit="S", deck_index=0)),
        TrickPlay(seat=1, card=Card(rank="3", suit="S", deck_index=0)),
    ]
    winner = _determine_trick_winner(cards_played, lead_suit="S", trump="S")
    # In Kaali Teeri, 3S is no longer the highest card, it just has standard rank 3
    assert winner.seat == 0, "Ace of Spades should beat 3 of Spades!"
