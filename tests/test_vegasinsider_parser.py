from __future__ import annotations

"""Fixture test for the VegasInsider futures parser (no network)."""

import importlib.util
import os

from src.ingestion.wayback_odds_client import Snapshot

# scripts/ isn't a package; load the module by path.
_SPEC = importlib.util.spec_from_file_location(
    "scrape_wayback_odds",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "scrape_wayback_odds.py"),
)
swo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(swo)  # type: ignore[union-attr]


# Minimal reproduction of the real 2006 capture's table shape.
FIXTURE = """
<table><tr class="table_title"><td bgcolor='E7A206'><a name='1637'>&nbsp;</a>
&nbsp;&nbsp;ODDS TO WIN THE 2006 FUNAI CLASSIC</td></tr></table>
<table class='sportPicksBorder'>
<tr class="table_title"><td class="sportPicksBorderL">Name</td>
<td class="sportPicksBorderL">Open</td><td class="sportPicksBorderR">Current</td></tr>
<tr><td class="sportPicksBorderL2">&nbsp;&nbsp;VIJAY SINGH</td>
<td class="sportPicksBorderL2">&nbsp;</td>
<td class="sportPicksBorderR2">&nbsp;7/1</td></tr>
<tr><td class="sportPicksBorderL2">&nbsp;&nbsp;DAVIS LOVE III</td>
<td class="sportPicksBorderL2">&nbsp;10/1</td>
<td class="sportPicksBorderR2">&nbsp;12/1</td></tr>
<tr><td class="sportPicksBorderL2">&nbsp;FIELD (ALL OTHERS)</td>
<td class="sportPicksBorderL2">&nbsp;</td>
<td class="sportPicksBorderR2">&nbsp;</td></tr>
</table>
"""

SNAP = Snapshot("com,vegasinsider)/golf/odds/futures", "20061016184207",
                "http://www.vegasinsider.com/golf/odds/futures/", "text/html", "200", "D1")


def test_parses_players_and_prices():
    rows = swo.parse_vegasinsider_futures(FIXTURE, SNAP)
    players = {r["player"]: r for r in rows}

    assert "VIJAY SINGH" in players
    assert players["VIJAY SINGH"]["current"] == "7/1"
    assert players["VIJAY SINGH"]["current_decimal"] == 8.0

    # open + current both captured when present
    assert players["DAVIS LOVE III"]["open_decimal"] == 11.0
    assert players["DAVIS LOVE III"]["current_decimal"] == 13.0


def test_tags_event_and_capture_date():
    rows = swo.parse_vegasinsider_futures(FIXTURE, SNAP)
    assert rows and all(r["event"] == "ODDS TO WIN THE 2006 FUNAI CLASSIC" for r in rows)
    assert all(r["captured"] == "20061016184207" for r in rows)


def test_skips_rows_without_any_price():
    rows = swo.parse_vegasinsider_futures(FIXTURE, SNAP)
    # FIELD (ALL OTHERS) has no open and no current price -> dropped
    assert not any(r["player"].startswith("FIELD") for r in rows)


def test_empty_when_no_futures_block():
    assert swo.parse_vegasinsider_futures("<html>no odds here</html>", SNAP) == []
