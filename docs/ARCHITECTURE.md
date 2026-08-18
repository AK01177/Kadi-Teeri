# Architecture Documentation

This document describes the high-level system architecture, component responsibilities, networking protocols, and game lifecycle flow of **Kadi Teeri Online**.

## 1. System Overview

Kadi Teeri Online is built as a single deployable monolithic web application.

```mermaid
flowchart TD
    subgraph Client ["Browser / Frontend"]
        SPA["React SPA (Vite + Zustand)"]
    end

    subgraph Backend ["FastAPI Monolith"]
        SPA_Server["Static File Server (/backend/static)"]
        REST_API["REST Routes (/api/*)"]
        WS_Server["WebSocket Handler (/ws/{room_id})"]
        Room_Mgr["Room Manager (Rooms & Sessions)"]
        Game_Eng["Game Engine (Rules & State)"]
        DB_Layer["Supabase Client (Optional)"]
    end

    SPA -->|HTTP GET /| SPA_Server
    SPA -->|POST /api/rooms| REST_API
    SPA -->|WS /ws/{room_id}| WS_Server
    WS_Server --> Room_Mgr
    REST_API --> Room_Mgr
    Room_Mgr --> Game_Eng
    Room_Mgr -.-> DB_Layer
```

## 2. Component Breakdown

### Backend (`backend/`)
- `main.py`: Application entry point, lifespan, CORS, REST endpoints, WebSocket message loop, static SPA catch-all handler.
- `game_engine.py`: Pure domain logic for card creation, deck balancing, dealing, bidding validation, trump selection, trump challenge duels, bheru calling/reveals, trick validation, winner evaluation, scoring.
- `room_manager.py`: Room lifecycle management (create, join, disconnect, reconnect, host transfer, remove player), cached in-memory with optional Supabase database backing.
- `ws_manager.py`: Active WebSocket connection registry grouped by room ID, broadcasting sanitized state updates and targeted private hand payloads.
- `models.py`: Pydantic data schemas for Cards, Players, Room Configurations, Game State, Bheru Calls, and WebSocket messages.
- `db.py`: Supabase client initialization.

### Frontend (`frontend/`)
- `App.tsx`: Top-level page router based on synchronized `game.status`.
- `pages/`: UI pages corresponding to game status (`HomePage`, `LobbyPage`, `BiddingPage`, `TrumpSelectPage`, `TrumpChallengePage`, `BheruSelectPage`, `PlayingPage`, `RoundEndPage`).
- `components/`: Reusable components including `GameTable3D`, `Card3D`, `Hand`, `PlayerSeat`, `ScoreBar`, `ActivityLog`, `HowToPlayModal`.
- `store/gameStore.ts`: Global state store using Zustand. Handles WebSocket incoming payloads, seat calculation, user action dispatching.
- `hooks/useWebSocket.ts`: Manages WebSocket lifecycle, auto-reconnect, ping/pong latency measurement, state updates.

## 3. Game Flow Lifecycle

```
[ LOBBY ] 
   │
   ▼ (Host starts game)
[ BIDDING ] ────── (Players bid min 150 in increments of 5)
   │
   ▼ (Highest bidder wins)
[ TRUMP SELECT ] ─ (Bidder names trump suit)
   │
   ▼ (10s window for opponents to challenge)
[ TRUMP CHALLENGE ] ─── Challenge Duel? ──► YES ──► Raise/Pass Duel ──► Winner re-picks Trump
   │                                                                           │
   ▼ (No challenge / Duel finished)                                            │
[ BHERU SELECT ] ◄──────────────────────────────────────────────────────────────┘
   │  (Bidder calls secret partner card(s): SIMPLE, FIX, BOTH, SECOND)
   ▼
[ PLAYING ] ────── (Trick-taking round: follow suit, trumping, 2-deck duplicate rule)
   │
   ▼ (All tricks completed)
[ ROUND END ] ──── (Calculate score vs contract target, record wins, offer restart)
```

## 4. WebSocket Protocol

All game actions flow over `/ws/{room_id}`:

### Client -> Server
- `join`: `{ "type": "join", "name": "Alice", "player_id": "optional-uuid" }`
- `rejoin`: `{ "type": "rejoin", "player_id": "uuid", "name": "Alice" }`
- `bid`: `{ "type": "bid", "amount": 160 }`
- `pass`: `{ "type": "pass" }`
- `select_trump`: `{ "type": "select_trump", "suit": "S" }`
- `challenge_accept`: `{ "type": "challenge_accept" }`
- `challenge_bid`: `{ "type": "challenge_bid" }`
- `challenge_pass`: `{ "type": "challenge_pass" }`
- `select_bherus`: `{ "type": "select_bherus", "calls": [...] }`
- `play_card`: `{ "type": "play_card", "rank": "A", "suit": "S", "deck_index": 0 }`
- `restart`: `{ "type": "restart" }`

### Server -> Client
- `welcome`: `{ "type": "welcome", "player_id": "...", "room_id": "...", "seat": 0, "is_host": true }`
- `game_state`: `{ "type": "game_state", "game": { ... sanitized state ... }, "hand": [ ... player's cards ... ] }`
- `trick_winner`: `{ "type": "trick_winner", "name": "Alice", "points": 40 }`
- `error`: `{ "type": "error", "error": "Reason" }`
