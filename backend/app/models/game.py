"""
Kadi Teeri Online — Data Models & Schemas

All Pydantic models for game state, room configuration, players, cards,
and WebSocket message types.
"""

from __future__ import annotations

from enum import Enum

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
    """Lifecycle phases of a Kadi Teeri game room."""

    LOBBY = "lobby"
    BIDDING = "bidding"
    TRUMP = "trump"
    TRUMP_CHALLENGE = "trump_challenge"
    BHERU = "bheru"
    PLAYING = "playing"
    ROUND_END = "round_end"


class BheruCallMode(str, Enum):
    """How a bheru card is called (relevant for 2-deck games)."""

    SIMPLE = "simple"  # 1-deck: just name the card
    FIX = "fix"  # 2-deck: "I have one, I want the other"
    BOTH = "both"  # 2-deck: "I want both copies"
    SECOND = "second"  # 2-deck: "I want whoever plays it second"


# ──────────────────────────── Card ────────────────────────────


class Card(BaseModel):
    """Represents a playing card with rank, suit, and deck index."""

    rank: str
    suit: str
    deck_index: int = 0  # 0 or 1, used for 2-deck disambiguation

    def label(self) -> str:
        return f"{self.rank}{SUIT_SYMBOLS.get(self.suit, self.suit)}"

    def points(self) -> int:
        return card_points(self.rank, self.suit)

    def same_face(self, other: Card) -> bool:
        """Same rank and suit (ignoring deck_index)."""
        return self.rank == other.rank and self.suit == other.suit

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit and self.deck_index == other.deck_index

    def __hash__(self) -> int:
        return hash((self.rank, self.suit, self.deck_index))


# ──────────────────────────── Player ────────────────────────────


class Player(BaseModel):
    """Represents a connected or disconnected player in a room."""

    id: str
    name: str
    seat: int
    is_host: bool = False
    is_connected: bool = True
    ping_ms: int | None = None


# ──────────────────────────── Bheru Call ────────────────────────────


class BheruCall(BaseModel):
    """A single bheru card call by the bidder."""

    rank: str
    suit: str
    mode: BheruCallMode = BheruCallMode.SIMPLE


# ──────────────────────────── Room Config ────────────────────────────


class RoomConfig(BaseModel):
    """Configuration options for a game room."""

    player_count: int = Field(default=4, ge=4, le=12)
    deck_count: int = Field(default=1, ge=1, le=2)


# ──────────────────────────── Bidding State ────────────────────────────


class BidEntry(BaseModel):
    """Single bid action recorded in bidding history."""

    seat: int
    action: str  # "bid" or "pass"
    amount: int | None = None


class BiddingState(BaseModel):
    """Current progress of the bidding phase."""

    highest_bid: int = 0
    highest_bidder_seat: int | None = None
    passed: list[bool] = Field(default_factory=list)
    history: list[BidEntry] = Field(default_factory=list)


# ──────────────────────────── Trick State ────────────────────────────


class TrickPlay(BaseModel):
    """Single card played by a player during a trick."""

    seat: int
    card: Card


class TrickState(BaseModel):
    """Current state of an active trick."""

    leader_seat: int
    lead_suit: str | None = None
    cards_played: list[TrickPlay] = Field(default_factory=list)


# ──────────────────────────── Bheru Info ────────────────────────────


class BheruInfo(BaseModel):
    """Tracks a bheru partner relationship."""

    call: BheruCall
    holder_seat: int | None = None
    revealed: bool = False
    play_count: int = 0


# ──────────────────────────── Round Result ────────────────────────────


class RoundResult(BaseModel):
    """Final score breakdown for a completed round."""

    bidding_points: int
    defending_points: int
    bidding_won: bool
    bidding_seats: list[int]
    defending_seats: list[int]
    target: int
    per_seat: dict[int, int]


# ──────────────────────────── Full Game State ────────────────────────────


class GameState(BaseModel):
    """Complete state tree for a Kadi Teeri room."""

    status: GameStatus = GameStatus.LOBBY
    config: RoomConfig = Field(default_factory=RoomConfig)
    players: list[Player] = Field(default_factory=list)
    dealer: int = 0
    turn_seat: int | None = None

    # Bidding
    bidding: BiddingState | None = None
    trump_suit: str | None = None
    bid_target: int | None = None
    bidder_seat: int | None = None

    # Trump Challenge
    trump_challenge_used: bool = False
    challenge_deadline: float | None = None
    challenge_duel_seats: list[int] | None = None
    challenger_seat: int | None = None

    # Bheru
    bheru_calls: list[BheruCall] = Field(default_factory=list)
    bherus: list[BheruInfo] = Field(default_factory=list)
    is_solo: bool = False

    # Playing
    hands: dict[int, list[Card]] = Field(default_factory=dict)
    trick: TrickState | None = None
    trick_number: int = 0
    captured: dict[int, list[Card]] = Field(default_factory=dict)

    # Results
    round_result: RoundResult | None = None
    rounds_played: int = 0
    wins: dict[str, int] = Field(default_factory=dict)

    # Log
    log: list[str] = Field(default_factory=list)

    def add_log(self, msg: str):
        """Add a message to the game log, capping at 100 entries to prevent memory leaks."""
        self.log.append(msg)
        if len(self.log) > 100:
            self.log = self.log[-100:]
# ──────────────────────────── WebSocket Messages ────────────────────────────


class ClientMessage(BaseModel):
    """Message sent from client to server."""

    type: str
    # Optional payloads depending on type:
    name: str | None = None
    player_id: str | None = None
    target_player_id: str | None = None
    player_count: int | None = None
    deck_count: int | None = None
    amount: int | None = None
    suit: str | None = None
    rank: str | None = None
    deck_index: int | None = None
    calls: list[BheruCall] | None = None
    ping_ms: int | None = None


class ServerMessage(BaseModel):
    """Message sent from server to client."""

    type: str
    room_id: str | None = None
    player_id: str | None = None
    players: list[Player] | None = None
    config: RoomConfig | None = None
    status: str | None = None
    game: dict | None = None
    hand: list[Card] | None = None
    message: str | None = None
    error: str | None = None
    is_host: bool | None = None
    seat: int | None = None
    ping_ms: int | None = None
    sender_id: str | None = None
    sender_name: str | None = None
