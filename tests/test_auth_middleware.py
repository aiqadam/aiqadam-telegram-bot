"""Tests for AuthMiddleware (FR-BOT-001 AC-7) and ApiClient's HTTP contract.

Uses httpx.MockTransport so no real network call is made — this asserts
the exact request shape (method, path, header, body) the auth middleware
sends, matching the contract documented in
.copilot/tasks/active/wf-20260731-feat-171/03-code-summary.md.
"""

from __future__ import annotations

import httpx
import pytest

from src.middlewares.auth import AuthMiddleware
from src.services.api_client import ApiClient
from src.services.user_cache import UserCache
from tests.conftest import make_message_update


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


@pytest.mark.asyncio
async def test_lookup_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={"directusUserId": "user-1", "isTemp": False, "country": "uz"},
        )

    api_client = _client_for(handler)
    result = await api_client.lookup_telegram_user("12345")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/v1/internal/telegram/lookup"
    assert captured["header"] == "test-token"
    assert b'"telegramId":"12345"' in captured["body"]
    assert result.directus_user_id == "user-1"
    assert result.is_temp is False
    assert result.country == "uz"

    await api_client.aclose()


@pytest.mark.asyncio
async def test_auth_middleware_attaches_known_user_context() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"directusUserId": "user-42", "isTemp": False, "country": "kz"},
        )

    api_client = _client_for(handler)
    middleware = AuthMiddleware(api_client)

    downstream_data: dict = {}

    async def downstream(_event, data):
        downstream_data.update(data)
        return "ok"

    update = make_message_update(telegram_user_id=42)
    result = await middleware(downstream, update, {})

    assert result == "ok"
    ctx = downstream_data["user_context"]
    assert ctx.is_known is True
    assert ctx.directus_user_id == "user-42"
    assert ctx.country == "kz"

    await api_client.aclose()


@pytest.mark.asyncio
async def test_auth_middleware_lets_update_through_on_404_unknown_user() -> None:
    """New users (no Authentik record yet) must still reach /start (AC-6)."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "telegram_user_not_found"})

    api_client = _client_for(handler)
    middleware = AuthMiddleware(api_client)

    downstream_data: dict = {}

    async def downstream(_event, data):
        downstream_data.update(data)
        return "reached-handler"

    update = make_message_update(telegram_user_id=999)
    result = await middleware(downstream, update, {})

    assert result == "reached-handler"  # NOT hard-blocked
    ctx = downstream_data["user_context"]
    assert ctx.is_known is False
    assert ctx.directus_user_id is None


@pytest.mark.asyncio
async def test_auth_middleware_lets_update_through_when_api_unavailable() -> None:
    """An API outage must not block /start either — degrade, don't block."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    middleware = AuthMiddleware(api_client)

    downstream_data: dict = {}

    async def downstream(_event, data):
        downstream_data.update(data)
        return "reached-handler"

    update = make_message_update(telegram_user_id=7)
    result = await middleware(downstream, update, {})

    assert result == "reached-handler"
    ctx = downstream_data["user_context"]
    assert ctx.is_known is None


@pytest.mark.asyncio
async def test_auth_middleware_calls_lookup_exactly_once_per_update(tmp_path) -> None:
    call_count = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(200, json={"directusUserId": "u", "isTemp": False, "country": None})

    api_client = _client_for(handler)
    cache = UserCache(tmp_path / "cache.sqlite3")
    middleware = AuthMiddleware(api_client, cache)

    async def downstream(_event, _data):
        return "ok"

    update = make_message_update(telegram_user_id=1)
    await middleware(downstream, update, {})

    assert call_count["n"] == 1
    cache.close()
