from fastapi.testclient import TestClient

from main import app
from room_manager import room_manager

client = TestClient(app)

def test_create_room():
    response = client.post("/api/rooms", json={"player_name": "TestPlayer"})
    assert response.status_code == 200
    data = response.json()
    assert "room_id" in data
    assert "player_id" in data
    room_manager._rooms.clear()
    room_manager._player_rooms.clear()

def test_websocket_join_and_leave():
    response = client.post("/api/rooms", json={"player_name": "Host"})
    data = response.json()
    room_id = data["room_id"]
    player_id = data["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as websocket:
        # Send join message
        websocket.send_json({"type": "join", "name": "Host", "player_id": player_id})

        # Should receive welcome
        welcome = websocket.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["player_id"] == player_id

        # Should receive game_state
        state = websocket.receive_json()
        assert state["type"] == "game_state"

    # Connection closed
    # Cleanup
    room_manager._rooms.clear()
    room_manager._player_rooms.clear()

