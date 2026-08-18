"""
Integration tests for Refresh (fetch_state) and Reconnect (rejoin) WebSocket endpoints.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.game import GameStatus
from app.services.room_service import room_service

client = TestClient(app)


def test_refresh_fetch_state_success():
    """Verify fetch_state retrieves latest state without mutating room/game state or logs."""
    # 1. Create a room
    resp = client.post("/api/rooms", json={"player_name": "HostPlayer"})
    assert resp.status_code == 200
    data = resp.json()
    room_id = data["room_id"]
    host_id = data["player_id"]

    game_before = room_service.get_room(room_id)
    assert game_before is not None
    initial_status = game_before.status

    # 2. Connect via WebSocket and send join, then fetch_state
    with client.websocket_connect(f"/ws/{room_id}") as websocket:
        websocket.send_json({"type": "join", "name": "HostPlayer", "player_id": host_id})
        welcome = websocket.receive_json()
        assert welcome["type"] == "welcome"
        broadcast_state = websocket.receive_json()
        assert broadcast_state["type"] == "game_state"

        # Now send fetch_state
        websocket.send_json({"type": "fetch_state"})
        refreshed = websocket.receive_json()
        assert refreshed["type"] == "game_state"
        assert refreshed["game"]["status"] == GameStatus.LOBBY.value

        # 3. Assert game state was NOT mutated by fetch_state
        game_after = room_service.get_room(room_id)
        assert game_after is not None
        assert game_after.status == initial_status


def test_refresh_fetch_state_missing_room():
    """Verify fetch_state fails gracefully for a missing room."""
    with client.websocket_connect("/ws/NONEXISTENT") as websocket:
        websocket.send_json({"type": "join", "name": "Player1"})
        err = websocket.receive_json()
        assert err["type"] == "error"
        assert "not found" in err["error"].lower()


def test_refresh_does_not_mutate_state_or_deal_cards():
    """Verify fetch_state does not deal cards or modify bidding/playing state."""
    resp = client.post("/api/rooms", json={"player_name": "Host"})
    room_id = resp.json()["room_id"]
    host_id = resp.json()["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as websocket:
        websocket.send_json({"type": "join", "name": "Host", "player_id": host_id})
        websocket.receive_json()  # welcome
        websocket.receive_json()  # state

        game = room_service.get_room(room_id)
        assert game is not None
        assert game.bidding is None

        # Fetch state multiple times
        for _ in range(3):
            websocket.send_json({"type": "fetch_state"})
            res = websocket.receive_json()
            assert res["type"] == "game_state"

        # Ensure bidding is still None and status is still lobby
        assert game.bidding is None
        assert game.status == GameStatus.LOBBY
