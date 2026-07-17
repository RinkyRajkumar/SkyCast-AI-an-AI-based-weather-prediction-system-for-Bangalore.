"""Tests for the backend-proxied Open-Meteo location search."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.locations import LocationSearchError, OpenMeteoLocationSearchService
from backend.app.main import create_app
from backend.app.schemas import LocationSearchResponse


class FakeResponse:
    """Minimal HTTP response replacement for geocoding tests."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


def geocoding_payload() -> dict[str, Any]:
    """Return a representative Open-Meteo geocoding payload."""
    return {
        "results": [{
            "name": "London", "latitude": 51.5085, "longitude": -0.1257,
            "country": "United Kingdom", "admin1": "England", "timezone": "Europe/London",
        }]
    }


def test_location_search_returns_valid_places(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *_args, **_kwargs: FakeResponse(geocoding_payload()))
    response = OpenMeteoLocationSearchService(retries=1).search("London")

    assert response.results[0].name == "London"
    assert response.results[0].timezone == "Europe/London"


def test_location_search_reuses_cached_query(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def request(*_args: Any, **_kwargs: Any) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(geocoding_payload())

    monkeypatch.setattr(httpx, "get", request)
    service = OpenMeteoLocationSearchService(retries=1, clock=lambda: 100.0)
    service.search("London")
    service.search("london")
    assert calls == 1


def test_location_search_rejects_short_queries() -> None:
    with pytest.raises(LocationSearchError, match="at least two characters"):
        OpenMeteoLocationSearchService(retries=1).search("x")


def test_location_endpoint_uses_injected_search_service() -> None:
    class FakeLocationService:
        def search(self, query: str):  # type: ignore[no-untyped-def]
            return LocationSearchResponse(
                query=query,
                results=OpenMeteoLocationSearchService._parse_results(geocoding_payload()),
            )

    response = TestClient(create_app(location_search_service=FakeLocationService())).get("/api/locations?query=London")
    assert response.status_code == 200
    assert response.json()["results"][0]["name"] == "London"


def test_invalid_selected_timezone_returns_a_clear_validation_error() -> None:
    response = TestClient(create_app()).get("/api/observations?timezone=Not%2FAZone")
    assert response.status_code == 422
    assert "invalid timezone" in response.json()["detail"]
