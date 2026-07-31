"""Tests for the /event <N> handler and its Register placeholder callback
(FR-BOT-002 PR 1/6)."""

from __future__ import annotations

import httpx
import pytest
from aiogram.filters import CommandObject

from src.handlers.event_detail import handle_event_detail, handle_register_placeholder
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient
from tests.conftest import (
    make_callback_query,
    make_message_update,
    mock_answer,
    mock_callback_answer,
)


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


def _detail_response(**overrides) -> dict:
    base = {
        "id": "evt-1",
        "title": "Meetup #1",
        "startsAt": "2026-08-15T18:00:00.000Z",
        "venue": "Tashkent Hub",
        "description": "A great meetup.",
        "capacity": 50,
        "registrationCount": 10,
        "isRegistered": False,
    }
    base.update(overrides)
    return base


def _known_user_context(directus_user_id: str = "dir-user-1") -> UserContext:
    return UserContext(
        telegram_id="12345",
        is_known=True,
        directus_user_id=directus_user_id,
        is_temp=False,
        country="uz",
    )


@pytest.mark.asyncio
async def test_event_detail_shows_usage_message_when_no_argument_given() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without an event id argument")

    api_client = _client_for(handler)
    update = make_message_update(text="/event")
    command = CommandObject(command="event", args=None)

    with mock_answer(update.message) as answer:
        await handle_event_detail(update.message, command, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("events.usage")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_event_detail_renders_full_detail_with_register_button_when_not_registered() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "directusUserId=dir-user-1" in str(request.url)
        return httpx.Response(200, json=_detail_response(isRegistered=False))

    api_client = _client_for(handler)
    update = make_message_update(text="/event evt-1")
    command = CommandObject(command="event", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_event_detail(update.message, command, api_client, _known_user_context())
        (sent_text,), kwargs = answer.call_args

    assert "Meetup #1" in sent_text
    assert "Tashkent Hub" in sent_text
    assert "A great meetup." in sent_text
    keyboard = kwargs.get("reply_markup")
    assert keyboard is not None
    button = keyboard.inline_keyboard[0][0]
    assert button.text == t("event.button_register")
    assert button.callback_data == "evreg:evt-1"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_event_detail_shows_going_button_when_already_registered() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_detail_response(isRegistered=True))

    api_client = _client_for(handler)
    update = make_message_update(text="/event evt-1")
    command = CommandObject(command="event", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_event_detail(update.message, command, api_client, _known_user_context())
        _, kwargs = answer.call_args

    button = kwargs["reply_markup"].inline_keyboard[0][0]
    assert button.text == t("event.button_going")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_event_detail_omits_directus_user_id_when_user_context_is_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "directusUserId" not in str(request.url)
        return httpx.Response(200, json=_detail_response())

    api_client = _client_for(handler)
    update = make_message_update(text="/event evt-1")
    command = CommandObject(command="event", args="evt-1")

    with mock_answer(update.message):
        await handle_event_detail(update.message, command, api_client, None)

    await api_client.aclose()


@pytest.mark.asyncio
async def test_event_detail_shows_not_found_message_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "event_not_found"})

    api_client = _client_for(handler)
    update = make_message_update(text="/event missing")
    command = CommandObject(command="event", args="missing")

    with mock_answer(update.message) as answer:
        await handle_event_detail(update.message, command, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.not_found")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_event_detail_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    update = make_message_update(text="/event evt-1")
    command = CommandObject(command="event", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_event_detail(update.message, command, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_register_placeholder_shows_coming_soon_alert_without_crashing() -> None:
    callback = make_callback_query(data="evreg:evt-1")

    with mock_callback_answer(callback) as cb_answer:
        await handle_register_placeholder(callback)
        cb_answer.assert_awaited_once_with(t("event.register_placeholder"), show_alert=True)
