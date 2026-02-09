from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def project_root() -> Path:
    # src/utils/env.py -> src/utils -> src -> project root
    return Path(__file__).resolve().parents[2]


def load_env() -> None:
    """
    Load env vars from dotenv file if present.

    - If ENV_FILE is set, we load that path explicitly.
    - Otherwise we call load_dotenv() which searches for a .env file.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    env_file = os.getenv("ENV_FILE")
    if env_file:
        load_dotenv(dotenv_path=env_file, override=False)
        return

    load_dotenv(override=False)


def getenv_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def getenv_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def getenv_str(name: str, default: Optional[str] = None) -> Optional[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw


