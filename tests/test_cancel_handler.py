"""Tests for the /cancel <N> command handler (FR-BOT-002 PR 2/6)."""

from __future__ import annotations

import httpx
import pytest
from aiogram.filters import CommandObject

from src.handlers.cancel import handle_cancel_command
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient
from tests.conftest import make_message_update, mock_answer


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


def _known_user_context(
    *, directus_user_id: str | None = "dir-user-1", country: str | None = "uz"
) -> UserContext:
    return UserContext(
        telegram_id="12345",
        is_known=True,
        directus_user_id=directus_user_id,
        is_temp=False,
        country=country,
    )


@pytest.mark.asyncio
async def test_cancel_shows_usage_message_when_no_argument_given() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without an event id argument")

    api_client = _client_for(handler)
    update = make_message_update(text="/cancel")
    command = CommandObject(command="cancel", args=None)

    with mock_answer(update.message) as answer:
        await handle_cancel_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("cancel.usage")
    await api_client.aclose()


# ── AC-3: /cancel 5 cancels the registration ────────────────────────────


@pytest.mark.asyncio
async def test_cancel_shows_confirmation_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/v1/internal/telegram/register"
        return httpx.Response(200, json={"status": "cancelled"})

    api_client = _client_for(handler)
    update = make_message_update(text="/cancel evt-1")
    command = CommandObject(command="cancel", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_cancel_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("cancel.confirmed")
    await api_client.aclose()


# ── Not-registered edge case (judgement call, not in FR's explicit list) ──


@pytest.mark.asyncio
async def test_cancel_shows_not_registered_message_without_crashing() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "not_registered"})

    api_client = _client_for(handler)
    update = make_message_update(text="/cancel evt-1")
    command = CommandObject(command="cancel", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_cancel_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("cancel.not_registered")
    await api_client.aclose()


# ── Error states ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_shows_not_found_message_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "event_not_found"})

    api_client = _client_for(handler)
    update = make_message_update(text="/cancel missing")
    command = CommandObject(command="cancel", args="missing")

    with mock_answer(update.message) as answer:
        await handle_cancel_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.not_found")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_cancel_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    update = make_message_update(text="/cancel evt-1")
    command = CommandObject(command="cancel", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_cancel_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_cancel_shows_unavailable_message_when_user_context_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved user context")

    api_client = _client_for(handler)
    update = make_message_update(text="/cancel evt-1")
    command = CommandObject(command="cancel", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_cancel_command(update.message, command, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_cancel_shows_events_unavailable_message_when_country_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved country")

    api_client = _client_for(handler)
    update = make_message_update(text="/cancel evt-1")
    command = CommandObject(command="cancel", args="evt-1")
    context = _known_user_context(country=None)

    with mock_answer(update.message) as answer:
        await handle_cancel_command(update.message, command, api_client, context)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("events.unavailable")
    await api_client.aclose()
