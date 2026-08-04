"""Tests for the /me command handler (FR-BOT-002 PR 3/6).

Covers: guard cases (unresolved identity/country), rendering (empty state,
status badges, points total, temp-account nudge, link CTA), API-unavailable
handling, and the Cancel-button callback that reuses cancel_registration.
"""

from __future__ import annotations

import httpx
import pytest

from src.handlers.me import handle_me, handle_me_cancel_callback, render_me
from src.keyboards.me import ME_CANCEL_PREFIX
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient, MeRegistration, MeRegistrationEvent, MeSummary
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


def _known_user_context(
    *,
    directus_user_id: str | None = "dir-user-1",
    country: str | None = "uz",
    is_temp: bool = False,
) -> UserContext:
    return UserContext(
        telegram_id="12345",
        is_known=True,
        directus_user_id=directus_user_id,
        is_temp=is_temp,
        country=country,
    )


def _registration(
    *, status: str = "registered", title: str = "Meetup #1", event_id: str = "evt-1"
) -> MeRegistration:
    return MeRegistration(
        id="reg-1",
        status=status,
        event=MeRegistrationEvent(
            id=event_id,
            title=title,
            starts_at="2026-08-15T18:00:00Z",
            ends_at="2026-08-15T20:00:00Z",
            location=None,
        ),
    )


# ── Guard cases ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_shows_unavailable_message_when_user_context_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved user context")

    api_client = _client_for(handler)
    update = make_message_update(text="/me")
    with mock_answer(update.message) as answer:
        await handle_me(update.message, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_me_shows_events_unavailable_message_when_country_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved country")

    api_client = _client_for(handler)
    update = make_message_update(text="/me")
    context = _known_user_context(country=None)
    with mock_answer(update.message) as answer:
        await handle_me(update.message, api_client, context)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("events.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_me_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    update = make_message_update(text="/me")
    with mock_answer(update.message) as answer:
        await handle_me(update.message, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("me.unavailable")
    await api_client.aclose()


# ── AC: /me correctly shows all active registrations with status badges ──


@pytest.mark.asyncio
async def test_me_shows_empty_state_when_no_registrations() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"registrations": [], "pointsTotal": 0})

    api_client = _client_for(handler)
    update = make_message_update(text="/me")
    with mock_answer(update.message) as answer:
        await handle_me(update.message, api_client, _known_user_context())
        (sent_text,), kwargs = answer.call_args

    assert t("me.registrations_empty") in sent_text
    assert kwargs["reply_markup"] is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_me_renders_registered_and_waitlisted_badges_distinctly() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "registrations": [
                    {
                        "id": "reg-1",
                        "status": "registered",
                        "event": {
                            "id": "evt-1",
                            "title": "Meetup #1",
                            "startsAt": "2026-08-15T18:00:00Z",
                            "endsAt": "2026-08-15T20:00:00Z",
                            "location": None,
                        },
                    },
                    {
                        "id": "reg-2",
                        "status": "waitlisted",
                        "event": {
                            "id": "evt-2",
                            "title": "Full Meetup",
                            "startsAt": "2026-08-20T18:00:00Z",
                            "endsAt": "2026-08-20T20:00:00Z",
                            "location": None,
                        },
                    },
                ],
                "pointsTotal": 15,
            },
        )

    api_client = _client_for(handler)
    update = make_message_update(text="/me")
    with mock_answer(update.message) as answer:
        await handle_me(update.message, api_client, _known_user_context())
        (sent_text,), kwargs = answer.call_args

    assert t("me.status_registered") in sent_text
    assert t("me.status_waitlisted") in sent_text
    assert "Meetup #1" in sent_text
    assert "Full Meetup" in sent_text
    assert t("me.points_total").format(points=15) in sent_text
    assert kwargs["reply_markup"] is not None  # two registrations -> two Cancel buttons
    await api_client.aclose()


@pytest.mark.asyncio
async def test_me_shows_temp_account_nudge_only_for_temp_users() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"registrations": [], "pointsTotal": 0})

    api_client = _client_for(handler)

    update = make_message_update(text="/me")
    with mock_answer(update.message) as answer:
        await handle_me(update.message, api_client, _known_user_context(is_temp=True))
        (temp_text,), _ = answer.call_args
    assert t("me.temp_account_nudge") in temp_text

    update2 = make_message_update(text="/me", update_id=2)
    with mock_answer(update2.message) as answer2:
        await handle_me(update2.message, api_client, _known_user_context(is_temp=False))
        (full_text,), _ = answer2.call_args
    assert t("me.temp_account_nudge") not in full_text

    await api_client.aclose()


def test_render_me_shows_telegram_not_linked_prompt() -> None:
    """FR-AUTH-007: /me shows the real Telegram link state instead of the
    old generic "link on web" CTA. Not-linked shows a /link prompt."""
    summary = MeSummary(registrations=[], points_total=0, telegram_linked=False)
    text = render_me(summary, is_temp=False, lang="ru")
    assert t("me.telegram_not_linked") in text


def test_render_me_shows_telegram_linked_handle() -> None:
    summary = MeSummary(
        registrations=[],
        points_total=0,
        telegram_linked=True,
        telegram_username="ivanov",
    )
    text = render_me(summary, is_temp=False, lang="ru")
    assert t("me.telegram_linked").format(handle="@ivanov") in text


def test_render_me_shows_telegram_linked_without_username() -> None:
    """telegram_username can be None even when linked (username is optional
    on Telegram accounts) — falls back to a generic "Telegram" label rather
    than rendering a literal "@None"."""
    summary = MeSummary(
        registrations=[],
        points_total=0,
        telegram_linked=True,
        telegram_username=None,
    )
    text = render_me(summary, is_temp=False, lang="ru")
    assert t("me.telegram_linked").format(handle="Telegram") in text
    assert "@None" not in text


def test_render_me_never_mentions_streak() -> None:
    """Documents the deliberate scope decision: no streak concept exists
    anywhere in this codebase, so /me must never render one (not even a
    fabricated placeholder). See handlers/me.py's module docstring."""
    summary = MeSummary(
        registrations=[_registration()],
        points_total=50,
    )
    text = render_me(summary, is_temp=True, lang="ru")
    assert "streak" not in text.lower()
    assert "серия" not in text.lower()  # ru: "streak"/"series"


# ── Cancel button callback ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_cancel_callback_confirms_cancellation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        return httpx.Response(200, json={"status": "cancelled"})

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{ME_CANCEL_PREFIX}:evt-1")

    with mock_callback_answer(callback) as cb_answer:
        await handle_me_cancel_callback(callback, api_client, _known_user_context())
        cb_answer.assert_awaited_once_with(t("cancel.confirmed"), show_alert=True)
    await api_client.aclose()


@pytest.mark.asyncio
async def test_me_cancel_callback_shows_not_registered_without_raising() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "not_registered"})

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{ME_CANCEL_PREFIX}:evt-1")

    with mock_callback_answer(callback) as cb_answer:
        await handle_me_cancel_callback(callback, api_client, _known_user_context())
        cb_answer.assert_awaited_once_with(t("cancel.not_registered"), show_alert=True)
    await api_client.aclose()


@pytest.mark.asyncio
async def test_me_cancel_callback_ignores_when_context_missing() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved user context")

    api_client = _client_for(handler)
    callback = make_callback_query(data=f"{ME_CANCEL_PREFIX}:evt-1")

    with mock_callback_answer(callback) as cb_answer:
        await handle_me_cancel_callback(callback, api_client, None)
        cb_answer.assert_awaited_once_with(t("event.unavailable"), show_alert=True)
    await api_client.aclose()
