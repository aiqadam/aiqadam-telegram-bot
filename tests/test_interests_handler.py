"""Tests for the /interests command handler and its toggle callback
(FR-BOT-002 PR 5/6).

Covers: guard cases (unresolved identity — no country guard, unlike
leaderboard, since interests are not tenant-scoped), rendering (no
interests -> all [ ], one selected -> [x] on that button only), toggle-on
callback (asserts edit_text called with the updated keyboard), toggle-off
callback, and the ApiUnavailableError -> interests.unavailable path on
both the message and callback surfaces (AC-5).
"""

from __future__ import annotations

import httpx
import pytest

from src.handlers.interests import handle_interest_toggle_callback, handle_interests
from src.keyboards.interests import INTEREST_TOGGLE_PREFIX, SELECTED_MARKER, UNSELECTED_MARKER
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient
from tests.conftest import (
    make_callback_query,
    make_message_update,
    mock_answer,
    mock_callback_answer,
    mock_edit_text,
)

AVAILABLE = ["llm", "mlops", "computer-vision", "product", "career", "ethics", "infra"]


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


def _known_user_context(
    *, directus_user_id: str | None = "dir-user-1", is_known: bool | None = True
) -> UserContext:
    return UserContext(
        telegram_id="12345",
        is_known=is_known,
        directus_user_id=directus_user_id,
        is_temp=False,
        country="uz",
    )


# ── Guard cases ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_interests_shows_unavailable_message_when_user_context_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved user context")

    api_client = _client_for(handler)
    update = make_message_update(text="/interests")
    with mock_answer(update.message) as answer:
        await handle_interests(update.message, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interests_shows_unavailable_message_when_user_is_unknown() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API for an unknown user")

    api_client = _client_for(handler)
    update = make_message_update(text="/interests")
    context = _known_user_context(is_known=False)
    with mock_answer(update.message) as answer:
        await handle_interests(update.message, api_client, context)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interests_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    update = make_message_update(text="/interests")
    with mock_answer(update.message) as answer:
        await handle_interests(update.message, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("interests.unavailable")
    await api_client.aclose()


# ── AC-1/AC-2: rendering ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_interests_renders_all_unselected_when_no_interests() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"selected": [], "available": AVAILABLE})

    api_client = _client_for(handler)
    update = make_message_update(text="/interests")
    with mock_answer(update.message) as answer:
        await handle_interests(update.message, api_client, _known_user_context())
        _, kwargs = answer.call_args

    keyboard = kwargs["reply_markup"]
    buttons = [row[0] for row in keyboard.inline_keyboard]
    assert len(buttons) == len(AVAILABLE)
    assert all(b.text.startswith(UNSELECTED_MARKER) for b in buttons)
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interests_renders_only_selected_topic_as_checked() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"selected": ["llm"], "available": AVAILABLE})

    api_client = _client_for(handler)
    update = make_message_update(text="/interests")
    with mock_answer(update.message) as answer:
        await handle_interests(update.message, api_client, _known_user_context())
        _, kwargs = answer.call_args

    keyboard = kwargs["reply_markup"]
    buttons = {row[0].callback_data: row[0] for row in keyboard.inline_keyboard}
    llm_button = buttons[f"{INTEREST_TOGGLE_PREFIX}:llm"]
    other_buttons = [b for cd, b in buttons.items() if cd != f"{INTEREST_TOGGLE_PREFIX}:llm"]

    assert llm_button.text.startswith(SELECTED_MARKER)
    assert all(b.text.startswith(UNSELECTED_MARKER) for b in other_buttons)
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interests_callback_data_stays_within_telegram_64_byte_limit() -> None:
    """AC-6 — every button's callback_data must stay within Telegram's
    64-byte cap, matching ME_CANCEL_PREFIX/EVENTS_PAGE_PREFIX's own
    established short-prefix convention."""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"selected": [], "available": AVAILABLE})

    api_client = _client_for(handler)
    update = make_message_update(text="/interests")
    with mock_answer(update.message) as answer:
        await handle_interests(update.message, api_client, _known_user_context())
        _, kwargs = answer.call_args

    keyboard = kwargs["reply_markup"]
    for row in keyboard.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) <= 64
    await api_client.aclose()


# ── AC-3/AC-4: toggle callback, in-place edit ────────────────────────────


@pytest.mark.asyncio
async def test_interest_toggle_on_callback_edits_message_with_updated_keyboard() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, json={"selected": ["llm"], "available": AVAILABLE})

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{INTEREST_TOGGLE_PREFIX}:llm")
    with mock_edit_text(callback.message) as edit_text, mock_callback_answer(callback) as cb_answer:
        await handle_interest_toggle_callback(callback, api_client, _known_user_context())

    edit_text.assert_awaited_once()
    _, kwargs = edit_text.call_args
    keyboard = kwargs["reply_markup"]
    buttons = {row[0].callback_data: row[0] for row in keyboard.inline_keyboard}
    assert buttons[f"{INTEREST_TOGGLE_PREFIX}:llm"].text.startswith(SELECTED_MARKER)
    cb_answer.assert_awaited_once()
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interest_toggle_off_callback_edits_message_with_unselected_button() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, json={"selected": [], "available": AVAILABLE})

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{INTEREST_TOGGLE_PREFIX}:llm")
    with mock_edit_text(callback.message) as edit_text, mock_callback_answer(callback):
        await handle_interest_toggle_callback(callback, api_client, _known_user_context())

    _, kwargs = edit_text.call_args
    keyboard = kwargs["reply_markup"]
    buttons = {row[0].callback_data: row[0] for row in keyboard.inline_keyboard}
    assert buttons[f"{INTEREST_TOGGLE_PREFIX}:llm"].text.startswith(UNSELECTED_MARKER)
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interest_toggle_callback_sends_the_tapped_topic_slug() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content
        return httpx.Response(200, json={"selected": [], "available": AVAILABLE})

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{INTEREST_TOGGLE_PREFIX}:computer-vision")
    with mock_edit_text(callback.message), mock_callback_answer(callback):
        await handle_interest_toggle_callback(callback, api_client, _known_user_context())

    assert b'"topic":"computer-vision"' in captured["body"]
    await api_client.aclose()


# ── AC-5: API unavailable, both surfaces ─────────────────────────────────


@pytest.mark.asyncio
async def test_interest_toggle_callback_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{INTEREST_TOGGLE_PREFIX}:llm")
    with mock_edit_text(callback.message) as edit_text, mock_callback_answer(callback) as cb_answer:
        await handle_interest_toggle_callback(callback, api_client, _known_user_context())

    (sent_text,), _ = edit_text.call_args
    assert sent_text == t("interests.unavailable")
    cb_answer.assert_awaited_once()
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interest_toggle_callback_guards_on_unknown_user() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API for an unknown user")

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{INTEREST_TOGGLE_PREFIX}:llm")
    context = _known_user_context(is_known=False)
    with mock_edit_text(callback.message) as edit_text, mock_callback_answer(callback):
        await handle_interest_toggle_callback(callback, api_client, context)

    (sent_text,), _ = edit_text.call_args
    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_interest_toggle_callback_noop_when_message_is_none() -> None:
    api_client = _client_for(lambda _: httpx.Response(200, json={}))
    callback = make_callback_query(data=f"{INTEREST_TOGGLE_PREFIX}:llm")
    callback = callback.model_copy(update={"message": None})

    with mock_callback_answer(callback) as cb_answer:
        await handle_interest_toggle_callback(callback, api_client, _known_user_context())

    cb_answer.assert_awaited_once()
    await api_client.aclose()
