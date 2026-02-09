-- Add primary key constraint to nfl_betting_odds if not exists
-- This allows upsert operations

-- First check if id is already the primary key
ALTER TABLE public.nfl_betting_odds
  ADD PRIMARY KEY IF NOT EXISTS (id);

-- Alternative: if we want to use game_id + vendor as unique
-- ALTER TABLE public.nfl_betting_odds
--   ADD CONSTRAINT IF NOT EXISTS uq_betting_odds_game_vendor UNIQUE (game_id, vendor);

