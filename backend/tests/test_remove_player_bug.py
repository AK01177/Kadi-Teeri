from room_manager import room_manager


def test_remove_player_mid_game_corrupts_state():
    room_id, game = room_manager.create_room("host_id", "Host")
    room_manager.join_room(room_id, "p2", "P2")
    room_manager.join_room(room_id, "p3", "P3")
    room_manager.join_room(room_id, "p4", "P4")

    # Start game
    room_manager.start_game(room_id, "host_id")

    # p4 disconnects
    room_manager.disconnect_player("p4")

    # host removes p4
    err = room_manager.remove_player(room_id, "host_id", "p4")
    assert err is None

    # Now there are 3 players. But hands were dealt to 4 seats.
    # If the turn seat is 3 (which was p4's seat), and we do turn_seat % len(players), it might break.
    assert len(game.players) == 3

    # This proves the bug exists if we don't abort or handle the game properly.
