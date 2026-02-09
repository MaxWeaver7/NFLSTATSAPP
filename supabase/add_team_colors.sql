-- Add missing UI columns to nfl_teams table
ALTER TABLE nfl_teams ADD COLUMN IF NOT EXISTS primary_color TEXT DEFAULT '#000000';
ALTER TABLE nfl_teams ADD COLUMN IF NOT EXISTS secondary_color TEXT DEFAULT '#FFFFFF';
ALTER TABLE nfl_teams ADD COLUMN IF NOT EXISTS logo_url TEXT;

-- Update with actual NFL team colors (based on abbreviation)
UPDATE nfl_teams SET primary_color = '#C83803', secondary_color = '#000000' WHERE abbreviation = 'ARI';
UPDATE nfl_teams SET primary_color = '#A71930', secondary_color = '#000000' WHERE abbreviation = 'ATL';
UPDATE nfl_teams SET primary_color = '#241773', secondary_color = '#000000' WHERE abbreviation = 'BAL';
UPDATE nfl_teams SET primary_color = '#00338D', secondary_color = '#C60C30' WHERE abbreviation = 'BUF';
UPDATE nfl_teams SET primary_color = '#0085CA', secondary_color = '#101820' WHERE abbreviation = 'CAR';
UPDATE nfl_teams SET primary_color = '#C83803', secondary_color = '#0B162A' WHERE abbreviation = 'CHI';
UPDATE nfl_teams SET primary_color = '#FB4F14', secondary_color = '#000000' WHERE abbreviation = 'CIN';
UPDATE nfl_teams SET primary_color = '#311D00', secondary_color = '#FF3C00' WHERE abbreviation = 'CLE';
UPDATE nfl_teams SET primary_color = '#041E42', secondary_color = '#869397' WHERE abbreviation = 'DAL';
UPDATE nfl_teams SET primary_color = '#FB4F14', secondary_color = '#002244' WHERE abbreviation = 'DEN';
UPDATE nfl_teams SET primary_color = '#0076B6', secondary_color = '#B0B7BC' WHERE abbreviation = 'DET';
UPDATE nfl_teams SET primary_color = '#203731', secondary_color = '#FFB612' WHERE abbreviation = 'GB';
UPDATE nfl_teams SET primary_color = '#03202F', secondary_color = '#A71930' WHERE abbreviation = 'HOU';
UPDATE nfl_teams SET primary_color = '#002C5F', secondary_color = '#A2AAAD' WHERE abbreviation = 'IND';
UPDATE nfl_teams SET primary_color = '#006778', secondary_color = '#D7A22A' WHERE abbreviation = 'JAX';
UPDATE nfl_teams SET primary_color = '#E31837', secondary_color = '#FFB81C' WHERE abbreviation = 'KC';
UPDATE nfl_teams SET primary_color = '#0080C6', secondary_color = '#FFC20E' WHERE abbreviation = 'LAC';
UPDATE nfl_teams SET primary_color = '#003594', secondary_color = '#FFA300' WHERE abbreviation = 'LAR';
UPDATE nfl_teams SET primary_color = '#000000', secondary_color = '#A5ACAF' WHERE abbreviation = 'LV';
UPDATE nfl_teams SET primary_color = '#008E97', secondary_color = '#FC4C02' WHERE abbreviation = 'MIA';
UPDATE nfl_teams SET primary_color = '#4F2683', secondary_color = '#FFC62F' WHERE abbreviation = 'MIN';
UPDATE nfl_teams SET primary_color = '#002244', secondary_color = '#C60C30' WHERE abbreviation = 'NE';
UPDATE nfl_teams SET primary_color = '#D3BC8D', secondary_color = '#101820' WHERE abbreviation = 'NO';
UPDATE nfl_teams SET primary_color = '#0B2265', secondary_color = '#A5ACAF' WHERE abbreviation = 'NYG';
UPDATE nfl_teams SET primary_color = '#125740', secondary_color = '#000000' WHERE abbreviation = 'NYJ';
UPDATE nfl_teams SET primary_color = '#004C54', secondary_color = '#A5ACAF' WHERE abbreviation = 'PHI';
UPDATE nfl_teams SET primary_color = '#FFB612', secondary_color = '#101820' WHERE abbreviation = 'PIT';
UPDATE nfl_teams SET primary_color = '#002244', secondary_color = '#69BE28' WHERE abbreviation = 'SEA';
UPDATE nfl_teams SET primary_color = '#AA0000', secondary_color = '#B3995D' WHERE abbreviation = 'SF';
UPDATE nfl_teams SET primary_color = '#D50A0A', secondary_color = '#34302B' WHERE abbreviation = 'TB';
UPDATE nfl_teams SET primary_color = '#0C2340', secondary_color = '#4B92DB' WHERE abbreviation = 'TEN';
UPDATE nfl_teams SET primary_color = '#773141', secondary_color = '#FFB612' WHERE abbreviation = 'WSH';
