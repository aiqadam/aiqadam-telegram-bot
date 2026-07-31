"""Tests for ApiClient.get_leaderboard (FR-BOT-002 PR 4/6).

Uses httpx.MockTransport, same pattern as test_api_client_me.py — asserts
the exact request shape (method, path, query params, header) and response
parsing, plus the status-code -> exception mapping contract.
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
async def test_get_leaderboard_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        return httpx.Response(200, json={"entries": []})

    api_client = _client_for(handler)
    result = await api_client.get_leaderboard(directus_user_id="dir-user-1", country="uz")

    assert captured["method"] == "GET"
    assert captured["url"] == (
        "https://api.example.com/v1/internal/telegram/leaderboard"
        "?directusUserId=dir-user-1&country=uz"
    )
    assert captured["header"] == "test-token"
    assert result.entries == []
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_leaderboard_parses_entries_and_caller_flag() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "entries": [
                    {"displayName": "Alice", "points": 120, "isCaller": False},
                    {"displayName": "Bob", "points": 90, "isCaller": True},
                ]
            },
        )

    api_client = _client_for(handler)
    result = await api_client.get_leaderboard(directus_user_id="dir-user-2", country="uz")

    assert len(result.entries) == 2
    assert result.entries[0].display_name == "Alice"
    assert result.entries[0].points == 120
    assert result.entries[0].is_caller is False
    assert result.entries[1].display_name == "Bob"
    assert result.entries[1].points == 90
    assert result.entries[1].is_caller is True
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_leaderboard_defaults_is_caller_false_when_field_missing() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entries": [{"displayName": "Alice", "points": 5}]})

    api_client = _client_for(handler)
    result = await api_client.get_leaderboard(directus_user_id="dir-user-1", country="uz")

    assert result.entries[0].is_caller is False
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_leaderboard_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.get_leaderboard(directus_user_id="dir-user-1", country="uz")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_leaderboard_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.get_leaderboard(directus_user_id="dir-user-1", country="uz")
    await api_client.aclose()
