# Database and State Architecture

This document describes the state management, database schema, and persistence model of **Kadi Teeri Online**.

## 1. Overview

Kadi Teeri Online operates primarily as an **in-memory active state server**, with optional persistent storage provided by **Supabase (PostgreSQL)** when configured.

```
+-------------------------------------------------------------+
|                      FastAPI Backend                        |
|                                                             |
|   +-----------------------+     +-----------------------+   |
|   |   In-Memory Cache     |     |   Supabase Client     |   |
|   |  self._rooms = {...}  | <-> |   table("rooms")      |   |
|   +-----------------------+     +-----------------------+   |
+-------------------------------------------------------------+
                                              |
                                              v
                                   +---------------------+
                                   | Supabase Postgres   |
                                   | rooms (room_code,   |
                                   |        game_state)  |
                                   +---------------------+
```

## 2. In-Memory State Model

Active game state is managed in-memory inside `RoomManager`:
- `_rooms`: Mapping of `room_code` (4-character uppercase string) -> `GameState` Pydantic model.
- `_player_rooms`: Reverse lookup mapping `player_id` (UUID string) -> `room_code`.

If Supabase environment variables (`SUPABASE_URL`, `SUPABASE_KEY`) are missing, the server runs completely in-memory without error.

## 3. Database Schema

When Supabase is enabled, room states are stored in the `rooms` table:

```sql
CREATE TABLE rooms (
    room_code TEXT PRIMARY KEY,
    game_state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

GRANT ALL ON public.rooms TO anon;
GRANT ALL ON public.rooms TO authenticated;
GRANT ALL ON public.rooms TO service_role;

ALTER TABLE rooms DISABLE ROW LEVEL SECURITY;
```

## 4. State Serialization & Deserialization

- **Save**: When game actions occur (`bid`, `select_trump`, `play_card`, etc.), `room_manager.save_room(room_id)` serializes `GameState` using `game.model_dump(mode="json")` and performs an `upsert` on the `rooms` table.
- **Load**: On server startup or cache miss, `GameState.model_validate(row["game_state"])` deserializes the JSONB payload into standard Pydantic models.
- **Sanitization**: Before broadcasting via WebSocket, `sanitize_game_state(game)` strips all opponents' hidden hand data so clients only receive public info and their own hand.
