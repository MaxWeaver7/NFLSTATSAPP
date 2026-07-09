from __future__ import annotations

"""
Generic, source-agnostic Wayback Machine harness for historical odds recovery.

The mechanism (proven, not theoretical):

  1. CDX enumeration -- ``web.archive.org/cdx/search/cdx`` lists *every* URL the
     Internet Archive ever captured for a domain/prefix, with timestamp + digest.
     This is the brute-force index.

  2. Raw replay -- appending ``id_`` to a snapshot
     (``web.archive.org/web/{timestamp}id_/{url}``) returns the *original,
     unmodified* bytes the origin server sent at capture time. You are talking to
     archive.org, so the origin's live anti-bot layer (DataDome, TLS
     fingerprinting, rate-limits) is irrelevant -- it did not exist in the bytes
     and cannot touch you on replay.

The source does not matter: hundreds of sites render golf futures/outright odds
in plain HTML (or fetched JSON) that got captured. You point this at any of them,
supply a small parser for that site's shape, and the enumerate-and-replay loop is
identical.

The one real constraint is that *archive.org itself* rate-limits (HTTP 429 with a
``Retry-After``). This client self-paces: a minimum inter-request interval plus
exponential backoff that honours ``Retry-After``. It throttles rather than evades
-- that is the correct way to be a good citizen of a free public archive.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Optional

import requests

CDX_URL = "https://web.archive.org/cdx/search/cdx"
REPLAY_TMPL = "https://web.archive.org/web/{timestamp}id_/{original}"

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class WaybackError(RuntimeError):
    pass


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


@dataclass
class RateLimiter:
    """Client-side floor on request frequency (mirrors the BallDontLie limiter)."""

    min_interval_seconds: float
    _sleep: Callable[[float], None] = _sleep
    _last_ts: float = 0.0

    def wait(self) -> None:
        now = time.time()
        if self._last_ts <= 0:
            self._last_ts = now
            return
        remaining = self.min_interval_seconds - (now - self._last_ts)
        if remaining > 0:
            self._sleep(remaining)
        self._last_ts = time.time()


@dataclass(frozen=True)
class Snapshot:
    """One captured URL. ``replay_url`` fetches the original unmodified bytes."""

    urlkey: str
    timestamp: str
    original: str
    mimetype: str
    statuscode: str
    digest: str
    length: str = ""

    @property
    def replay_url(self) -> str:
        return REPLAY_TMPL.format(timestamp=self.timestamp, original=self.original)


@dataclass
class WaybackClient:
    """
    Enumerate + replay Wayback captures with archive.org-friendly pacing.

    Every knob has a sane default; ``session`` and ``sleep_fn`` are injectable so
    the paging/backoff logic is unit-testable with zero network.
    """

    min_interval_seconds: float = 1.0  # archive.org is comfortable ~1 req/s
    timeout_seconds: int = 45
    max_retries: int = 5
    user_agent: str = _DEFAULT_UA
    session: requests.Session = field(default_factory=requests.Session)
    sleep_fn: Callable[[float], None] = _sleep
    rate_limiter: Optional[RateLimiter] = None

    def __post_init__(self) -> None:
        if self.rate_limiter is None:
            self.rate_limiter = RateLimiter(
                min_interval_seconds=self.min_interval_seconds, _sleep=self.sleep_fn
            )

    # -- low-level request with 429/5xx-aware backoff -----------------------

    def _get(self, url: str, *, params: Optional[dict[str, Any]] = None) -> requests.Response:
        backoff = 1.0
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            self.rate_limiter.wait()  # type: ignore[union-attr]
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    headers={"User-Agent": self.user_agent},
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:  # network hiccup -> retry
                last_exc = exc
                if attempt >= self.max_retries:
                    raise WaybackError(f"GET {url} failed after retries: {exc}") from exc
                self.sleep_fn(backoff)
                backoff = min(backoff * 2, 60.0)
                continue

            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                # Honour Retry-After when present, else exponential backoff.
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if (retry_after or "").isdigit() else backoff
                if attempt >= self.max_retries:
                    raise WaybackError(
                        f"GET {url} throttled/failed: HTTP {resp.status_code} after "
                        f"{self.max_retries} retries"
                    )
                self.sleep_fn(wait)
                backoff = min(backoff * 2, 60.0)
                continue

            return resp

        raise WaybackError(f"GET {url} exhausted retries: {last_exc}")

    # -- CDX enumeration (paged for large domains) --------------------------

    def enumerate(
        self,
        url_pattern: str,
        *,
        match_type: str = "prefix",
        collapse: Optional[str] = "digest",
        filters: Optional[list[str]] = None,
        from_ts: Optional[str] = None,
        to_ts: Optional[str] = None,
        page_size: int = 5000,
    ) -> Iterator[Snapshot]:
        """
        Yield every capture matching ``url_pattern``.

        Uses CDX resume-key paging so arbitrarily large domains stream without
        blowing memory. ``collapse='digest'`` drops byte-identical re-captures so
        you replay each distinct version of a page exactly once.

        Example patterns:
          - ``"vegasinsider.com/golf"`` with ``match_type='prefix'``
          - ``"example.com/feed/odds.json"`` with ``match_type='exact'``
        """
        params: dict[str, Any] = {
            "url": url_pattern,
            "matchType": match_type,
            "output": "json",
            "limit": page_size,
            "showResumeKey": "true",
        }
        if collapse:
            params["collapse"] = collapse
        if filters:
            params["filter"] = filters  # requests repeats the key for a list
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts

        while True:
            resp = self._get(CDX_URL, params=params)
            rows = resp.json() if resp.text.strip() else []
            if not rows:
                return

            # The resume key (if any) is the last non-empty row, preceded by a
            # blank row. Peel it off before yielding data rows.
            resume_key: Optional[str] = None
            if len(rows) >= 2 and rows[-2] == []:
                resume_key = rows[-1][0]
                rows = rows[:-2]

            # CDX repeats the ``urlkey`` header on every page -- strip it each time.
            start = 1 if (rows and rows[0] and rows[0][0] == "urlkey") else 0

            for row in rows[start:]:
                if not row:
                    continue
                # pad short rows so Snapshot construction never IndexErrors
                cols = (row + [""] * 7)[:7]
                yield Snapshot(*cols)

            if not resume_key:
                return
            params["resumeKey"] = resume_key

    # -- raw replay ---------------------------------------------------------

    def fetch_raw(self, snapshot: Snapshot) -> str:
        """Return the original unmodified response body for a capture."""
        resp = self._get(snapshot.replay_url)
        if resp.status_code != 200:
            raise WaybackError(
                f"replay {snapshot.replay_url} returned HTTP {resp.status_code}"
            )
        return resp.text

    def scrape(
        self,
        url_pattern: str,
        parser: Callable[[str, Snapshot], Any],
        *,
        only_status: str = "200",
        **enumerate_kwargs: Any,
    ) -> Iterator[Any]:
        """
        End-to-end: enumerate captures, replay each, hand the raw body to
        ``parser(body, snapshot)``. Whatever the parser returns (a list of odds
        rows, a dict, ...) is yielded through. Parser exceptions on a single
        snapshot are skipped so one bad capture never kills the run.
        """
        for snap in self.enumerate(url_pattern, **enumerate_kwargs):
            if only_status and snap.statuscode != only_status:
                continue
            try:
                body = self.fetch_raw(snap)
            except WaybackError:
                continue
            try:
                yield parser(body, snap)
            except Exception:  # noqa: BLE001 -- one bad capture must not halt the sweep
                continue
