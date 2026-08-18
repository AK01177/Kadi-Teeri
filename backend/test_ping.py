import json
from pydantic import BaseModel
from typing import Optional

class BheruCall(BaseModel):
    rank: str
    suit: str
    mode: str = "simple"

class ClientMessage(BaseModel):
    type: str
    name: Optional[str] = None
    player_id: Optional[str] = None
    target_player_id: Optional[str] = None
    player_count: Optional[int] = None
    deck_count: Optional[int] = None
    amount: Optional[int] = None
    suit: Optional[str] = None
    rank: Optional[str] = None
    deck_index: Optional[int] = None
    calls: Optional[list[BheruCall]] = None
    ping_ms: Optional[int] = None

try:
    msg = ClientMessage.model_validate_json('{"type": "ping"}')
    print("Success:", msg)
except Exception as e:
    print("Error:", e)

