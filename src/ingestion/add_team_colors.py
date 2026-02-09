#!/usr/bin/env python3
"""
Add team color columns to nfl_teams table.
This adds primary_color, secondary_color, and logo_url columns needed by the UI.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.supabase_client import SupabaseClient, SupabaseConfig
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Team colors map
TEAM_COLORS = {
    'ARI': ('#C83803', '#000000'),
    'ATL': ('#A71930', '#000000'),
    'BAL': ('#241773', '#000000'),
    'BUF': ('#00338D', '#C60C30'),
    'CAR': ('#0085CA', '#101820'),
    'CHI': ('#C83803', '#0B162A'),
    'CIN': ('#FB4F14', '#000000'),
    'CLE': ('#311D00', '#FF3C00'),
    'DAL': ('#041E42', '#869397'),
    'DEN': ('#FB4F14', '#002244'),
    'DET': ('#0076B6', '#B0B7BC'),
    'GB': ('#203731', '#FFB612'),
    'HOU': ('#03202F', '#A71930'),
    'IND': ('#002C5F', '#A2AAAD'),
    'JAX': ('#006778', '#D7A22A'),
    'KC': ('#E31837', '#FFB81C'),
    'LAC': ('#0080C6', '#FFC20E'),
    'LAR': ('#003594', '#FFA300'),
    'LV': ('#000000', '#A5ACAF'),
    'MIA': ('#008E97', '#FC4C02'),
    'MIN': ('#4F2683', '#FFC62F'),
    'NE': ('#002244', '#C60C30'),
    'NO': ('#D3BC8D', '#101820'),
    'NYG': ('#0B2265', '#A5ACAF'),
    'NYJ': ('#125740', '#000000'),
    'PHI': ('#004C54', '#A5ACAF'),
    'PIT': ('#FFB612', '#101820'),
    'SEA': ('#002244', '#69BE28'),
    'SF': ('#AA0000', '#B3995D'),
    'TB': ('#D50A0A', '#34302B'),
    'TEN': ('#0C2340', '#4B92DB'),
    'WSH': ('#773141', '#FFB612'),
}

def main():
    cfg = SupabaseConfig(
        url=os.getenv("SUPABASE_URL"),
        service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    sb = SupabaseClient(cfg)
    
    logger.info("Fetching all teams...")
    teams = sb.select("nfl_teams", select="id,abbreviation", limit=50)
    
    logger.info(f"Updating {len(teams)} teams with color data...")
    
    for team in teams:
        abbr = team.get("abbreviation")
        team_id = team.get("id")
        
        if abbr in TEAM_COLORS:
            primary, secondary = TEAM_COLORS[abbr]
            
            # Update via PATCH
            try:
                result = sb.update(
                    "nfl_teams",
                    {"primary_color": primary, "secondary_color": secondary},
                    filters={"id": f"eq.{team_id}"}
                )
                logger.info(f"✅ Updated {abbr} with {primary}/{secondary}")
            except Exception as e:
                logger.error(f"Failed to update {abbr}: {e}")
        else:
            logger.warning(f"No colors defined for {abbr}")
    
    logger.info("✅ Team colors updated!")

if __name__ == "__main__":
    main()
