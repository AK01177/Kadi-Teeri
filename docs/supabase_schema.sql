-- Run this in your Supabase SQL Editor to create the necessary table

CREATE TABLE rooms (
    room_code TEXT PRIMARY KEY,
    game_state JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Ensure the API roles have permission to access the table
GRANT ALL ON public.rooms TO anon;
GRANT ALL ON public.rooms TO authenticated;
GRANT ALL ON public.rooms TO service_role;

-- Disable Row Level Security since our backend acts as the sole secure client
ALTER TABLE rooms DISABLE ROW LEVEL SECURITY;
