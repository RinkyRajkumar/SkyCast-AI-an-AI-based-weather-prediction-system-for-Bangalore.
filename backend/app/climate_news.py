"""Fetch a small, cached set of current climate and weather headlines."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as element_tree
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import RLock
from typing import Callable
from urllib.parse import quote_plus

import httpx

from backend.app import config
from backend.app.locations import default_location
from backend.app.schemas import ClimateNewsItem, ClimateNewsResponse, WeatherLocation

LOGGER = logging.getLogger(__name__)


class ClimateNewsError(RuntimeError):
    """Raised when a usable climate-news feed cannot be obtained."""


class ClimateNewsService:
    """Provide cached RSS headlines without exposing the upstream feed to the browser."""

    def __init__(
        self,
        *,
        cache_seconds: int = config.CLIMATE_NEWS_CACHE_SECONDS,
        retries: int = config.OPEN_METEO_RETRIES,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.cache_seconds = cache_seconds
        self.retries = retries
        self._clock = clock
        self._sleeper = sleeper
        self._cache: dict[str, tuple[float, ClimateNewsResponse]] = {}
        self._lock = RLock()

    def fetch_headlines(self, location: WeatherLocation | None = None) -> ClimateNewsResponse:
        """Return a fresh or cached set of valid climate and weather headlines."""
        selected_location = location or default_location()
        cache_key = selected_location.label.casefold()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None and self._clock() - cached[0] < self.cache_seconds:
                LOGGER.info("Using cached climate and weather headlines for %s", selected_location.label)
                return cached[1].model_copy(deep=True)

            response = self._parse_feed(self._request_feed(selected_location))
            self._cache[cache_key] = (self._clock(), response)
            return response.model_copy(deep=True)

    def _request_feed(self, location: WeatherLocation) -> str:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = httpx.get(
                    config.CLIMATE_NEWS_RSS_URL.format(
                        query=quote_plus(f"{location.label} climate weather")
                    ),
                    timeout=config.OPEN_METEO_TIMEOUT_SECONDS,
                    headers={"User-Agent": "SkyCast-AI/1.0"},
                )
                response.raise_for_status()
                if not response.text.strip():
                    raise ClimateNewsError("The climate-news feed returned no content.")
                return response.text
            except (httpx.HTTPError, ClimateNewsError) as exc:
                last_error = exc
                LOGGER.warning(
                    "Climate-news request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.retries,
                    exc,
                )
                if attempt < self.retries - 1:
                    self._sleeper(0.5 * (2**attempt))
        raise ClimateNewsError("Unable to fetch current climate and weather news.") from last_error

    @staticmethod
    def _parse_feed(feed: str) -> ClimateNewsResponse:
        try:
            root = element_tree.fromstring(feed)
        except element_tree.ParseError as exc:
            raise ClimateNewsError("The climate-news feed returned invalid data.") from exc

        articles: list[ClimateNewsItem] = []
        for item in root.findall("./channel/item"):
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            source = (item.findtext("source") or "Google News").strip()
            published = (item.findtext("pubDate") or "").strip()
            if not title or not url.startswith(("https://", "http://")) or not published:
                continue
            try:
                published_at = parsedate_to_datetime(published)
            except (TypeError, ValueError):
                continue
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            articles.append(
                ClimateNewsItem(
                    title=title,
                    url=url,
                    source=source,
                    published_at=published_at,
                )
            )
            if len(articles) == config.CLIMATE_NEWS_MAX_ITEMS:
                break

        if not articles:
            raise ClimateNewsError("The climate-news feed did not contain usable current headlines.")
        return ClimateNewsResponse(
            source="Google News RSS",
            fetched_at=datetime.now(timezone.utc),
            articles=articles,
        )
