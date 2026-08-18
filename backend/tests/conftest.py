"""
Pytest configuration and shared test fixtures for unit and integration tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.game import GameState, GameStatus, Player, RoomConfig


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
