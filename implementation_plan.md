# Implementation Plan: Professional Structure Cleanup

## Summary of Changes

Three scoped areas of work, **zero internal logic changes**:

1. **Frontend** — Remove all `index.ts` barrel files; flatten single-file features directly into `features/`
2. **Backend** — Reorganise into proper sub-packages; fix redline import errors; add professional comments
3. **Git** — One focused commit per area

---

## 1. Frontend Cleanup

### Remove all `index.ts` barrel files

All 15 barrel files (`features/*/index.ts`, `components/*/index.ts`, `store/index.ts`, `hooks/index.ts`, `types/index.ts`) will be deleted.

### Flatten single-file features into `features/` root

Features with **exactly one file** have no business living in a subfolder:

| Before | After |
|---|---|
| `features/home/HomePage.tsx` | `features/HomePage.tsx` |
| `features/lobby/LobbyPage.tsx` | `features/LobbyPage.tsx` |
| `features/bidding/BiddingPage.tsx` | `features/BiddingPage.tsx` |
| `features/bheru/BheruSelectPage.tsx` | `features/BheruSelectPage.tsx` |
| `features/playing/PlayingPage.tsx` | `features/PlayingPage.tsx` |
| `features/round-end/RoundEndPage.tsx` | `features/RoundEndPage.tsx` |
| `features/trump/TrumpSelectPage.tsx` ✅ | kept — 2 files in one folder |
| `features/trump/TrumpChallengePage.tsx` ✅ | kept |

### Update App.tsx imports
Direct to e.g. `"./features/HomePage"` (no barrel).

---

## 2. Backend Restructure

### Current flat structure (problem)
```
backend/
├── main.py          # 575-line monolith (routes + WS handler)
├── models.py
├── db.py
├── room_manager.py
├── ws_manager.py
├── game_engine.py
└── engine/          # existing sub-package
```

### Proposed professional structure
```
backend/
├── main.py                   # FastAPI app setup only (lifespan, middleware, mounts)
├── api/
│   ├── __init__.py
│   └── routes.py             # All HTTP + WS route handlers (split out of main.py)
├── core/
│   ├── __init__.py
│   ├── room_manager.py       # ← was backend/room_manager.py
│   └── ws_manager.py         # ← was backend/ws_manager.py
├── db/
│   ├── __init__.py
│   └── client.py             # ← was backend/db.py
├── models/
│   ├── __init__.py
│   └── game.py               # ← was backend/models.py
├── engine/                   # existing, unchanged
│   ├── __init__.py
│   ├── bheru.py
│   ├── bidding.py
│   ├── deck.py
│   ├── scoring.py
│   ├── trick.py
│   └── trump.py
├── game_engine.py            # unchanged facade
├── tests/                    # unchanged
├── static/                   # unchanged
└── requirements.txt          # unchanged
```

> [!IMPORTANT]
> `main.py` is 575 lines — it contains both the FastAPI app setup AND all route/WS handlers. Since you said **don't change internal code**, the split of routes into `api/routes.py` means extracting the existing handler functions into that file and importing them back — the handler code itself is **not changed, only moved**.

> [!WARNING]
> All engine sub-modules import `from models import ...`. After moving `models.py → models/game.py`, these will need updating to `from models.game import ...` OR we add a `models/__init__.py` that re-exports everything (backward compatible). I will use the **re-export `__init__.py`** approach so engine files don't need touching.

### Fix Redline Errors
All `# pyrefly: ignore [missing-import]` comments indicate the linter/pyright cannot resolve the third-party packages because there's no type stub or the venv isn't visible. These will be fixed by:
- Adding `py.typed` marker
- Adding `pyrightconfig.json` pointing to `.venv`
- Using `TYPE_CHECKING` guards where appropriate

### Add Professional Comments
Meaningful docstrings and section comments added to:
- `main.py` (app factory, lifespan, middleware setup)
- `api/routes.py` (each endpoint/handler)
- `core/room_manager.py` (class, key methods)
- `core/ws_manager.py` (class, key methods)
- `db/client.py` (connection setup)
- `models/game.py` (model sections)

---

## Verification Plan

```bash
uv run ruff check .                    # 0 errors
uv run pytest backend/tests            # all pass
cd frontend && npx tsc --noEmit        # 0 errors
cd frontend && npm run build           # succeeds
```
