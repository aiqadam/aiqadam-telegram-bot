"""Tests for ApiClient.get_interests / .toggle_interest (FR-BOT-002 PR 5/6).

Uses httpx.MockTransport, same pattern as test_api_client_leaderboard.py —
asserts the exact request shape (method, path, query/body params, header)
and response parsing, plus the status-code -> exception mapping contract.
"""

from __future__ import annotations

import httpx
import pytest

from src.services.api_client import ApiClient, ApiUnavailableError


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


# ── get_interests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_interests_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        return httpx.Response(200, json={"selected": [], "available": []})

    api_client = _client_for(handler)
    result = await api_client.get_interests(directus_user_id="dir-user-1")

    assert captured["method"] == "GET"
    assert captured["url"] == (
        "https://api.example.com/v1/internal/telegram/interests?directusUserId=dir-user-1"
    )
    # No `country` param — interests are not tenant-scoped.
    assert "country" not in captured["url"]
    assert captured["header"] == "test-token"
    assert result.selected == []
    assert result.available == []
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_interests_parses_selected_and_available() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "selected": ["llm", "ethics"],
                "available": [
                    "llm",
                    "mlops",
                    "computer-vision",
                    "product",
                    "career",
                    "ethics",
                    "infra",
                ],
            },
        )

    api_client = _client_for(handler)
    result = await api_client.get_interests(directus_user_id="dir-user-1")

    assert result.selected == ["llm", "ethics"]
    assert len(result.available) == 7
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_interests_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.get_interests(directus_user_id="dir-user-1")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_get_interests_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.get_interests(directus_user_id="dir-user-1")
    await api_client.aclose()


# ── toggle_interest ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_interest_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        captured["json"] = request.content
        return httpx.Response(200, json={"selected": ["llm"], "available": ["llm"]})

    api_client = _client_for(handler)
    result = await api_client.toggle_interest(directus_user_id="dir-user-1", topic="llm")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/v1/internal/telegram/interests/toggle"
    assert captured["header"] == "test-token"
    assert b'"directusUserId":"dir-user-1"' in captured["json"]
    assert b'"topic":"llm"' in captured["json"]
    assert result.selected == ["llm"]
    await api_client.aclose()


@pytest.mark.asyncio
async def test_toggle_interest_parses_post_toggle_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"selected": [], "available": ["llm", "mlops"]})

    api_client = _client_for(handler)
    result = await api_client.toggle_interest(directus_user_id="dir-user-1", topic="llm")

    assert result.selected == []
    assert result.available == ["llm", "mlops"]
    await api_client.aclose()


@pytest.mark.asyncio
async def test_toggle_interest_raises_unavailable_on_400() -> None:
    # An out-of-list topic would 400 (AC-11) — the bot only ever sends
    # slugs it rendered from its own keyboard, so this maps to the same
    # generic ApiUnavailableError path as any other non-2xx, no dedicated
    # exception type needed.
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.toggle_interest(directus_user_id="dir-user-1", topic="not-a-real-topic")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_toggle_interest_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.toggle_interest(directus_user_id="dir-user-1", topic="llm")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_toggle_interest_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.toggle_interest(directus_user_id="dir-user-1", topic="llm")
    await api_client.aclose()
