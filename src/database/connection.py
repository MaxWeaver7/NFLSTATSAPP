from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

from src.utils.env import project_root


def resolve_db_path(db_path: Optional[str]) -> Path:
    raw = db_path or os.getenv("NFL_DB_PATH", "data/nfl_data.db")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project_root() / path
    return path.resolve()


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


