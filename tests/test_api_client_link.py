"""Tests for ApiClient.request_link_start() and request_link_confirm() (FR-AUTH-005).

Uses httpx.MockTransport — same pattern as test_api_client_upgrade.py.
Asserts request shape (method, path, header, body) and the
status-code → exception mapping that handlers/link.py depends on.
"""

from __future__ import annotations

import httpx
import pytest

from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    LinkAlreadyLinkedOtherError,
    LinkConfirmResult,
    LinkInvalidCodeError,
    LinkMemberNotFoundError,
    LinkRateLimitedError,
    LinkStartResult,
)


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


# ── request_link_start ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_link_start_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        captured["body"] = request.content.decode()
        return httpx.Response(
            200, json={"challenge_id": "ch-001", "sent_to_email_masked": "a***@example.com"}
        )

    api_client = _client_for(handler)
    await api_client.request_link_start(telegram_id="99", email="alice@example.com")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/v1/telegram/link/start"
    assert captured["header"] == "test-token"
    assert '"tg_user_id"' in captured["body"]
    assert '"99"' in captured["body"]
    assert '"alice@example.com"' in captured["body"]
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_start_returns_link_start_result_on_200() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"challenge_id": "ch-abc", "sent_to_email_masked": "a***@example.com"}
        )

    api_client = _client_for(handler)
    result = await api_client.request_link_start(telegram_id="99", email="alice@example.com")

    assert isinstance(result, LinkStartResult)
    assert result.challenge_id == "ch-abc"
    assert result.sent_to_email_masked == "a***@example.com"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_start_raises_rate_limited_on_400_rate_limited() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "rate_limited"})

    api_client = _client_for(handler)
    with pytest.raises(LinkRateLimitedError):
        await api_client.request_link_start(telegram_id="99", email="alice@example.com")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_start_raises_unavailable_on_400_non_rate_limited() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "invalid_request"})

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.request_link_start(telegram_id="99", email="alice@example.com")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_start_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.request_link_start(telegram_id="99", email="alice@example.com")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_start_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.request_link_start(telegram_id="99", email="alice@example.com")
    await api_client.aclose()


# ── request_link_confirm ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_request_link_confirm_sends_expected_request_shape_with_username() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"member_id": "m-1", "tenant": "uz"})

    api_client = _client_for(handler)
    await api_client.request_link_confirm(
        challenge_id="ch-001",
        code="123456",
        telegram_id="99",
        telegram_username="alice_tg",
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/v1/telegram/link/confirm"
    assert captured["header"] == "test-token"
    assert '"ch-001"' in captured["body"]
    assert '"123456"' in captured["body"]
    assert '"99"' in captured["body"]
    assert '"alice_tg"' in captured["body"]
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_confirm_omits_tg_username_field_when_none() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"member_id": "m-1", "tenant": "uz"})

    api_client = _client_for(handler)
    await api_client.request_link_confirm(
        challenge_id="ch-001",
        code="123456",
        telegram_id="99",
        telegram_username=None,
    )

    assert "tg_username" not in captured["body"]
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_confirm_returns_link_confirm_result_on_200() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"member_id": "m-1", "tenant": "uz"})

    api_client = _client_for(handler)
    result = await api_client.request_link_confirm(
        challenge_id="ch-001",
        code="123456",
        telegram_id="99",
        telegram_username=None,
    )

    assert isinstance(result, LinkConfirmResult)
    assert result.member_id == "m-1"
    assert result.tenant == "uz"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_confirm_raises_invalid_code_on_401() -> None:
    # 401 covers both wrong-code and attempt-exhausted; the API returns the
    # same status for both, so both raise LinkInvalidCodeError.
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_code"})

    api_client = _client_for(handler)
    with pytest.raises(LinkInvalidCodeError):
        await api_client.request_link_confirm(
            challenge_id="ch-001", code="000000", telegram_id="99", telegram_username=None
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_confirm_raises_member_not_found_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "member_not_found"})

    api_client = _client_for(handler)
    with pytest.raises(LinkMemberNotFoundError):
        await api_client.request_link_confirm(
            challenge_id="ch-001", code="123456", telegram_id="99", telegram_username=None
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_confirm_raises_already_linked_other_on_409() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "already_linked_to_different_account"})

    api_client = _client_for(handler)
    with pytest.raises(LinkAlreadyLinkedOtherError):
        await api_client.request_link_confirm(
            challenge_id="ch-001", code="123456", telegram_id="99", telegram_username=None
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_confirm_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.request_link_confirm(
            challenge_id="ch-001", code="123456", telegram_id="99", telegram_username=None
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_request_link_confirm_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.request_link_confirm(
            challenge_id="ch-001", code="123456", telegram_id="99", telegram_username=None
        )
    await api_client.aclose()
