"""Tests for the /leaderboard command handler (FR-BOT-002 PR 4/6).

Covers: guard cases (unresolved identity/country), rendering (empty
state, top-10 ordering, caller-row highlight when present, no-highlight
when caller is absent from the top 10 — the AC-literal "if they appear"
scope decision documented in handlers/leaderboard.py's module docstring),
and API-unavailable handling. Temp-user exclusion is NOT re-tested here —
it's an API-side/live-verification concern (the bot has no filtering
logic of its own to exercise); see this workflow's Step 8 live
verification instead.
"""

from __future__ import annotations

import httpx
import pytest

from src.handlers.leaderboard import handle_leaderboard, render_leaderboard
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient, LeaderboardEntry, LeaderboardResult
from tests.conftest import make_message_update, mock_answer


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


# ── Guard cases ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_leaderboard_shows_unavailable_message_when_user_context_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved user context")

    api_client = _client_for(handler)
    update = make_message_update(text="/leaderboard")
    with mock_answer(update.message) as answer:
        await handle_leaderboard(update.message, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_leaderboard_shows_events_unavailable_message_when_country_is_none() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved country")

    api_client = _client_for(handler)
    update = make_message_update(text="/leaderboard")
    context = _known_user_context(country=None)
    with mock_answer(update.message) as answer:
        await handle_leaderboard(update.message, api_client, context)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("events.unavailable")
    await api_client.aclose()


@pytest.mark.asyncio
async def test_leaderboard_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    update = make_message_update(text="/leaderboard")
    with mock_answer(update.message) as answer:
        await handle_leaderboard(update.message, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("leaderboard.unavailable")
    await api_client.aclose()


# ── AC: shows top 10 members; caller's row highlighted if they appear ────


@pytest.mark.asyncio
async def test_leaderboard_shows_empty_state_when_no_entries() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entries": []})

    api_client = _client_for(handler)
    update = make_message_update(text="/leaderboard")
    with mock_answer(update.message) as answer:
        await handle_leaderboard(update.message, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert t("leaderboard.empty") in sent_text
    await api_client.aclose()


@pytest.mark.asyncio
async def test_leaderboard_renders_all_rows_in_order_with_rank_numbers() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "entries": [
                    {"displayName": "Alice", "points": 100, "isCaller": False},
                    {"displayName": "Bob", "points": 80, "isCaller": False},
                    {"displayName": "Carol", "points": 50, "isCaller": False},
                ]
            },
        )

    api_client = _client_for(handler)
    update = make_message_update(text="/leaderboard")
    with mock_answer(update.message) as answer:
        await handle_leaderboard(update.message, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    assert "1. Alice" in sent_text or "1. Alice — 100" in sent_text
    assert "Alice" in sent_text and "Bob" in sent_text and "Carol" in sent_text
    # Ordering: Alice's line appears before Bob's, Bob's before Carol's.
    assert sent_text.index("Alice") < sent_text.index("Bob") < sent_text.index("Carol")


@pytest.mark.asyncio
async def test_leaderboard_highlights_caller_row_when_present() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "entries": [
                    {"displayName": "Alice", "points": 100, "isCaller": False},
                    {"displayName": "Bob", "points": 80, "isCaller": True},
                ]
            },
        )

    api_client = _client_for(handler)
    update = make_message_update(text="/leaderboard")
    with mock_answer(update.message) as answer:
        await handle_leaderboard(update.message, api_client, _known_user_context())
        (sent_text,), _ = answer.call_args

    # Bob's row uses the bold/caller-marked template; Alice's uses the plain one.
    assert t("leaderboard.item_caller").format(rank=2, name="Bob", points=80) in sent_text
    assert t("leaderboard.item").format(rank=1, name="Alice", points=100) in sent_text


def test_render_leaderboard_no_highlight_when_caller_absent() -> None:
    """AC-literal scope decision: a caller outside the top 10 (i.e. no
    entry has is_caller=True) sees a fully unmarked list — no separate
    'your rank' line is rendered anywhere, and no row uses the bold
    caller template."""
    result = LeaderboardResult(
        entries=[
            LeaderboardEntry(display_name="Alice", points=100, is_caller=False),
            LeaderboardEntry(display_name="Bob", points=80, is_caller=False),
        ]
    )
    text = render_leaderboard(result, lang="ru")

    assert t("leaderboard.item").format(rank=1, name="Alice", points=100) in text
    assert t("leaderboard.item").format(rank=2, name="Bob", points=80) in text
    # Only the title carries <b> — no row does, since no row is is_caller.
    assert text.count("<b>") == 1
    assert "вы)" not in text  # ru "(you)" marker never appears
    assert "(you)" not in text
