# Code Rules and Standards

This document establishes the engineering standards, conventions, and practices for the **Kadi Teeri Online** codebase.

## 1. Core Principles

- **Single Source of Truth**: The backend FastAPI server enforces all game rules, state transitions, validation, and scoring. The React frontend is a visual client that renders state received via WebSockets and sends user actions.
- **Immutability & State Sanitization**: Player hands must never be leaked to opponents. The backend sanitizes game state before broadcasting over WebSockets.
- **Zero Breaking Changes**: Preserve existing REST endpoints (`/api/rooms`, `/api/health`, `/api/network-info`) and WebSocket event structures (`/ws/{room_id}`).
- **Deployment Compatibility**: The app must build and run as a single monolithic process on Render.

## 2. Python (Backend) Conventions

- **Tooling**: Managed with `uv`. Format and lint code using `ruff`.
- **Type Annotations**: Use Python 3.10+ type hints (`str | None`, `list[Card]`, `dict[int, list[Card]]`).
- **Pydantic Models**: Data structures use Pydantic `BaseModel` for validation and serialization.
- **Error Handling**: REST endpoints return `HTTPException` with clear error details. WebSocket handlers return standard `{"type": "error", "error": "Reason"}` JSON frames.
- **Logging**: Use standard library `logging` with structured formats. Avoid plain `print()` statements.

## 3. TypeScript & React (Frontend) Conventions

- **Tooling**: Built with Vite, typed with TypeScript, linted with `oxlint`, tested with Vitest.
- **State Management**: Zustand store (`gameStore.ts`) holds synchronized state, local player hand, room info, and connection status.
- **Components**: Functional components separated by game phase (`LobbyPage`, `BiddingPage`, `TrumpSelectPage`, `TrumpChallengePage`, `BheruSelectPage`, `PlayingPage`, `RoundEndPage`).
- **Styling**: Vanilla CSS tokens in `index.css` and `GameTable3D.css` for felt themes, glassmorphism, animations, and responsive cards.

## 4. Git & Commit Guidelines

- **Clean Commit History**: Keep commits focused, logical, and incremental.
- **Commit Messages**: Use conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `build:`).
- **Attribution**: No personal names or AI/agent identity tags in commits, code comments, or documentation.
