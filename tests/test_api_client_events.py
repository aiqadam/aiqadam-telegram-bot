"""Tests for ApiClient.list_events / get_event_detail (FR-BOT-002 PR 1/6).

Uses httpx.MockTransport, same pattern as test_auth_middleware.py's
test_lookup_sends_expected_request_shape — asserts the exact request shape
(method, path, query params, header) and response parsing.
"""

from __future__ import annotations

import httpx
import pytest

from src.services.api_client import ApiClient, ApiUnavailableError, EventNotFoundError


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


# ── list_events ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_events_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "evt-1",
                        "title": "Meetup",
                        "startsAt": "2026-08-15T18:00:00.000Z",
                        "registrationCount": 3,
                    }
                ],
                "offset": 0,
                "limit": 5,
                "total": 1,
            },
        )

    api_client = _client_for(handler)
    result = await api_client.list_events("uz", offset=0, limit=5)

    assert captured["method"] == "GET"
    assert captured["url"].startswith("https://api.example.com/v1/internal/telegram/events?")
    assert "country=uz" in captured["url"]
    assert "offset=0" in captured["url"]
    assert "limit=5" in captured["url"]
    assert captured["header"] == "test-token"
    assert len(result.items) == 1
    assert result.items[0].id == "evt-1"
    assert result.items[0].title == "Meetup"
    assert result.items[0].registration_count == 3
    assert result.total == 1

    await api_client.aclose()


@pytest.mark.asyncio
async def test_list_events_returns_empty_result_without_crashing() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "offset": 0, "limit": 5, "total": 0})

    api_client = _client_for(handler)
    result = await api_client.list_events("kz", offset=0, limit=5)

    assert result.items == []
    assert result.total == 0

    await api_client.aclose()


@pytest.mark.asyncio
async def test_list_events_raises_api_unavailable_on_5xx() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    api_client = _client_for(handler)

    with pytest.raises(ApiUnavailableError):
        await api_client.list_events("uz", offset=0, limit=5)

    await api_client.aclose()


@pytest.mark.asyncio
async def test_list_events_raises_api_unavailable_on_network_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    api_client = _client_for(handler)

    with pytest.raises(ApiUnavailableError):
        await api_client.list_events("uz", offset=0, limit=5)

    await api_client.aclose()


# ── get_event_detail ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_event_detail_sends_expected_request_shape_with_directus_user_id() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        return httpx.Response(
            200,
            json={
                "id": "evt-1",
                "title": "Meetup",
                "startsAt": "2026-08-15T18:00:00.000Z",
                "venue": "Hub",
                "description": "Great talks.",
                "capacity": 50,
                "registrationCount": 10,
                "isRegistered": True,
            },
        )

    api_client = _client_for(handler)
    result = await api_client.get_event_detail("evt-1", directus_user_id="dir-user-1")

    assert captured["method"] == "GET"
    assert captured["url"].startswith("https://api.example.com/v1/internal/telegram/events/evt-1")
    assert "directusUserId=dir-user-1" in captured["url"]
    assert captured["header"] == "test-token"
    assert result.id == "evt-1"
    assert result.venue == "Hub"
    assert result.capacity == 50
    assert result.is_registered is True

    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_event_detail_omits_directus_user_id_query_param_when_none() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "id": "evt-1",
                "title": "Meetup",
                "startsAt": "2026-08-15T18:00:00.000Z",
                "venue": None,
                "description": "Great talks.",
                "capacity": None,
                "registrationCount": 0,
                "isRegistered": False,
            },
        )

    api_client = _client_for(handler)
    result = await api_client.get_event_detail("evt-1", directus_user_id=None)

    assert "directusUserId" not in captured["url"]
    assert result.venue is None
    assert result.capacity is None
    assert result.is_registered is False

    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_event_detail_raises_event_not_found_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "event_not_found"})

    api_client = _client_for(handler)

    with pytest.raises(EventNotFoundError):
        await api_client.get_event_detail("missing-evt")

    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_event_detail_raises_api_unavailable_on_5xx() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)

    with pytest.raises(ApiUnavailableError):
        await api_client.get_event_detail("evt-1")

    await api_client.aclose()
