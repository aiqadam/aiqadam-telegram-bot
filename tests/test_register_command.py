"""Tests for the /register <N> command handler (FR-BOT-002 PR 2/6).

The Register button callback (handle_register_callback) shares the same
_do_register helper and is covered separately in
test_event_detail_handler.py, alongside /event <N>.
"""

from __future__ import annotations

import httpx
import pytest
from aiogram.filters import CommandObject

from src.handlers.event_detail import handle_register_command
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
async def test_register_shows_usage_message_when_no_argument_given() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without an event id argument")

    api_client = _client_for(handler)
    update = make_message_update(text="/register")
    command = CommandObject(command="register", args=None)

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("register.usage")
    await api_client.aclose()


# ── AC-1: normal registration confirmation with event title ────────────


@pytest.mark.asyncio
async def test_register_shows_confirmation_with_event_title_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/internal/telegram/register"
        return httpx.Response(200, json={"status": "registered", "eventTitle": "Meetup #1"})

    api_client = _client_for(handler)
    update = make_message_update(text="/register evt-1")
    command = CommandObject(command="register", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("register.confirmed").format(title="Meetup #1")
    await api_client.aclose()


# ── AC-2: distinct waitlist confirmation copy ───────────────────────────


@pytest.mark.asyncio
async def test_register_shows_distinct_waitlist_message_when_event_is_full() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "waitlisted", "eventTitle": "Full Meetup"})

    api_client = _client_for(handler)
    update = make_message_update(text="/register evt-2")
    command = CommandObject(command="register", args="evt-2")

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("register.waitlisted").format(title="Full Meetup")
    assert sent_text != t("register.confirmed").format(title="Full Meetup")
    await api_client.aclose()


# ── Idempotency: duplicate register shows the same confirmation, no crash ──


@pytest.mark.asyncio
async def test_register_twice_shows_same_confirmation_both_times() -> None:
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"status": "registered", "eventTitle": "Meetup #1"})

    api_client = _client_for(handler)
    update = make_message_update(text="/register evt-1")
    command = CommandObject(command="register", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, _known_user_context())
        await handle_register_command(update.message, command, api_client, _known_user_context())
        assert answer.call_count == 2
        first_call, second_call = answer.call_args_list
        assert first_call == second_call

    assert call_count == 2
    await api_client.aclose()


# ── Error states ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_shows_not_found_message_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "event_not_found"})

    api_client = _client_for(handler)
    update = make_message_update(text="/register missing")
    command = CommandObject(command="register", args="missing")

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.not_found")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_shows_consent_required_message_on_409_consent_required() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "consent_required"})

    api_client = _client_for(handler)
    update = make_message_update(text="/register evt-1")
    command = CommandObject(command="register", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("register.consent_required")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    update = make_message_update(text="/register evt-1")
    command = CommandObject(command="register", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_shows_unavailable_message_when_user_context_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved user context")

    api_client = _client_for(handler)
    update = make_message_update(text="/register evt-1")
    command = CommandObject(command="register", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_shows_events_unavailable_message_when_country_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved country")

    api_client = _client_for(handler)
    update = make_message_update(text="/register evt-1")
    command = CommandObject(command="register", args="evt-1")
    context = _known_user_context(country=None)

    with mock_answer(update.message) as answer:
        await handle_register_command(update.message, command, api_client, context)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("events.unavailable")
    await api_client.aclose()
