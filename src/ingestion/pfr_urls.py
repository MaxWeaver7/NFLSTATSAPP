from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


# Map nflfastR-style team abbreviations to PFR "home team" codes used in boxscore URLs.
# Example: https://www.pro-football-reference.com/boxscores/202409050kan.htm
NFL_TO_PFR_HOME_CODE: dict[str, str] = {
    "ARI": "crd",
    "ATL": "atl",
    "BAL": "rav",
    "BUF": "buf",
    "CAR": "car",
    "CHI": "chi",
    "CIN": "cin",
    "CLE": "cle",
    "DAL": "dal",
    "DEN": "den",
    "DET": "det",
    "GB": "gnb",
    "HOU": "htx",
    "IND": "clt",
    "JAX": "jax",
    "KC": "kan",
    "LV": "rai",
    "LAC": "sdg",
    "LAR": "ram",
    "MIA": "mia",
    "MIN": "min",
    "NE": "nwe",
    "NO": "nor",
    "NYG": "nyg",
    "NYJ": "nyj",
    "PHI": "phi",
    "PIT": "pit",
    "SEA": "sea",
    "SF": "sfo",
    "TB": "tam",
    "TEN": "oti",
    "WAS": "was",
}


@dataclass(frozen=True)
class PfrUrlInfo:
    gameday: date
    home_team: str
    url: str


def build_pfr_boxscore_url(*, gameday_iso: str, home_team: str) -> Optional[PfrUrlInfo]:
    """
    Build a PFR boxscore URL from `games.gameday` (YYYY-MM-DD) and `games.home_team` (NFL abbr).

    Returns None if mapping or date parsing fails.
    """
    if not gameday_iso or not home_team:
        return None
    try:
        y, m, d = (int(x) for x in gameday_iso.split("-"))
        gd = date(y, m, d)
    except Exception:
        return None

    code = NFL_TO_PFR_HOME_CODE.get(home_team.strip().upper())
    if not code:
        return None

    url = f"https://www.pro-football-reference.com/boxscores/{gd:%Y%m%d}{code}.htm"
    return PfrUrlInfo(gameday=gd, home_team=home_team.strip().upper(), url=url)


