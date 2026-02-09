from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional

import requests


class BallDontLieError(RuntimeError):
    pass


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


@dataclass
class RateLimiter:
    """
    Client-side limiter for GOAT Tier (600 req/min = ~0.1s interval).
    """
    min_interval_seconds: float
    _sleep: Callable[[float], None] = _sleep
    _last_ts: float = 0.0

    def wait(self) -> None:
        now = time.time()
        if self._last_ts <= 0:
            self._last_ts = now
            return
        elapsed = now - self._last_ts
        remaining = self.min_interval_seconds - elapsed
        if remaining > 0:
            self._sleep(remaining)
        self._last_ts = time.time()


class BallDontLieNFLClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.balldontlie.io/nfl/v1",
        session: Optional[requests.Session] = None,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        per_page: int = 100,
        rate_limiter: Optional[RateLimiter] = None,
        sleep_fn: Callable[[float], None] = _sleep,
    ) -> None:
        self._api_key = api_key.strip()
        if not self._api_key:
            raise BallDontLieError("BALLDONTLIE api_key is required")
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._per_page = per_page
        self._sleep = sleep_fn
        # GOAT Tier: 10 req/sec
        self._rl = rate_limiter or RateLimiter(min_interval_seconds=0.11, _sleep=sleep_fn)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._api_key}

    def _request(self, method: str, path: str, *, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        backoff = 0.5
        
        for attempt in range(self._max_retries + 1):
            self._rl.wait()
            try:
                resp = self._session.request(
                    method=method,
                    url=url,
                    headers=self._headers(),
                    params=params,
                    timeout=self._timeout,
                )
            except Exception:
                if attempt >= self._max_retries:
                    raise
                self._sleep(backoff)
                continue

            if resp.status_code == 429:
                self._sleep(float(resp.headers.get("Retry-After", backoff)))
                continue
                
            if not resp.ok:
                raise BallDontLieError(f"HTTP {resp.status_code} for {method} {url}")

            return resp.json()

        raise BallDontLieError(f"Request failed: {method} {url}")

    def paginate(self, path: str, *, params: Optional[dict[str, Any]] = None) -> Iterator[dict[str, Any]]:
        cursor: Optional[int] = None
        while True:
            p = dict(params or {})
            p.setdefault("per_page", self._per_page)
            if cursor is not None:
                p["cursor"] = cursor
            
            payload = self._request("GET", path, params=p)
            data = payload.get("data", [])
            for row in data:
                yield row

            meta = payload.get("meta") or {}
            next_cursor = meta.get("next_cursor")
            if not next_cursor:
                break
            cursor = int(next_cursor)

    # --- Core Endpoints ---
    def list_teams(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/teams")
        return payload.get("data", [])

    def iter_players(self, *, search: Optional[str] = None, team_ids: Optional[list[int]] = None) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {}
        if search:
            params["search"] = search
        if team_ids:
            params["team_ids[]"] = team_ids
        yield from self.paginate("/players", params=params)

    def iter_teams(self) -> Iterator[dict[str, Any]]:
        yield from self.paginate("/teams")

    def iter_games(self, *, seasons: list[int], weeks: Optional[list[int]] = None) -> Iterator[dict[str, Any]]:
        params = {"seasons[]": seasons}
        if weeks:
            params["weeks[]"] = weeks
        yield from self.paginate("/games", params=params)

    # --- Stats & Extras ---
    def iter_team_season_stats(self, *, season: int, team_ids: list[int]) -> Iterator[dict[str, Any]]:
        # team_ids is REQUIRED per API spec
        params: dict[str, Any] = {"season": int(season), "team_ids[]": team_ids}
        yield from self.paginate("/team_season_stats", params=params)

    def iter_team_game_stats(self, *, season: int, team_ids: Optional[list[int]] = None) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"seasons[]": [int(season)]}
        if team_ids:
            params["team_ids[]"] = team_ids
        yield from self.paginate("/team_stats", params=params)
    
    def iter_player_season_stats(self, *, season: int, player_ids: Optional[list[int]] = None) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"season": int(season)}
        if player_ids:
            params["player_ids[]"] = player_ids
        yield from self.paginate("/season_stats", params=params)

    def iter_active_players(self) -> Iterator[dict[str, Any]]:
        yield from self.paginate("/players/active")

    def iter_team_roster(self, *, team_id: int, season: Optional[int] = None) -> Iterator[dict[str, Any]]:
        # This endpoint is NOT paginated cursor-based typically, but let's check doc.
        # "returns JSON structured like this: { data: [...] }" no meta.
        # So it returns list directly.
        url = f"/teams/{team_id}/roster"
        params = {}
        if season:
            params["season"] = season
        
        payload = self._request("GET", url, params=params)
        data = payload.get("data", [])
        yield from data # List of roster objects

    def iter_player_game_stats(self, *, seasons: list[int], player_ids: Optional[list[int]] = None, game_ids: Optional[list[int]] = None) -> Iterator[dict[str, Any]]:
        # /stats endpoint
        params: dict[str, Any] = {"seasons[]": seasons}
        if player_ids:
            params["player_ids[]"] = player_ids
        if game_ids:
            params["game_ids[]"] = game_ids
        yield from self.paginate("/stats", params=params)

    def iter_standings(self, *, season: int) -> Iterator[dict[str, Any]]:
        yield from self.paginate("/standings", params={"season": season})

    def iter_injuries(self, *, team_ids: Optional[list[int]] = None) -> Iterator[dict[str, Any]]:
        params = {}
        if team_ids:
            params["team_ids[]"] = team_ids
        yield from self.paginate("/player_injuries", params=params)

    def iter_betting_odds(self, *, game_ids: list[int]) -> Iterator[dict[str, Any]]:
        yield from self.paginate("/odds", params={"game_ids[]": game_ids})

    def iter_player_props(
        self,
        *,
        game_id: int,
        vendors: Optional[list[str]] = None
    ) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"game_id": game_id}
        if vendors:
            params["vendors[]"] = vendors
        yield from self.paginate("/odds/player_props", params=params)

    # --- Advanced Stats ---
    def iter_advanced_receiving(self, *, season: int, week: Optional[int] = None, postseason: bool = False) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"season": season}
        if postseason:
            params["postseason"] = "true"
        if week is not None:
            params["week"] = week
        yield from self.paginate("/advanced_stats/receiving", params=params)

    def iter_advanced_rushing(self, *, season: int, week: Optional[int] = None, postseason: bool = False) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"season": season}
        if postseason:
            params["postseason"] = "true"
        if week is not None:
            params["week"] = week
        yield from self.paginate("/advanced_stats/rushing", params=params)

    def iter_advanced_passing(self, *, season: int, week: Optional[int] = None, postseason: bool = False) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"season": season}
        if postseason:
            params["postseason"] = "true"
        if week is not None:
            params["week"] = week
        yield from self.paginate("/advanced_stats/passing", params=params)