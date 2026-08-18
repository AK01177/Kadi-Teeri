from app.game.bheru import validate_bheru_calls
from app.models.game import BheruCall, BheruCallMode, GameState, GameStatus, Player, RoomConfig


def test_duplicate_bheru_calls():
    game = GameState(
        status=GameStatus.BHERU,
        bidder_seat=0,
        players=[Player(id="1", name="1", seat=0)] * 6,  # 6 players -> max_bherus = 2
        config=RoomConfig(deck_count=1),
    )

    calls = [
        BheruCall(rank="A", suit="S", mode=BheruCallMode.SIMPLE),
        BheruCall(rank="A", suit="S", mode=BheruCallMode.SIMPLE),
    ]
    err = validate_bheru_calls(game, 0, calls)
    assert err is not None, "Duplicate bheru calls should be invalid"
