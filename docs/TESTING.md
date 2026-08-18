# Testing Guide

This document describes the testing structure, execution instructions, and test coverage strategy for **Kadi Teeri Online**.

## 1. Overview

The codebase includes automated tests for both backend game engine logic and frontend UI/store components.

```
tests/
├── backend/
│   ├── test_game_engine.py       # Core rules, bidding, card rank, 2-deck duplicates
│   ├── test_bheru_calls.py       # Partner call validation, mode checking
│   ├── test_remove_player_bug.py # Disconnect, kick player, room reset safety
│   └── test_ws_api.py            # REST endpoints, room creation, WebSocket lifecycle
└── frontend/
    └── src/store/gameStore.test.ts # Zustand state store mutations and state handling
```

## 2. Running Backend Tests

Backend tests are written using `pytest` and `httpx`.

```bash
# Using uv (recommended)
uv run pytest backend/tests

# Verbose output
uv run pytest backend/tests -v
```

## 3. Running Frontend Tests

Frontend tests are written using `vitest`.

```bash
cd frontend

# Run unit tests
npm test

# Run vitest in watch mode
npx vitest
```

## 4. Test Coverage Areas

Key scenarios covered by tests:

1. **Deck Balancing**: Verified removal priority (`2♣`, `2♦`, `2♥`, `2♠`) for 1-deck and 2-deck configurations across player counts (4 to 12).
2. **Bidding Logic**: Order of bidding, turn rotation, pass logic, minimum bid enforcement (150 minimum, step of 5), and single remaining bidder win conditions.
3. **2-Deck Duplicate Rule**: Verification that when two identical highest cards (e.g. two Aces of Spades) are played in a trick, the card played **later** in order wins the trick.
4. **Bheru Calls**: Mode validation (`SIMPLE`, `FIX`, `BOTH`, `SECOND`), duplicate call prevention, and reveal triggers.
5. **WebSocket & REST APIs**: Room creation HTTP response, room lookup, WebSocket `join`/`welcome`/`game_state` frames, and disconnect handling.
