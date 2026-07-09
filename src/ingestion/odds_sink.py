from __future__ import annotations

"""
Persistence sinks for scraped odds rows.

Two sinks, same tiny interface (``write(rows) -> int`` + ``close()``):

  - ``FileSink``  -- always works, no creds. Streams JSONL and (optionally) CSV
    to disk. This is the default so a scrape run persists *something* anywhere.
  - ``SupabaseSink`` -- upserts into a Postgres table via the existing
    SupabaseClient, deduping on (source_url, event, player, captured) so re-runs
    are idempotent. Only used when SUPABASE_* env vars are present.

``build_sink()`` picks based on the ``--out`` target and environment.
"""

import csv
import json
import os
from typing import Any, Optional, Protocol

DEFAULT_TABLE = "golf_odds_history"
_CONFLICT_KEY = "source_url,event,player,captured"


class OddsSink(Protocol):
    def write(self, rows: list[dict[str, Any]]) -> int: ...
    def close(self) -> None: ...


class FileSink:
    """Append rows to a JSONL file; mirror to CSV when ``csv_path`` is given."""

    def __init__(self, jsonl_path: str, csv_path: Optional[str] = None) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(jsonl_path)) or ".", exist_ok=True)
        self._jsonl = open(jsonl_path, "a", encoding="utf-8")
        self._csv_path = csv_path
        self._csv_file = None
        self._csv_writer: Optional[csv.DictWriter] = None
        self.total = 0

    def _ensure_csv(self, sample: dict[str, Any]) -> None:
        if self._csv_path and self._csv_writer is None:
            new = not os.path.exists(self._csv_path) or os.path.getsize(self._csv_path) == 0
            self._csv_file = open(self._csv_path, "a", encoding="utf-8", newline="")
            self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=list(sample.keys()))
            if new:
                self._csv_writer.writeheader()

    def write(self, rows: list[dict[str, Any]]) -> int:
        for row in rows:
            self._jsonl.write(json.dumps(row) + "\n")
            if self._csv_path:
                self._ensure_csv(row)
                # tolerate rows with extra keys vs. the header locked in first
                assert self._csv_writer is not None
                self._csv_writer.writerow({k: row.get(k) for k in self._csv_writer.fieldnames})
        self._jsonl.flush()
        if self._csv_file:
            self._csv_file.flush()
        self.total += len(rows)
        return len(rows)

    def close(self) -> None:
        self._jsonl.close()
        if self._csv_file:
            self._csv_file.close()


class SupabaseSink:
    """Idempotent upsert into a Supabase/Postgres table."""

    def __init__(self, client: Any, table: str = DEFAULT_TABLE,
                 on_conflict: str = _CONFLICT_KEY) -> None:
        self._client = client
        self._table = table
        self._on_conflict = on_conflict
        self.total = 0

    def write(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        n = self._client.upsert(self._table, rows, on_conflict=self._on_conflict)
        self.total += n
        return n

    def close(self) -> None:  # nothing to flush
        pass


def build_sink(out: str, *, table: str = DEFAULT_TABLE) -> OddsSink:
    """
    Resolve an ``--out`` value to a sink:

      - ``"supabase"``      -> SupabaseSink (requires SUPABASE_URL + key)
      - ``"path/to.jsonl"`` -> FileSink writing that JSONL + a sibling .csv
    """
    if out == "supabase":
        from src.database.supabase_client import SupabaseClient, SupabaseConfig

        client = SupabaseClient(SupabaseConfig.from_env())
        return SupabaseSink(client, table=table)

    jsonl = out if out.endswith((".jsonl", ".json")) else out + ".jsonl"
    csv_path = jsonl.rsplit(".", 1)[0] + ".csv"
    return FileSink(jsonl, csv_path)
