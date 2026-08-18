"""
Shared test fixtures for Kadi Teeri game engine tests.
"""
import pytest
from models import Player, GameState, GameStatus, RoomConfig, Card


@pytest.fixture
def four_player_game():
    """Create a standard 4-player game state for testing."""
    game = GameState(
        players=[
            Player(id=str(i), name=f"P{i+1}", seat=i)
            for i in range(4)
        ],
        config=RoomConfig(player_count=4, deck_count=1),
    )
    return game


@pytest.fixture
def six_player_game():
    """Create a 6-player game state for testing."""
    game = GameState(
        players=[
            Player(id=str(i), name=f"P{i+1}", seat=i)
            for i in range(6)
        ],
        config=RoomConfig(player_count=6, deck_count=1),
    )
    return game


@pytest.fixture
def eight_player_double_deck():
    """Create an 8-player, 2-deck game state for testing."""
    game = GameState(
        players=[
            Player(id=str(i), name=f"P{i+1}", seat=i)
            for i in range(8)
        ],
        config=RoomConfig(player_count=8, deck_count=2),
    )
    return game


@pytest.fixture
def sample_hand():
    """A sample hand of cards for testing."""
    return [
        Card(rank="A", suit="S", deck_index=0),
        Card(rank="K", suit="S", deck_index=0),
        Card(rank="Q", suit="H", deck_index=0),
        Card(rank="J", suit="H", deck_index=0),
        Card(rank="10", suit="D", deck_index=0),
        Card(rank="5", suit="D", deck_index=0),
        Card(rank="3", suit="S", deck_index=0),  # Teeri!
        Card(rank="7", suit="C", deck_index=0),
        Card(rank="4", suit="C", deck_index=0),
        Card(rank="2", suit="H", deck_index=0),
    ]
