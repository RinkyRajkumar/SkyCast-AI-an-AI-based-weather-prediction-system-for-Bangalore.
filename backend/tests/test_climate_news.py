"""Tests for the cached climate and weather news feed."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.climate_news import ClimateNewsError, ClimateNewsService
from backend.app.main import create_app


def rss_feed() -> str:
    """Return a representative RSS feed containing current story metadata."""
    return """<?xml version=\"1.0\"?><rss><channel>
    <item><title>Climate outlook update</title><link>https://example.com/story-one</link><source>Example News</source><pubDate>Fri, 18 Jul 2026 06:00:00 GMT</pubDate></item>
    <item><title>Weather patterns this week</title><link>https://example.com/story-two</link><source>Weather Desk</source><pubDate>Fri, 18 Jul 2026 05:00:00 GMT</pubDate></item>
    </channel></rss>"""


class FakeResponse:
    """Minimal response replacement for RSS requests."""

    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_news_feed_maps_current_headlines(monkeypatch: pytest.MonkeyPatch) -> None:
    """RSS items are converted to safe dashboard articles."""
    monkeypatch.setattr(httpx, "get", lambda *_args, **_kwargs: FakeResponse(rss_feed()))

    response = ClimateNewsService(retries=1).fetch_headlines()

    assert response.source == "Google News RSS"
    assert response.articles[0].title == "Climate outlook update"
    assert response.articles[0].source == "Example News"
    assert response.articles[0].published_at.tzinfo is not None


def test_news_feed_rejects_invalid_or_empty_articles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed feeds and incomplete stories cannot reach the browser."""
    monkeypatch.setattr(httpx, "get", lambda *_args, **_kwargs: FakeResponse("<rss><channel><item><title>Missing fields</title></item></channel></rss>"))

    with pytest.raises(ClimateNewsError, match="usable current headlines"):
        ClimateNewsService(retries=1).fetch_headlines()


def test_news_cache_reuses_a_fresh_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """A page refresh within the cache lifetime does not repeat the RSS request."""
    calls = 0

    def request(*_args: Any, **_kwargs: Any) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(rss_feed())

    monkeypatch.setattr(httpx, "get", request)
    service = ClimateNewsService(retries=1, clock=lambda: 100.0)
    assert len(service.fetch_headlines().articles) == 2
    assert len(service.fetch_headlines().articles) == 2
    assert calls == 1


def test_news_endpoint_returns_injected_service_response() -> None:
    """The API endpoint exposes a valid injected service result."""

    class FakeNewsService:
        def fetch_headlines(self, _location):  # type: ignore[no-untyped-def]
            return ClimateNewsService._parse_feed(rss_feed())

    with TestClient(create_app(climate_news_service=FakeNewsService())) as client:
        response = client.get("/api/climate-news")

    assert response.status_code == 200
    assert response.json()["articles"][0]["source"] == "Example News"
