"""Tests for ApiClient.get_me_summary (FR-BOT-002 PR 3/6).

Uses httpx.MockTransport, same pattern as test_api_client_register.py —
asserts the exact request shape (method, path, query params, header) and
response parsing, plus the status-code -> exception mapping contract.
"""

from __future__ import annotations

import httpx
import pytest

from src.services.api_client import ApiClient, ApiUnavailableError


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


@pytest.mark.asyncio
async def test_get_me_summary_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        return httpx.Response(200, json={"registrations": [], "pointsTotal": 0})

    api_client = _client_for(handler)
    result = await api_client.get_me_summary(directus_user_id="dir-user-1", country="uz")

    assert captured["method"] == "GET"
    assert captured["url"] == (
        "https://api.example.com/v1/internal/telegram/me?directusUserId=dir-user-1&country=uz"
    )
    assert captured["header"] == "test-token"
    assert result.registrations == []
    assert result.points_total == 0
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_me_summary_parses_registrations_and_points() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "registrations": [
                    {
                        "id": "reg-1",
                        "status": "registered",
                        "event": {
                            "id": "evt-1",
                            "title": "Meetup #1",
                            "startsAt": "2026-08-15T18:00:00Z",
                            "endsAt": "2026-08-15T20:00:00Z",
                            "location": "Tashkent",
                        },
                    },
                    {
                        "id": "reg-2",
                        "status": "waitlisted",
                        "event": {
                            "id": "evt-2",
                            "title": "Full Meetup",
                            "startsAt": "2026-08-20T18:00:00Z",
                            "endsAt": "2026-08-20T20:00:00Z",
                            "location": None,
                        },
                    },
                ],
                "pointsTotal": 135,
            },
        )

    api_client = _client_for(handler)
    result = await api_client.get_me_summary(directus_user_id="dir-user-1", country="uz")

    assert result.points_total == 135
    assert len(result.registrations) == 2
    assert result.registrations[0].id == "reg-1"
    assert result.registrations[0].status == "registered"
    assert result.registrations[0].event.title == "Meetup #1"
    assert result.registrations[0].event.location == "Tashkent"
    assert result.registrations[1].status == "waitlisted"
    assert result.registrations[1].event.location is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_me_summary_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.get_me_summary(directus_user_id="dir-user-1", country="uz")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_me_summary_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.get_me_summary(directus_user_id="dir-user-1", country="uz")
    await api_client.aclose()
