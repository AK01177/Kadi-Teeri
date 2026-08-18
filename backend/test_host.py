from models import GameState, Player, GameStatus, RoomConfig
import room_manager
rm = room_manager.RoomManager()

game = GameState(status=GameStatus.LOBBY, config=RoomConfig(), players=[
    Player(id="1", name="A", seat=0, is_host=True, is_connected=False),
    Player(id="2", name="B", seat=1, is_host=False, is_connected=True)
])
rm._ensure_host(game)
print("Host A:", game.players[0].is_host)
print("Host B:", game.players[1].is_host)
