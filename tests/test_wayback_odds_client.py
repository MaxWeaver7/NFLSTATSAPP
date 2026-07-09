from __future__ import annotations

"""No-network tests for the Wayback harness: CDX paging, backoff, replay."""

import json
from typing import Any, Optional

import pytest

from src.ingestion.wayback_odds_client import (
    RateLimiter,
    Snapshot,
    WaybackClient,
    WaybackError,
)


class FakeResp:
    def __init__(self, status: int, body: Any = "", headers: Optional[dict] = None):
        self.status_code = status
        self._body = body
        self.headers = headers or {}

    @property
    def text(self) -> str:
        return self._body if isinstance(self._body, str) else json.dumps(self._body)

    def json(self) -> Any:
        return self._body if not isinstance(self._body, str) else json.loads(self._body)


class FakeSession:
    """Returns queued responses in order; records every call."""

    def __init__(self, responses: list[FakeResp]):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params})
        if not self._responses:
            raise AssertionError(f"unexpected extra GET {url}")
        return self._responses.pop(0)


def _client(session: FakeSession) -> tuple[WaybackClient, list[float]]:
    slept: list[float] = []
    c = WaybackClient(
        session=session,  # type: ignore[arg-type]
        sleep_fn=slept.append,
        min_interval_seconds=0.0,
    )
    return c, slept


HEADER = ["urlkey", "timestamp", "original", "mimetype", "statuscode", "digest", "length"]


def test_enumerate_single_page_strips_header():
    rows = [
        HEADER,
        ["com,x)/a", "20200101", "http://x.com/a", "text/html", "200", "D1", "10"],
        ["com,x)/b", "20200102", "http://x.com/b", "text/html", "200", "D2", "12"],
    ]
    session = FakeSession([FakeResp(200, rows)])
    client, _ = _client(session)

    snaps = list(client.enumerate("x.com", collapse=None))

    assert [s.original for s in snaps] == ["http://x.com/a", "http://x.com/b"]
    assert snaps[0].timestamp == "20200101"


def test_enumerate_follows_resume_key_across_pages():
    page1 = [
        HEADER,
        ["com,x)/a", "20200101", "http://x.com/a", "text/html", "200", "D1", "10"],
        [],
        ["com,x)/resumetoken"],  # resume key trailer
    ]
    page2 = [
        HEADER,
        ["com,x)/b", "20200102", "http://x.com/b", "text/html", "200", "D2", "12"],
    ]
    session = FakeSession([FakeResp(200, page1), FakeResp(200, page2)])
    client, _ = _client(session)

    snaps = list(client.enumerate("x.com", collapse=None))

    assert [s.original for s in snaps] == ["http://x.com/a", "http://x.com/b"]
    # second call must have carried the resumeKey
    assert session.calls[1]["params"]["resumeKey"] == "com,x)/resumetoken"


def test_get_retries_on_429_then_succeeds_and_honours_retry_after():
    session = FakeSession(
        [
            FakeResp(429, "", {"Retry-After": "7"}),
            FakeResp(200, [HEADER]),
        ]
    )
    client, slept = _client(session)

    list(client.enumerate("x.com"))

    assert 7.0 in slept  # Retry-After was honoured


def test_get_raises_after_exhausting_retries():
    session = FakeSession([FakeResp(429) for _ in range(10)])
    client, _ = _client(session)
    client.max_retries = 2

    with pytest.raises(WaybackError):
        list(client.enumerate("x.com"))


def test_fetch_raw_uses_id_replay_url():
    snap = Snapshot("com,x)/a", "20200101", "http://x.com/a", "text/html", "200", "D1")
    assert snap.replay_url == "https://web.archive.org/web/20200101id_/http://x.com/a"

    session = FakeSession([FakeResp(200, "<html>7/1</html>")])
    client, _ = _client(session)
    assert client.fetch_raw(snap) == "<html>7/1</html>"
    assert session.calls[0]["url"] == snap.replay_url


def test_scrape_skips_bad_parser_and_nonzero_status():
    good = Snapshot("com,x)/a", "1", "http://x.com/a", "text/html", "200", "D1")

    def parser(body: str, snap: Snapshot):
        if "boom" in body:
            raise ValueError("bad page")
        return [{"ok": body}]

    # first capture parses fine, second raises in parser (skipped), third is 404 (skipped)
    rows = [
        HEADER,
        ["com,x)/a", "1", "http://x.com/a", "text/html", "200", "D1", "1"],
        ["com,x)/b", "2", "http://x.com/b", "text/html", "200", "D2", "1"],
        ["com,x)/c", "3", "http://x.com/c", "text/html", "404", "D3", "1"],
    ]
    session = FakeSession(
        [
            FakeResp(200, rows),          # enumerate
            FakeResp(200, "clean"),       # replay a
            FakeResp(200, "boom"),        # replay b -> parser raises -> skipped
        ]
    )
    client, _ = _client(session)

    out = list(client.scrape("x.com", parser, collapse=None))
    assert out == [[{"ok": "clean"}]]


def test_rate_limiter_waits_between_calls():
    slept: list[float] = []
    rl = RateLimiter(min_interval_seconds=2.0, _sleep=slept.append)
    rl.wait()  # first call primes, no sleep
    rl.wait()  # second call should request a wait
    assert slept and slept[0] > 0
