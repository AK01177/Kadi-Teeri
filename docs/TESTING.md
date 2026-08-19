# Testing Strategy & Structure

This document outlines the testing strategy, framework setup, and test suite organization for **Kadi Teeri Online**.

---

## 1. Test Architecture

The repository enforces automated testing across both backend and frontend layers:

```text
backend/tests/
├── unit/                       # Unit tests for pure domain logic
│   ├── test_deck.py            # Deck balancing, shuffling, dealing
│   ├── test_bidding.py         # Bidding turn rotation and validation
│   ├── test_trump.py           # Trump selection and challenge duels
│   ├── test_bheru_calls.py     # Partner call validation and reveal logic
│   └── test_trick.py           # Legal plays and 2-deck duplicate winner resolution
├── integration/                # Integration tests for full flows
│   ├── test_game_mechanics.py  # End-to-end round execution and state transitions
│   ├── test_remove_player_bug.py # Player kick/disconnect logic
│   └── test_ws_api.py          # WebSocket connection, REST endpoints, and messaging
└── conftest.py                 # Shared pytest fixtures

frontend/src/store/
└── gameStore.test.ts          # Vitest unit tests for Zustand state management
```

---

## 2. Running Tests

### Backend Test Suite (Pytest)

Run all backend tests using `uv`:

```bash
uv run pytest backend/tests
```

Run specific test sub-suites:

```bash
# Unit tests only
uv run pytest backend/tests/unit

# Integration tests only
uv run pytest backend/tests/integration
```

### Frontend Test Suite (Vitest)

Run frontend unit tests using Vitest:

```bash
cd frontend
npm test
```

---

## 3. Test Coverage Highlights

- **Deck Balancing**: Validates that cards divide evenly among 4–12 players by removing lowest-ranked 2s first.
- **2-Deck Duplicate Winner Rule**: Guarantees that when identical highest cards are played (e.g. two A♠), the card played **later in time** wins the trick.
- **State Sanitization**: Ensures that private hands and unrevealed bheru partner identities are never exposed in broadcast state payloads.
- **WebSocket Protocol**: Tests multi-client connection handshakes, reconnection, host reassignment, and kick commands.
