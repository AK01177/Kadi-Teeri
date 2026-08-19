import pytest
from app.game.bot import _pick_best_bot_card
from app.game.trick import legal_plays
from app.models.game import Card, GameState, GameStatus, Player, RoomConfig, TrickState


def test_bot_pick_best_card_leading():
    """Test bot card selection when leading a trick."""
    game = GameState(
        status=GameStatus.PLAYING,
        config=RoomConfig(),
        players=[Player(id="p1", name="Bot", seat=0, is_connected=False)],
        dealer=0,
        turn_seat=0,
        trick_number=1,
        trump_suit="S",
        trick=TrickState(leader_seat=0, lead_suit=None, cards_played=[]),
    )
    
    # Give the bot some cards
    game.hands = {
        0: [
            Card(rank="A", suit="H", deck_index=0),
            Card(rank="K", suit="S", deck_index=0),
            Card(rank="5", suit="D", deck_index=0),
            Card(rank="J", suit="H", deck_index=0),
            Card(rank="2", suit="S", deck_index=0),  # lowest trump
            Card(rank="3", suit="D", deck_index=0),  # lowest non-trump
        ]
    }
    
    card = _pick_best_bot_card(game, 0)
    assert card is not None
    # Lowest non-trump is 3 of Diamonds
    assert card.rank == "3" and card.suit == "D"


def test_bot_pick_best_card_leading_only_trumps():
    """Test bot card selection when leading but only holding trumps."""
    game = GameState(
        status=GameStatus.PLAYING,
        config=RoomConfig(),
        players=[Player(id="p1", name="Bot", seat=0, is_connected=False)],
        dealer=0,
        turn_seat=0,
        trick_number=1,
        trump_suit="S",
        trick=TrickState(leader_seat=0, lead_suit=None, cards_played=[]),
    )
    
    game.hands = {
        0: [
            Card(rank="A", suit="S", deck_index=0),
            Card(rank="10", suit="S", deck_index=0),
            Card(rank="5", suit="S", deck_index=0),
        ]
    }
    
    card = _pick_best_bot_card(game, 0)
    assert card is not None
    # Lowest trump is 5 of Spades
    assert card.rank == "5" and card.suit == "S"


def test_bot_pick_best_card_following_suit():
    """Test bot card selection when following suit."""
    game = GameState(
        status=GameStatus.PLAYING,
        config=RoomConfig(),
        players=[
            Player(id="p1", name="Human", seat=0, is_connected=True),
            Player(id="p2", name="Bot", seat=1, is_connected=False),
        ],
        dealer=0,
        turn_seat=1,
        trick_number=1,
        trump_suit="S",
        trick=TrickState(leader_seat=0, lead_suit="H", cards_played=[]),
    )
    
    game.hands = {
        1: [
            Card(rank="A", suit="H", deck_index=0),
            Card(rank="10", suit="H", deck_index=0),
            Card(rank="K", suit="D", deck_index=0),
            Card(rank="5", suit="H", deck_index=0),
        ]
    }
    
    card = _pick_best_bot_card(game, 1)
    assert card is not None
    # Must follow suit (H). Lowest is 5 of Hearts.
    assert card.rank == "5" and card.suit == "H"


def test_bot_pick_best_card_dropping():
    """Test bot card selection when unable to follow suit (dropping/cutting)."""
    game = GameState(
        status=GameStatus.PLAYING,
        config=RoomConfig(),
        players=[
            Player(id="p1", name="Human", seat=0, is_connected=True),
            Player(id="p2", name="Bot", seat=1, is_connected=False),
        ],
        dealer=0,
        turn_seat=1,
        trick_number=1,
        trump_suit="S",
        trick=TrickState(leader_seat=0, lead_suit="H", cards_played=[]),
    )
    
    game.hands = {
        1: [
            Card(rank="A", suit="D", deck_index=0),
            Card(rank="10", suit="C", deck_index=0),
            Card(rank="5", suit="D", deck_index=0),
            Card(rank="K", suit="S", deck_index=0),  # Trump
        ]
    }
    
    card = _pick_best_bot_card(game, 1)
    assert card is not None
    # Cannot follow H. Legal plays is entire hand.
    # Prefer lowest non-trump. Lowest non-trump is 5 of Diamonds.
    assert card.rank == "5" and card.suit == "D"
