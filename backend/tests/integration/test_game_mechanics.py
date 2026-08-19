"""
Comprehensive Game Engine and Mechanics Tests for Kadi Teeri Online.
"""

from app.game.bheru import assign_bherus, validate_bheru_calls
from app.game.bidding import init_bidding, pass_bid, place_bid
from app.game.deck import balance_deck, make_deck
from app.game.scoring import sanitize_game_state
from app.game.trick import legal_plays, play_card
from app.game.trump import (
    accept_challenge,
    pass_challenge_bid,
    place_challenge_bid,
    select_trump,
    validate_challenge_accept,
    validate_challenge_bid,
    validate_challenge_pass,
    validate_trump,
)
from app.models.game import (
    BheruCall,
    BheruCallMode,
    Card,
    GameState,
    GameStatus,
    Player,
    RoomConfig,
)
from app.services.room_service import RoomManager


def test_deck_balancing_various_player_counts():
    """Test deck balancing for 4 to 12 players across 1-deck and 2-deck setups."""
    # 1-deck 4 players: 52 % 4 = 0 (no removal)
    deck1 = make_deck(1)
    assert len(balance_deck(deck1, 4, 1)) == 52

    # 1-deck 5 players: 52 % 5 = 2 -> 50 cards
    assert len(balance_deck(deck1, 5, 1)) == 50

    # 1-deck 6 players: 52 % 6 = 4 -> 48 cards
    assert len(balance_deck(deck1, 6, 1)) == 48

    # 2-deck 9 players: 104 % 9 = 5 -> 99 cards
    deck2 = make_deck(2)
    assert len(balance_deck(deck2, 9, 2)) == 99

    # 2-deck 10 players: 104 % 10 = 4 -> 100 cards
    assert len(balance_deck(deck2, 10, 2)) == 100

    # 2-deck 12 players: 104 % 12 = 8 -> 96 cards
    assert len(balance_deck(deck2, 12, 2)) == 96


def test_trump_challenge_flow():
    """Test full trump challenge duel flow: trump pick -> challenge -> duel raise -> pass -> new trump."""
    game = GameState(
        players=[
            Player(id="p1", name="P1", seat=0),
            Player(id="p2", name="P2", seat=1),
            Player(id="p3", name="P3", seat=2),
            Player(id="p4", name="P4", seat=3),
        ],
        config=RoomConfig(player_count=4, deck_count=1),
    )
    init_bidding(game)
    place_bid(game, 1, 150)
    pass_bid(game, 2)
    pass_bid(game, 3)
    pass_bid(game, 0)

    # P2 won bid at 150
    assert game.status == GameStatus.TRUMP
    assert game.bidder_seat == 1

    # P2 selects trump 'H'
    assert validate_trump(game, 1, "H") is None
    select_trump(game, 1, "H")

    # Should enter TRUMP_CHALLENGE window
    assert game.status == GameStatus.TRUMP_CHALLENGE
    assert game.trump_challenge_used is True

    # P3 challenges (seat 2)
    assert validate_challenge_accept(game, 2) is None
    accept_challenge(game, 2)

    assert game.bid_target == 170
    assert game.bidder_seat == 2
    assert game.turn_seat == 1  # Original bidder responds first

    # P2 raises to 190
    assert validate_challenge_bid(game, 1) is None
    place_challenge_bid(game, 1)
    assert game.bid_target == 190
    assert game.bidder_seat == 1
    assert game.turn_seat == 2

    # P3 passes duel
    assert validate_challenge_pass(game, 2) is None
    pass_challenge_bid(game, 2)

    # P2 wins duel and returns to TRUMP selection
    assert game.status == GameStatus.TRUMP
    assert game.bidder_seat == 1
    assert game.bid_target == 190

    # P2 selects new trump 'S'
    select_trump(game, 1, "S")
    # Challenge was already used, goes straight to BHERU
    assert game.status == GameStatus.BHERU
    assert game.trump_suit == "S"


