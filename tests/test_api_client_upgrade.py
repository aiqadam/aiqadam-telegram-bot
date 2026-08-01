"""Tests for ApiClient.request_upgrade (FR-BOT-002 PR 6/6, FR-AUTH-006).

Uses httpx.MockTransport, same pattern as test_api_client_register.py —
asserts the exact request shape (method, path, body, header) and the
status-code -> exception mapping contract handlers/upgrade.py depends on.
"""

from __future__ import annotations

import httpx
import pytest

from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    EmailAlreadyInUseError,
    NotATempAccountError,
    TelegramUserNotFoundError,
)


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


@pytest.mark.asyncio
async def test_request_upgrade_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"ok": True})

    api_client = _client_for(handler)
    await api_client.request_upgrade(telegram_id="12345", email="user@example.com")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/v1/internal/telegram/upgrade-temp"
    assert captured["header"] == "test-token"
    assert '"telegramId":"12345"' in captured["body"]
    assert '"email":"user@example.com"' in captured["body"]
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_upgrade_succeeds_silently_on_200() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    api_client = _client_for(handler)
    # No exception, no return value worth asserting on — success is
    # "did not raise."
    result = await api_client.request_upgrade(telegram_id="12345", email="user@example.com")
    assert result is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_upgrade_raises_telegram_user_not_found_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "telegram_user_not_found"})

    api_client = _client_for(handler)
    with pytest.raises(TelegramUserNotFoundError):
        await api_client.request_upgrade(telegram_id="unknown", email="user@example.com")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_upgrade_raises_not_a_temp_account_on_409() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "not_a_temp_account"})

    api_client = _client_for(handler)
    with pytest.raises(NotATempAccountError):
        await api_client.request_upgrade(telegram_id="12345", email="user@example.com")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_upgrade_raises_email_already_in_use_on_409() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "email_already_in_use"})

    api_client = _client_for(handler)
    with pytest.raises(EmailAlreadyInUseError):
        await api_client.request_upgrade(telegram_id="12345", email="taken@example.com")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_upgrade_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.request_upgrade(telegram_id="12345", email="user@example.com")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_upgrade_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.request_upgrade(telegram_id="12345", email="user@example.com")
    await api_client.aclose()
