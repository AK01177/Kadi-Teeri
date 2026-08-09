from pydantic import BaseModel, Field
import json

class Card(BaseModel):
    rank: str
    suit: str
    
class GameState(BaseModel):
    captured: dict[int, list[Card]] = Field(default_factory=dict)

game = GameState()
game.captured[0] = [Card(rank="A", suit="H")]
game.captured[1] = [Card(rank="J", suit="S")]

# Serialize
dumped = game.model_dump(mode="json")
print("Dumped:", dumped)

# Deserialize
loaded = GameState.model_validate(dumped)
print("Loaded keys:", loaded.captured.keys())
print("Loaded type of key 0:", type(list(loaded.captured.keys())[0]))
print("Loaded cards:", loaded.captured[0])