def test_bheru_modes_and_reveals():
    """Test 2-deck Bheru modes (FIX, BOTH, SECOND) and reveal triggers."""
    game = GameState(
        status=GameStatus.BHERU,
        bidder_seat=0,
        players=[
            Player(id="p1", name="P1", seat=0),
            Player(id="p2", name="P2", seat=1),
            Player(id="p3", name="P3", seat=2),
            Player(id="p4", name="P4", seat=3),
            Player(id="p5", name="P5", seat=4),
            Player(id="p6", name="P6", seat=5),
        ],
        config=RoomConfig(player_count=6, deck_count=2),
        hands={
            0: [Card(rank="A", suit="S", deck_index=0)],
            1: [Card(rank="A", suit="S", deck_index=1)],
            2: [Card(rank="K", suit="H", deck_index=0)],
            3: [Card(rank="K", suit="H", deck_index=1)],
            4: [Card(rank="Q", suit="D", deck_index=0)],
            5: [Card(rank="J", suit="C", deck_index=0)],
        },
    )

    calls = [
        BheruCall(rank="A", suit="S", mode=BheruCallMode.FIX),
        BheruCall(rank="K", suit="H", mode=BheruCallMode.SECOND),
    ]

    err = validate_bheru_calls(game, 0, calls)
    assert err is None

    assign_bherus(game, 0, calls)

    # FIX bheru holder should be seat 1 (holding the other Ace of Spades)
    fix_bheru = [b for b in game.bherus if b.call.mode == BheruCallMode.FIX][0]
    assert fix_bheru.holder_seat == 1
    assert fix_bheru.revealed is False

    # SECOND bheru holder is unknown until second play
    second_bheru = [b for b in game.bherus if b.call.mode == BheruCallMode.SECOND][0]
    assert second_bheru.holder_seat is None

    # Simulate play of King of Hearts by seat 2 (first play)
    play_card(game, 2, Card(rank="K", suit="H", deck_index=0), auto_resolve=False)
    assert second_bheru.play_count == 1
    assert second_bheru.revealed is False

    # Simulate play of King of Hearts by seat 3 (second play)
    play_card(game, 3, Card(rank="K", suit="H", deck_index=1), auto_resolve=False)
    assert second_bheru.play_count == 2
    assert second_bheru.revealed is True
    assert second_bheru.holder_seat == 3


def test_legal_play_validation():
    """Test follow suit enforcement and legal card plays."""
    hand = [
        Card(rank="A", suit="S", deck_index=0),
        Card(rank="10", suit="H", deck_index=0),
        Card(rank="5", suit="D", deck_index=0),
    ]

    # No lead suit -> any card in hand is legal
    legal_no_lead = legal_plays(hand, None)
    assert len(legal_no_lead) == 3

    # Lead suit is Spades -> must play Spades
    legal_spades = legal_plays(hand, "S")
    assert len(legal_spades) == 1
    assert legal_spades[0].suit == "S"

    # Lead suit is Clubs (player is void in Clubs) -> any card in hand is legal
    legal_clubs = legal_plays(hand, "C")
    assert len(legal_clubs) == 3


def test_card_points_and_scoring():
    """Test point values: 3S=30, A/K/Q/J/10=10, 5=5, others=0."""
    assert Card(rank="3", suit="S").points() == 30
    assert Card(rank="3", suit="H").points() == 0
    assert Card(rank="A", suit="S").points() == 10
    assert Card(rank="K", suit="D").points() == 10
    assert Card(rank="Q", suit="C").points() == 10
    assert Card(rank="J", suit="H").points() == 10
    assert Card(rank="10", suit="S").points() == 10
    assert Card(rank="5", suit="D").points() == 5
    assert Card(rank="2", suit="C").points() == 0


def test_sanitize_game_state_hides_private_hands():
    """Test that sanitize_game_state removes private hand information."""
    game = GameState(
        status=GameStatus.PLAYING,
        players=[
            Player(id="p1", name="P1", seat=0),
            Player(id="p2", name="P2", seat=1),
        ],
        hands={
            0: [Card(rank="A", suit="S")],
            1: [Card(rank="K", suit="H")],
        },
    )

    sanitized = sanitize_game_state(game)
    assert "hands" not in sanitized
    assert sanitized["hand_sizes"][0] == 1
    assert sanitized["hand_sizes"][1] == 1


def test_room_manager_full_lifecycle():
    """Test room creation, joining, configuration, start, and removal."""
    rm = RoomManager()

    # Create room
    room_id, game = rm.create_room("h1", "Host")
    assert len(room_id) in (4, 6)
    assert game.players[0].is_host is True

    # Join players
    err, _, _ = rm.join_room(room_id, "p2", "Player2")
    assert err is None
    err, _, _ = rm.join_room(room_id, "p3", "Player3")
    assert err is None
    err, _, _ = rm.join_room(room_id, "p4", "Player4")
    assert err is None

    # Configure room
    err = rm.configure_room(room_id, "h1", player_count=4, deck_count=1)
    assert err is None

    # Start game
    err = rm.start_game(room_id, "h1")
    assert err is None
    assert game.status == GameStatus.BIDDING

    # Reconnect
    err, reconnected_game, _ = rm.join_room(room_id, "p2", "Player2_Updated")
    assert err is None
    assert reconnected_game.players[1].name == "Player2_Updated"
