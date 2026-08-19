"""
HTTP REST endpoints for room creation and lobby information checks.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.game import GameStatus
from app.services.room_service import room_service

router = APIRouter(tags=["Rooms"])


class CreateRoomRequest(BaseModel):
    """Payload for creating a new room."""

    player_name: str


class CreateRoomResponse(BaseModel):
    """Response returned upon room creation."""

    room_id: str
    player_id: str


class RoomInfoResponse(BaseModel):
    """Room info returned for pre-join lobby check."""

    exists: bool
    status: str | None = None
    player_count: int = 0
    max_players: int = 4
    can_join: bool = False


@router.post("/api/rooms", response_model=CreateRoomResponse)
async def create_room(req: CreateRoomRequest):
    """Create a new room and return unique room ID and host player ID."""
    player_id = str(uuid.uuid4())
    name = req.player_name.strip()[:18]
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")

    room_id, _ = room_service.create_room(player_id, name)
    return CreateRoomResponse(room_id=room_id, player_id=player_id)


@router.get("/api/rooms/{room_id}", response_model=RoomInfoResponse)
async def get_room_info(room_id: str):
    """Inspect basic room info before joining."""
    room_id = room_id.upper()
    game = room_service.get_room(room_id)
    if not game:
        return RoomInfoResponse(exists=False)
    return RoomInfoResponse(
        exists=True,
        status=game.status.value,
        player_count=len(game.players),
        max_players=game.config.player_count,
        can_join=game.status == GameStatus.LOBBY and len(game.players) < game.config.player_count,
    )
