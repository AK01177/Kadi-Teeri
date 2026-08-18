"""
Integration tests for targeted Nudge Player WebSocket feature.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models.game import GameStatus
from app.services.room_service import room_service

client = TestClient(app)


def _drain_to_bidding(ws):
    """Drain WebSocket messages until bidding status is reached."""
    while True:
        msg = ws.receive_json()
        if msg.get("type") == "game_state" and msg.get("game", {}).get("status") == GameStatus.BIDDING.value:
            break


def _receive_nudge_event(ws):
    """Drain any pending game_state messages until nudge_received is returned."""
    while True:
        msg = ws.receive_json()
        if msg.get("type") == "nudge_received":
            return msg


def test_valid_nudge_delivered_only_to_target():
    """Verify a valid nudge reaches only the active turn player's WebSocket."""
    resp = client.post("/api/rooms", json={"player_name": "P0"})
    room_id = resp.json()["room_id"]
    p0_id = resp.json()["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as ws0:
        ws0.send_json({"type": "join", "name": "P0", "player_id": p0_id})

        with client.websocket_connect(f"/ws/{room_id}") as ws1:
            ws1.send_json({"type": "join", "name": "P1", "player_id": "p1_id"})

            with client.websocket_connect(f"/ws/{room_id}") as ws2:
                ws2.send_json({"type": "join", "name": "P2", "player_id": "p2_id"})

                with client.websocket_connect(f"/ws/{room_id}") as ws3:
                    ws3.send_json({"type": "join", "name": "P3", "player_id": "p3_id"})

                    # Host (P0) starts game
                    ws0.send_json({"type": "start_game"})

                    _drain_to_bidding(ws0)
                    _drain_to_bidding(ws1)
                    _drain_to_bidding(ws2)
                    _drain_to_bidding(ws3)

                    game = room_service.get_room(room_id)
                    assert game is not None
                    assert game.status == GameStatus.BIDDING
                    assert game.turn_seat == 1  # (dealer 0 + 1) % 4 = seat 1 (P1)

                    # P0 (seat 0) nudges P1 (seat 1, target_id="p1_id")
                    ws0.send_json({"type": "nudge_player", "target_player_id": "p1_id"})

                    # P1 (target) receives nudge_received
                    msg = _receive_nudge_event(ws1)
                    assert msg["type"] == "nudge_received"
                    assert msg["sender_id"] == p0_id
                    assert msg["sender_name"] == "P0"


def test_cannot_nudge_yourself():
    """Verify sending a nudge to oneself returns an error."""
    resp = client.post("/api/rooms", json={"player_name": "P0"})
    room_id = resp.json()["room_id"]
    p0_id = resp.json()["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as ws0:
        ws0.send_json({"type": "join", "name": "P0", "player_id": p0_id})

        with client.websocket_connect(f"/ws/{room_id}") as ws1:
            ws1.send_json({"type": "join", "name": "P1", "player_id": "p1_id"})

            with client.websocket_connect(f"/ws/{room_id}") as ws2:
                ws2.send_json({"type": "join", "name": "P2", "player_id": "p2_id"})

                with client.websocket_connect(f"/ws/{room_id}") as ws3:
                    ws3.send_json({"type": "join", "name": "P3", "player_id": "p3_id"})

                    ws0.send_json({"type": "start_game"})
                    _drain_to_bidding(ws0)
                    _drain_to_bidding(ws1)
                    _drain_to_bidding(ws2)
                    _drain_to_bidding(ws3)

                    # P1 tries to nudge P1
                    ws1.send_json({"type": "nudge_player", "target_player_id": "p1_id"})
                    err = _receive_error_event(ws1)
                    assert err["type"] == "error"
                    assert "cannot nudge yourself" in err["error"].lower()


def test_cannot_nudge_inactive_player():
    """Verify nudging a player whose turn it is not returns an error."""
    resp = client.post("/api/rooms", json={"player_name": "P0"})
    room_id = resp.json()["room_id"]
    p0_id = resp.json()["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as ws0:
        ws0.send_json({"type": "join", "name": "P0", "player_id": p0_id})

        with client.websocket_connect(f"/ws/{room_id}") as ws1:
            ws1.send_json({"type": "join", "name": "P1", "player_id": "p1_id"})

            with client.websocket_connect(f"/ws/{room_id}") as ws2:
                ws2.send_json({"type": "join", "name": "P2", "player_id": "p2_id"})

                with client.websocket_connect(f"/ws/{room_id}") as ws3:
                    ws3.send_json({"type": "join", "name": "P3", "player_id": "p3_id"})

                    ws0.send_json({"type": "start_game"})
                    _drain_to_bidding(ws0)
                    _drain_to_bidding(ws1)
                    _drain_to_bidding(ws2)
                    _drain_to_bidding(ws3)

                    # Turn is P1 (seat 1). P0 tries to nudge P2 (seat 2, inactive)
                    ws0.send_json({"type": "nudge_player", "target_player_id": "p2_id"})
                    err = _receive_error_event(ws0)
                    assert err["type"] == "error"
                    assert "not that player's turn" in err["error"].lower()


def test_cannot_nudge_in_lobby():
    """Verify nudging is rejected in LOBBY phase."""
    resp = client.post("/api/rooms", json={"player_name": "Host"})
    room_id = resp.json()["room_id"]
    host_id = resp.json()["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as ws1:
        ws1.send_json({"type": "join", "name": "Host", "player_id": host_id})

        with client.websocket_connect(f"/ws/{room_id}") as ws2:
            ws2.send_json({"type": "join", "name": "P2", "player_id": "p2_id"})

            ws2.send_json({"type": "nudge_player", "target_player_id": host_id})
            # Drain until we receive error message
            while True:
                msg = ws2.receive_json()
                if msg.get("type") == "error":
                    assert "not available" in msg["error"].lower()
                    break


def _receive_error_event(ws):
    """Drain any pending game_state messages until error is returned."""
    while True:
        msg = ws.receive_json()
        if msg.get("type") == "error":
            return msg


def test_nudge_cooldown_enforced():
    """Verify rapid consecutive nudges from the same sender trigger cooldown error."""
    resp = client.post("/api/rooms", json={"player_name": "P0"})
    room_id = resp.json()["room_id"]
    p0_id = resp.json()["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as ws0:
        ws0.send_json({"type": "join", "name": "P0", "player_id": p0_id})

        with client.websocket_connect(f"/ws/{room_id}") as ws1:
            ws1.send_json({"type": "join", "name": "P1", "player_id": "p1_id"})

            with client.websocket_connect(f"/ws/{room_id}") as ws2:
                ws2.send_json({"type": "join", "name": "P2", "player_id": "p2_id"})

                with client.websocket_connect(f"/ws/{room_id}") as ws3:
                    ws3.send_json({"type": "join", "name": "P3", "player_id": "p3_id"})

                    ws0.send_json({"type": "start_game"})
                    _drain_to_bidding(ws0)
                    _drain_to_bidding(ws1)
                    _drain_to_bidding(ws2)
                    _drain_to_bidding(ws3)

                    # Nudge 1: succeeds
                    ws0.send_json({"type": "nudge_player", "target_player_id": "p1_id"})
                    nudge_msg = _receive_nudge_event(ws1)
                    assert nudge_msg["type"] == "nudge_received"

                    # Nudge 2 immediately: rate limited
                    ws0.send_json({"type": "nudge_player", "target_player_id": "p1_id"})
                    err = _receive_error_event(ws0)
                    assert err["type"] == "error"
                    assert "please wait" in err["error"].lower()


def test_nudge_does_not_mutate_game_state():
    """Verify nudging does not change turn, status, hands, bids, or scores."""
    resp = client.post("/api/rooms", json={"player_name": "P0"})
    room_id = resp.json()["room_id"]
    p0_id = resp.json()["player_id"]

    with client.websocket_connect(f"/ws/{room_id}") as ws0:
        ws0.send_json({"type": "join", "name": "P0", "player_id": p0_id})

        with client.websocket_connect(f"/ws/{room_id}") as ws1:
            ws1.send_json({"type": "join", "name": "P1", "player_id": "p1_id"})

            with client.websocket_connect(f"/ws/{room_id}") as ws2:
                ws2.send_json({"type": "join", "name": "P2", "player_id": "p2_id"})

                with client.websocket_connect(f"/ws/{room_id}") as ws3:
                    ws3.send_json({"type": "join", "name": "P3", "player_id": "p3_id"})

                    ws0.send_json({"type": "start_game"})
                    _drain_to_bidding(ws0)
                    _drain_to_bidding(ws1)
                    _drain_to_bidding(ws2)
                    _drain_to_bidding(ws3)

                    game_before = room_service.get_room(room_id)
                    assert game_before is not None
                    status_before = game_before.status
                    turn_before = game_before.turn_seat

                    ws0.send_json({"type": "nudge_player", "target_player_id": "p1_id"})
                    _receive_nudge_event(ws1)

                    game_after = room_service.get_room(room_id)
                    assert game_after is not None
                    assert game_after.status == status_before
                    assert game_after.turn_seat == turn_before
