"""Tests for the /events handler and its pagination callback (FR-BOT-002 PR 1/6)."""

from __future__ import annotations

import httpx
import pytest

from src.handlers.events import format_event_date, handle_events, handle_events_page_callback
from src.locales import t
from src.services.api_client import ApiClient
from tests.conftest import (
    make_callback_query,
    make_message_update,
    mock_answer,
    mock_callback_answer,
    mock_edit_text,
)


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


def _events_response(
    items: list[dict], *, offset: int = 0, limit: int = 5, total: int | None = None
):
    resolved_total = total if total is not None else len(items)
    return {"items": items, "offset": offset, "limit": limit, "total": resolved_total}


def _item(i: int) -> dict:
    return {
        "id": f"evt-{i}",
        "title": f"Meetup #{i}",
        "startsAt": "2026-08-15T18:00:00.000Z",
        "registrationCount": i,
    }


# ── format_event_date ───────────────────────────────────────────────────


def test_format_event_date_renders_short_human_readable_form() -> None:
    assert format_event_date("2026-08-15T18:00:00.000Z") == "15.08.2026 18:00"


def test_format_event_date_falls_back_to_raw_string_on_parse_failure() -> None:
    assert format_event_date("not-a-date") == "not-a-date"


# ── /events command ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_events_shows_empty_message_when_no_events() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_events_response([]))

    api_client = _client_for(handler)
    update = make_message_update(text="/events")

    with mock_answer(update.message) as answer:
        await handle_events(update.message, api_client, "uz")
        (sent_text,), kwargs = answer.call_args

    assert sent_text == t("events.empty")
    assert kwargs.get("reply_markup") is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_events_renders_items_and_no_pagination_keyboard_when_5_or_fewer() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_events_response([_item(1), _item(2)], total=2))

    api_client = _client_for(handler)
    update = make_message_update(text="/events")

    with mock_answer(update.message) as answer:
        await handle_events(update.message, api_client, "uz")
        (sent_text,), kwargs = answer.call_args

    assert "Meetup #1" in sent_text
    assert "Meetup #2" in sent_text
    assert "/event evt-1" in sent_text
    assert kwargs.get("reply_markup") is None  # only one page — no buttons
    await api_client.aclose()


@pytest.mark.asyncio
async def test_events_renders_pagination_keyboard_when_more_than_one_page() -> None:
    items = [_item(i) for i in range(5)]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_events_response(items, offset=0, limit=5, total=12))

    api_client = _client_for(handler)
    update = make_message_update(text="/events")

    with mock_answer(update.message) as answer:
        await handle_events(update.message, api_client, "uz")
        _, kwargs = answer.call_args

    keyboard = kwargs.get("reply_markup")
    assert keyboard is not None
    buttons = [b.text for row in keyboard.inline_keyboard for b in row]
    assert t("events.button_next") in buttons
    assert t("events.button_prev") not in buttons  # first page: no "previous"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_events_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    update = make_message_update(text="/events")

    with mock_answer(update.message) as answer:
        await handle_events(update.message, api_client, "uz")
        (sent_text,), _ = answer.call_args

    assert sent_text == t("events.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_events_shows_unavailable_message_when_country_is_unresolved() -> None:
    """AuthMiddleware attaches country=None for unknown/unresolvable users."""

    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API when country is None")

    api_client = _client_for(handler)
    update = make_message_update(text="/events")

    with mock_answer(update.message) as answer:
        await handle_events(update.message, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("events.unavailable")
    await api_client.aclose()


# ── pagination callback ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_events_page_callback_edits_message_with_next_page() -> None:
    items = [_item(i) for i in range(5, 10)]

    def handler(request: httpx.Request) -> httpx.Response:
        assert "offset=5" in str(request.url)
        return httpx.Response(200, json=_events_response(items, offset=5, limit=5, total=12))

    api_client = _client_for(handler)
    callback = make_callback_query(data="evpg:5")

    with mock_edit_text(callback.message) as edit_text, mock_callback_answer(callback) as cb_answer:
        await handle_events_page_callback(callback, api_client, "uz")
        edit_text.assert_awaited_once()
        cb_answer.assert_awaited_once()

    await api_client.aclose()


@pytest.mark.asyncio
async def test_events_page_callback_ignores_malformed_offset_without_crashing() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API for a malformed offset")

    api_client = _client_for(handler)
    callback = make_callback_query(data="evpg:not-a-number")

    with mock_edit_text(callback.message) as edit_text, mock_callback_answer(callback) as cb_answer:
        await handle_events_page_callback(callback, api_client, "uz")
        edit_text.assert_not_awaited()
        cb_answer.assert_awaited_once()

    await api_client.aclose()
