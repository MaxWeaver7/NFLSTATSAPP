#!/usr/bin/env python3
"""
Point the generic Wayback harness at ANY archived odds source and stream out
whatever the per-source parser extracts.

The harness (src/ingestion/wayback_odds_client.py) is source-agnostic: CDX
enumeration + raw ``id_`` replay is identical everywhere. Each site only needs a
small parser that turns one captured page's bytes into odds rows. Register a new
source by adding an entry to PARSERS below -- nothing else changes.

Usage:
    python scripts/scrape_wayback_odds.py <source> [url_pattern] [--limit N] [--rate SECONDS]

    # discover how much a domain has archived, without replaying anything
    python scripts/scrape_wayback_odds.py index vegasinsider.com/golf

Examples:
    python scripts/scrape_wayback_odds.py generic vegasinsider.com/golf --limit 20
    python scripts/scrape_wayback_odds.py index  covers.com/sport/golf/odds
"""
from __future__ import annotations

import argparse
import html as ihtml
import json
import re
import sys
from typing import Any

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])

from src.ingestion.odds_sink import build_sink  # noqa: E402
from src.ingestion.wayback_odds_client import Snapshot, WaybackClient  # noqa: E402


# --- per-source parsers -----------------------------------------------------
# A parser is (raw_body, snapshot) -> list[dict]. Keep them defensive: the same
# domain changes layout over the years, so extract loosely and skip what doesn't
# match rather than raising.

_FRACTIONAL = re.compile(r"\b(\d{1,4})\s*/\s*(\d{1,4})\b")
_MONEYLINE = re.compile(r"([+-]\d{3,5})\b")


def parse_generic_html(body: str, snap: Snapshot) -> list[dict[str, Any]]:
    """
    Crude but source-independent: pull any fractional (7/1) or American (+650)
    price tokens out of the captured HTML, tagged with the snapshot's timestamp
    and source URL. A real per-book parser replaces this; it exists to prove the
    replayed bytes actually contain odds before you invest in a precise parser.
    """
    rows: list[dict[str, Any]] = []
    for m in _FRACTIONAL.finditer(body):
        num, den = int(m.group(1)), int(m.group(2))
        if 0 < num <= 2000 and 0 < den <= 2000:
            rows.append({"format": "fractional", "raw": m.group(0),
                         "decimal": round(num / den + 1, 4)})
    for m in _MONEYLINE.finditer(body):
        rows.append({"format": "american", "raw": m.group(1)})
    return [
        {"source_url": snap.original, "captured": snap.timestamp, **r}
        for r in rows
    ]


def parse_json_feed(body: str, snap: Snapshot) -> list[dict[str, Any]]:
    """For sources whose captured URL was itself a JSON odds feed."""
    data = json.loads(body)
    return [{"source_url": snap.original, "captured": snap.timestamp, "payload": data}]


# --- VegasInsider golf futures (confirmed archived back to 2006) -------------

def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", ihtml.unescape(s).replace("\xa0", " ")).strip()


def _frac_to_decimal(tok: str) -> float | None:
    m = re.fullmatch(r"(\d{1,4})\s*/\s*(\d{1,4})", (tok or "").strip())
    if not m:
        return None
    num, den = int(m.group(1)), int(m.group(2))
    return round(num / den + 1, 4) if den else None


_VI_TITLE = re.compile(r"ODDS TO WIN[^<]*", re.I)
_VI_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
_VI_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.I | re.S)


def parse_vegasinsider_futures(body: str, snap: Snapshot) -> list[dict[str, Any]]:
    """
    Precise parser for VegasInsider golf futures pages.

    Layout: an ``ODDS TO WIN THE <event>`` title cell delimits each tournament
    block; inside, rows are ``Name | Open | Current`` with fractional prices.
    Each capture's *Current* column is the price as of ``snap.timestamp`` -- so
    replaying every snapshot of one event reconstructs the line's movement.
    """
    titles = [(m.start(), _clean(m.group(0))) for m in _VI_TITLE.finditer(body)]
    if not titles:
        return []
    bounds = [t[0] for t in titles] + [len(body)]

    rows: list[dict[str, Any]] = []
    for i, (pos, event) in enumerate(titles):
        block = body[pos:bounds[i + 1]]
        for rm in _VI_ROW.finditer(block):
            cells = [_clean(c) for c in _VI_CELL.findall(rm.group(1))]
            if len(cells) < 3:
                continue
            name = cells[0]
            if not name or name.lower() == "name" or "open" in name.lower():
                continue
            open_dec, cur_dec = _frac_to_decimal(cells[1]), _frac_to_decimal(cells[-1])
            if open_dec is None and cur_dec is None:
                continue
            rows.append({
                "source_url": snap.original,
                "captured": snap.timestamp,
                "event": event,
                "player": name,
                "open": cells[1] or None,
                "open_decimal": open_dec,
                "current": cells[-1] or None,
                "current_decimal": cur_dec,
            })
    return rows


PARSERS = {
    "generic": parse_generic_html,
    "json": parse_json_feed,
    "vegasinsider": parse_vegasinsider_futures,
}


def cmd_index(client: WaybackClient, pattern: str, limit: int) -> None:
    """Just enumerate -- show what's archived, replay nothing."""
    n = 0
    for snap in client.enumerate(pattern, match_type="prefix"):
        print(f"{snap.timestamp}  {snap.statuscode:>3}  {snap.original}")
        n += 1
        if limit and n >= limit:
            break
    print(f"\n[{n} distinct captures shown for {pattern!r}]", file=sys.stderr)


def cmd_scrape(client: WaybackClient, source: str, pattern: str, limit: int,
               out: Optional[str]) -> None:
    parser = PARSERS[source]
    sink = build_sink(out) if out else None
    total_rows = n_pages = 0
    try:
        for result in client.scrape(pattern, parser, match_type="prefix"):
            n_pages += 1
            total_rows += len(result)
            if sink:
                sink.write(result)
            else:
                for row in result:
                    print(json.dumps(row))
            if limit and n_pages >= limit:
                break
    finally:
        if sink:
            sink.close()
    dest = f" -> {out}" if out else ""
    print(
        f"\n[{n_pages} captures replayed, {total_rows} odds rows extracted{dest}]",
        file=sys.stderr,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", choices=["index", *PARSERS.keys()],
                    help="'index' to list captures; otherwise a parser name")
    ap.add_argument("url_pattern", help="domain/prefix, e.g. vegasinsider.com/golf")
    ap.add_argument("--limit", type=int, default=0, help="max captures (0 = all)")
    ap.add_argument("--rate", type=float, default=1.0,
                    help="min seconds between requests to archive.org (default 1.0)")
    ap.add_argument("--out", default=None,
                    help="persist rows: a file path (writes .jsonl + .csv) or "
                         "'supabase' (upserts into golf_odds_history). "
                         "Omit to print JSON to stdout.")
    args = ap.parse_args()

    client = WaybackClient(min_interval_seconds=args.rate)
    if args.source == "index":
        cmd_index(client, args.url_pattern, args.limit)
    else:
        cmd_scrape(client, args.source, args.url_pattern, args.limit, args.out)


if __name__ == "__main__":
    main()
