from __future__ import annotations

"""Tests for the odds persistence sinks."""

import csv
import json

from src.ingestion.odds_sink import FileSink, SupabaseSink, build_sink

ROWS = [
    {"source_url": "u", "event": "E1", "player": "A", "captured": "1", "current_decimal": 8.0},
    {"source_url": "u", "event": "E1", "player": "B", "captured": "1", "current_decimal": 13.0},
]


def test_file_sink_writes_jsonl_and_csv(tmp_path):
    j = tmp_path / "odds.jsonl"
    c = tmp_path / "odds.csv"
    sink = FileSink(str(j), str(c))
    assert sink.write(ROWS) == 2
    sink.close()

    lines = j.read_text().strip().splitlines()
    assert [json.loads(x)["player"] for x in lines] == ["A", "B"]

    with open(c) as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["player"] == "A" and rows[1]["current_decimal"] == "13.0"


def test_file_sink_appends_without_duplicate_header(tmp_path):
    c = tmp_path / "odds.csv"
    s1 = FileSink(str(tmp_path / "o.jsonl"), str(c)); s1.write(ROWS[:1]); s1.close()
    s2 = FileSink(str(tmp_path / "o.jsonl"), str(c)); s2.write(ROWS[1:]); s2.close()
    text = c.read_text()
    assert text.count("player") == 1  # header written exactly once


def test_build_sink_defaults_to_file(tmp_path):
    sink = build_sink(str(tmp_path / "x"))
    assert isinstance(sink, FileSink)
    sink.close()


def test_supabase_sink_upserts_with_conflict_key():
    calls = {}

    class FakeClient:
        def upsert(self, table, rows, *, on_conflict=None):
            calls["table"], calls["rows"], calls["key"] = table, rows, on_conflict
            return len(rows)

    sink = SupabaseSink(FakeClient())
    assert sink.write(ROWS) == 2
    assert calls["table"] == "golf_odds_history"
    assert calls["key"] == "source_url,event,player,captured"
    assert sink.total == 2
