-- Add ATS columns to nfl_team_standings for Teams page
ALTER TABLE public.nfl_team_standings 
ADD COLUMN IF NOT EXISTS ats_wins integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS ats_losses integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS ats_pushes integer DEFAULT 0;
