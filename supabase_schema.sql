-- Run this in your Supabase SQL Editor to create the necessary table

CREATE TABLE rooms (
    room_code TEXT PRIMARY KEY,
    game_state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Optional: Enable Row Level Security (RLS) but allow the backend service key to bypass it
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable all for service role" ON rooms FOR ALL USING (true);
