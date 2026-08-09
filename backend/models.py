"""
Kadi Teeri Online — Data Models

All Pydantic models for game state, room configuration, players, cards,
and WebSocket message types.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────── Card Constants ────────────────────────────

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["S", "H", "D", "C"]  # Spades, Hearts, Diamonds, Clubs

SUIT_NAMES = {"S": "Spades", "H": "Hearts", "D": "Diamonds", "C": "Clubs"}
SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}

# Removal priority for card balancing (2s removed first)
REMOVAL_PRIORITY_1DECK = [
    ("2", "C"),  # 2♣
    ("2", "D"),  # 2♦
    ("2", "H"),  # 2♥
    ("2", "S"),  # 2♠
]

REMOVAL_PRIORITY_2DECK = [
    # Deck 0
    ("2", "C", 0),
    ("2", "D", 0),
    ("2", "H", 0),
    ("2", "S", 0),
    # Deck 1
    ("2", "C", 1),
    ("2", "D", 1),
    ("2", "H", 1),
    ("2", "S", 1),
]


def rank_index(rank: str) -> int:
    """Return the numerical index of a rank (2=0, 3=1, ..., A=12)."""
    return RANKS.index(rank)


def card_points(rank: str, suit: str) -> int:
    """Return the point value of a card."""
    if rank == "3" and suit == "S":
        return 30
    if rank in ("A", "K", "Q", "J", "10"):
        return 10
    if rank == "5":
        return 5
    return 0


# ──────────────────────────── Enums ────────────────────────────


class GameStatus(str, Enum):
    LOBBY = "lobby"
    BIDDING = "bidding"
    TRUMP = "trump"
    BHERU = "bheru"
    PLAYING = "playing"
    ROUND_END = "round_end"


class BheruCallMode(str, Enum):
    """How a bheru card is called (relevant for 2-deck games)."""
    SIMPLE = "simple"   # 1-deck: just name the card
    FIX = "fix"         # 2-deck: "I have one, I want the other"
    BOTH = "both"       # 2-deck: "I want both copies"
    SECOND = "second"   # 2-deck: "I want whoever plays it second"


# ──────────────────────────── Card ────────────────────────────


class Card(BaseModel):
    rank: str
    suit: str
    deck_index: int = 0  # 0 or 1, used for 2-deck disambiguation

    def label(self) -> str:
        return f"{self.rank}{SUIT_SYMBOLS.get(self.suit, self.suit)}"

    def points(self) -> int:
        return card_points(self.rank, self.suit)

    def same_face(self, other: "Card") -> bool:
        """Same rank and suit (ignoring deck_index)."""
        return self.rank == other.rank and self.suit == other.suit

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit and self.deck_index == other.deck_index

    def __hash__(self):
        return hash((self.rank, self.suit, self.deck_index))


# ──────────────────────────── Player ────────────────────────────


class Player(BaseModel):
    id: str
    name: str
    seat: int
    is_host: bool = False
    is_connected: bool = True


# ──────────────────────────── Bheru Call ────────────────────────────


class BheruCall(BaseModel):
    """A single bheru card call by the bidder."""
    rank: str
    suit: str
    mode: BheruCallMode = BheruCallMode.SIMPLE


# ──────────────────────────── Room Config ────────────────────────────


class RoomConfig(BaseModel):
    player_count: int = Field(default=4, ge=4, le=8)
    deck_count: int = Field(default=1, ge=1, le=2)


# ──────────────────────────── Bidding State ────────────────────────────


class BidEntry(BaseModel):
    seat: int
    action: str  # "bid" or "pass"
    amount: Optional[int] = None


class BiddingState(BaseModel):
    highest_bid: int = 0
    highest_bidder_seat: Optional[int] = None
    passed: list[bool] = []  # one per player
    history: list[BidEntry] = []


# ──────────────────────────── Trick State ────────────────────────────


class TrickPlay(BaseModel):
    seat: int
    card: Card


class TrickState(BaseModel):
    leader_seat: int
    lead_suit: Optional[str] = None
    cards_played: list[TrickPlay] = []


# ──────────────────────────── Bheru Info ────────────────────────────


class BheruInfo(BaseModel):
    """Tracks a bheru relationship."""
    call: BheruCall
    holder_seat: Optional[int] = None  # The actual bheru player's seat
    revealed: bool = False
    # For "second" mode: how many times the card has been played
    play_count: int = 0


# ──────────────────────────── Round Result ────────────────────────────


class RoundResult(BaseModel):
    bidding_points: int
    defending_points: int
    bidding_won: bool
    bidding_seats: list[int]  # bidder + bherus
    defending_seats: list[int]
    target: int
    per_seat: dict[int, int]  # seat -> points captured


# ──────────────────────────── Full Game State ────────────────────────────


class GameState(BaseModel):
    status: GameStatus = GameStatus.LOBBY
    config: RoomConfig = Field(default_factory=RoomConfig)
    players: list[Player] = []
    dealer: int = 0
    turn_seat: Optional[int] = None

    # Bidding
    bidding: Optional[BiddingState] = None
    trump_suit: Optional[str] = None
    bid_target: Optional[int] = None
    bidder_seat: Optional[int] = None

    # Bheru
    bheru_calls: list[BheruCall] = []
    bherus: list[BheruInfo] = []
    is_solo: bool = False

    # Playing
    hands: dict[int, list[Card]] = {}  # seat -> cards (server-only, never sent to other players)
    trick: Optional[TrickState] = None
    trick_number: int = 0
    captured: dict[int, list[Card]] = {}  # seat -> captured cards

    # Results
    round_result: Optional[RoundResult] = None
    rounds_played: int = 0
    wins: dict[str, int] = {}  # player_id -> win count

    # Log
    log: list[str] = []


# ──────────────────────────── WebSocket Messages ────────────────────────────


class ClientMessage(BaseModel):
    """Message from client to server."""
    type: str
    # Optional payloads depending on type:
    name: Optional[str] = None
    player_count: Optional[int] = None
    deck_count: Optional[int] = None
    amount: Optional[int] = None
    suit: Optional[str] = None
    rank: Optional[str] = None
    deck_index: Optional[int] = None
    calls: Optional[list[BheruCall]] = None


class ServerMessage(BaseModel):
    """Message from server to client."""
    type: str
    # Various payloads
    room_id: Optional[str] = None
    player_id: Optional[str] = None
    players: Optional[list[Player]] = None
    config: Optional[RoomConfig] = None
    status: Optional[str] = None
    game: Optional[dict] = None  # Sanitized game state (no other players' hands)
    hand: Optional[list[Card]] = None
    message: Optional[str] = None
    error: Optional[str] = None
    is_host: Optional[bool] = None
    seat: Optional[int] = None
