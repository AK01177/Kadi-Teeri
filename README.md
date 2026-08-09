# Kadi Teeri Online

A real-time, multiplayer web application for playing the Indian trick-taking card game Kadi Teeri. The application features room-based matchmaking, real-time synchronized game state via WebSockets, and automatic reconnect handling.

## Overview

Kadi Teeri Online allows up to four players to create or join private rooms to play Kadi Teeri with their friends. It fully implements the game's core rules, including bidding, trump selection, partner (Bheru) calling, and trick-taking validation.

## Features

- **Room-Based Matchmaking:** Create a private room and share the 6-character room code.
- **Real-Time Gameplay:** Synchronized game state across all clients with minimal latency using WebSockets.
- **Resilient Connections:** Seamless reconnection handling that restores a player's hand and game state if they disconnect.
- **Full Game Logic Enforcement:** Server-side validation of bids, trump selection, Bheru calls, and card plays.
- **Responsive UI:** A dynamic frontend providing a unified experience across the Lobby, Bidding, Trump Selection, Bheru Selection, and Playing phases.

## Tech Stack

| Layer          | Technology       | Purpose                       |
| -------------- | ---------------- | ----------------------------- |
| **Frontend**   | React 19 / Vite  | User Interface                |
| **State**      | Zustand          | Client-side State Management  |
| **Backend**    | FastAPI          | REST API & WebSocket Server   |
| **Validation** | Pydantic         | Data parsing and validation   |
| **Networking** | WebSockets       | Real-time bi-directional sync |

## Architecture

```mermaid
flowchart LR
    User -->|HTTP / WS| Frontend[React SPA]
    Frontend -->|POST /api/rooms| API[FastAPI REST]
    Frontend -->|WS /ws/{room_id}| WS[FastAPI WebSocket]
    WS --> GameEngine[In-Memory Game Engine]
    API --> RoomManager[In-Memory Room Manager]
    GameEngine -.-> RoomManager
```

## Project Structure

```text
Kadi teeri/
├── backend/
│   ├── main.py            # FastAPI entry point & WS routing
│   ├── game_engine.py     # Core Kadi Teeri rules and mechanics
│   ├── room_manager.py    # Room lifecycle and player sessions
│   ├── ws_manager.py      # WebSocket connection management
│   ├── models.py          # Pydantic schemas and game models
│   ├── tests/             # Backend tests
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/         # UI for different game phases
    │   ├── components/    # Reusable UI components
    │   ├── store/         # Zustand game store
    │   ├── hooks/         # Custom hooks (e.g., useWebSocket)
    │   ├── types/         # TypeScript definitions
    │   └── App.tsx        # Main application router
    ├── package.json
    └── vite.config.ts
```

## Prerequisites

- **Node.js** (v18+)
- **Python** (3.10+)

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd "Kadi teeri"
```

### 2. Start the Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
pip install -r requirements.txt

# Start the server (runs on port 8000 by default)
python main.py
```

### 3. Start the Frontend
```bash
cd ../frontend
npm install

# Start the development server
npm run dev
```

## Environment Variables

The backend relies on defaults and does not require a `.env` file for local development.
For the frontend, you can optionally configure connection URLs if hosting the backend elsewhere.

### Frontend

| Variable         | Required | Description                                                  |
| ---------------- | :------: | ------------------------------------------------------------ |
| `VITE_API_URL`   |    No    | REST API base URL (Default: `http://<hostname>:8000`)        |
| `VITE_WS_URL`    |    No    | WebSocket base URL (Default: `ws://<hostname>:8000`)         |

## Usage

1. Start both the backend and frontend servers.
2. Open the frontend URL (e.g., `http://localhost:5173`) in your browser.
3. **Player 1**: Enter a name and click **Create Room**. A unique 6-character room code will be generated.
4. **Players 2–4**: Open the same URL in different browsers/incognito windows, enter a name, provide the room code, and click **Join Room**.
5. Once 4 players have joined, the host can start the game.

## API Documentation

### REST Endpoints

| Method | Endpoint               | Description                                | Auth |
| ------ | ---------------------- | ------------------------------------------ | ---- |
| `GET`  | `/api/health`          | Health check endpoint                      | No   |
| `POST` | `/api/rooms`           | Creates a new game room                    | No   |
| `GET`  | `/api/rooms/{room_id}` | Retrieves lobby status and player count    | No   |

### WebSocket

| Endpoint          | Description                                  |
| ----------------- | -------------------------------------------- |
| `/ws/{room_id}`   | Real-time connection for game state syncing  |

## Database

This project currently operates entirely **in-memory**. There is no persistent database. Game rooms and active sessions are stored in memory (`room_manager.py`), making it highly responsive but ephemeral.

## Testing

Backend unit tests are written using `pytest`.

```bash
cd backend
pytest
```

Frontend testing is configured using `vitest`, though testing coverage is currently limited.

## Development

The frontend uses `oxlint` for linting and Vite for hot module replacement.

```bash
cd frontend
npm run lint
npm run build
```

## Limitations

- **In-Memory State**: Because game state is held in memory, restarting the backend server will immediately destroy all active rooms and disconnect all players.
- **Single-Instance Architecture**: The current WebSocket and room management implementation is designed for a single server instance. It cannot be horizontally scaled without introducing a Pub/Sub layer (like Redis) and a persistent state store.
- **Authentication**: There is no formal user authentication; sessions are tied to randomly generated UUIDs saved in browser `localStorage`.
