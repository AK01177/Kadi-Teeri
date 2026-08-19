"""
Pytest configuration and shared test fixtures for unit and integration tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.game import Card, GameState, GameStatus, Player, RoomConfig


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient instance."""
    return TestClient(app)


@pytest.fixture
def sample_game_state() -> GameState:
    """Standard 4-player lobby GameState fixture."""
    players = [Player(id=f"p{i}", name=f"Player {i}", seat=i, is_host=(i == 0)) for i in range(4)]
    return GameState(
        status=GameStatus.LOBBY,
        config=RoomConfig(player_count=4, deck_count=1),
        players=players,
        dealer=0,
    )

@pytest.fixture
def four_player_game() -> GameState:
    """Create a standard 4-player game state for testing."""
    return GameState(
        players=[Player(id=str(i), name=f"P{i+1}", seat=i, is_host=(i == 0)) for i in range(4)],
        config=RoomConfig(player_count=4, deck_count=1),
    )

@pytest.fixture
def six_player_game() -> GameState:
    """Create a 6-player game state for testing."""
    return GameState(
        players=[Player(id=str(i), name=f"P{i+1}", seat=i, is_host=(i == 0)) for i in range(6)],
        config=RoomConfig(player_count=6, deck_count=1),
    )

@pytest.fixture
def eight_player_double_deck() -> GameState:
    """Create an 8-player, 2-deck game state for testing."""
    return GameState(
        players=[Player(id=str(i), name=f"P{i+1}", seat=i, is_host=(i == 0)) for i in range(8)],
        config=RoomConfig(player_count=8, deck_count=2),
    )

@pytest.fixture
def sample_hand() -> list[Card]:
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
