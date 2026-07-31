"""Tests for ApiClient.register_for_event / cancel_registration (FR-BOT-002 PR 2/6).

Uses httpx.MockTransport, same pattern as test_api_client_events.py — asserts
the exact request shape (method, path, body, header) and response parsing,
plus the status-code -> exception mapping contract each handler depends on.
"""

from __future__ import annotations

import httpx
import pytest

from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    EventNotFoundError,
    RegistrationConsentRequiredError,
    RegistrationIneligibleError,
)


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


# ── register_for_event ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_for_event_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"status": "registered", "eventTitle": "Meetup #1"})

    api_client = _client_for(handler)
    result = await api_client.register_for_event(
        directus_user_id="dir-user-1", event_id="evt-1", country="uz"
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/v1/internal/telegram/register"
    assert captured["header"] == "test-token"
    assert '"directusUserId":"dir-user-1"' in captured["body"]
    assert '"eventId":"evt-1"' in captured["body"]
    assert '"country":"uz"' in captured["body"]
    assert result.status == "registered"
    assert result.event_title == "Meetup #1"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_for_event_returns_waitlisted_status_faithfully() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "waitlisted", "eventTitle": "Full Meetup"})

    api_client = _client_for(handler)
    result = await api_client.register_for_event(
        directus_user_id="dir-user-1", event_id="evt-2", country="uz"
    )

    assert result.status == "waitlisted"
    assert result.event_title == "Full Meetup"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_for_event_raises_event_not_found_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "event_not_found"})

    api_client = _client_for(handler)
    with pytest.raises(EventNotFoundError):
        await api_client.register_for_event(
            directus_user_id="dir-user-1", event_id="missing", country="uz"
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_for_event_raises_consent_required_on_409_consent_required() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "consent_required"})

    api_client = _client_for(handler)
    with pytest.raises(RegistrationConsentRequiredError):
        await api_client.register_for_event(
            directus_user_id="dir-user-1", event_id="evt-1", country="uz"
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_for_event_raises_ineligible_on_409_other() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "registration_ineligible"})

    api_client = _client_for(handler)
    with pytest.raises(RegistrationIneligibleError):
        await api_client.register_for_event(
            directus_user_id="dir-user-1", event_id="evt-1", country="uz"
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_for_event_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.register_for_event(
            directus_user_id="dir-user-1", event_id="evt-1", country="uz"
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_for_event_raises_unavailable_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.register_for_event(
            directus_user_id="dir-user-1", event_id="evt-1", country="uz"
        )
    await api_client.aclose()


# ── cancel_registration ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_registration_sends_expected_request_shape() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["header"] = request.headers.get("x-internal-auth")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"status": "cancelled"})

    api_client = _client_for(handler)
    result = await api_client.cancel_registration(
        directus_user_id="dir-user-1", event_id="evt-1", country="uz"
    )

    assert captured["method"] == "DELETE"
    assert captured["url"] == "https://api.example.com/v1/internal/telegram/register"
    assert captured["header"] == "test-token"
    assert '"directusUserId":"dir-user-1"' in captured["body"]
    assert result.status == "cancelled"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_cancel_registration_returns_not_registered_status_without_raising() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "not_registered"})

    api_client = _client_for(handler)
    result = await api_client.cancel_registration(
        directus_user_id="dir-user-1", event_id="evt-1", country="uz"
    )

    assert result.status == "not_registered"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_cancel_registration_raises_event_not_found_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "event_not_found"})

    api_client = _client_for(handler)
    with pytest.raises(EventNotFoundError):
        await api_client.cancel_registration(
            directus_user_id="dir-user-1", event_id="missing", country="uz"
        )
    await api_client.aclose()


@pytest.mark.asyncio
async def test_cancel_registration_raises_unavailable_on_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    with pytest.raises(ApiUnavailableError):
        await api_client.cancel_registration(
            directus_user_id="dir-user-1", event_id="evt-1", country="uz"
        )
    await api_client.aclose()
