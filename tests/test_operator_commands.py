"""Tests for FR-BOT-003 operator handlers and api_client operator methods."""

from __future__ import annotations

import httpx
import pytest

from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient
from tests.conftest import make_message_update, mock_answer


# ── helpers ───────────────────────────────────────────────────────────────────


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


def _operator_context(is_known: bool = True, role: str = "organizer") -> UserContext:
    return UserContext(
        telegram_id="99999",
        is_known=is_known,
        directus_user_id="dir-op-1",
        is_temp=False,
        country="uz",
        role=role,
    )


def _member_context() -> UserContext:
    return UserContext(
        telegram_id="11111",
        is_known=True,
        directus_user_id="dir-mem-1",
        is_temp=False,
        country="uz",
        role="member",
    )


# ── UserContext.is_operator ────────────────────────────────────────────────────


def test_is_operator_returns_true_for_organizer() -> None:
    assert _operator_context(role="organizer").is_operator() is True


def test_is_operator_returns_true_for_country_admin() -> None:
    assert _operator_context(role="country_admin").is_operator() is True


def test_is_operator_returns_true_for_super_admin() -> None:
    assert _operator_context(role="super_admin").is_operator() is True


def test_is_operator_returns_false_for_member() -> None:
    assert _member_context().is_operator() is False


def test_is_operator_returns_false_for_none_role() -> None:
    ctx = UserContext(
        telegram_id="0",
        is_known=True,
        directus_user_id="d",
        is_temp=False,
        country="uz",
        role=None,
    )
    assert ctx.is_operator() is False


# ── lookup returns role ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lookup_returns_role_from_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"directusUserId": "u-1", "isTemp": False, "country": "kz", "role": "organizer"},
        )

    api_client = _client_for(handler)
    result = await api_client.lookup_telegram_user("12345")

    assert result.role == "organizer"
    await api_client.aclose()


@pytest.mark.asyncio
async def test_lookup_role_is_none_when_absent_from_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"directusUserId": "u-2", "isTemp": False, "country": "uz"},
        )

    api_client = _client_for(handler)
    result = await api_client.lookup_telegram_user("22222")

    assert result.role is None
    await api_client.aclose()


# ── /attendance api_client.get_attendance ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_attendance_returns_counts() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "registered": 42,
                "attended": 15,
                "waitlisted": 3,
                "eventTitle": "AI Summit",
            },
        )

    api_client = _client_for(handler)
    result = await api_client.get_attendance(event_id="evt-1", country="uz")

    assert result.registered == 42
    assert result.attended == 15
    assert result.waitlisted == 3
    assert result.event_title == "AI Summit"
    await api_client.aclose()


# ── /attendance handler role gate ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_attendance_handler_denies_non_operator() -> None:
    from src.handlers.attendance import handle_attendance

    from aiogram.filters import CommandObject

    update = make_message_update(text="/attendance evt-1")
    cmd = CommandObject(prefix="/", command="attendance", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_attendance(
            update.message,
            command=cmd,
            api_client=None,
            user_context=_member_context(),
        )
        (sent_text,), _ = answer.call_args

    assert "доступ" in sent_text.lower() or "access" in sent_text.lower()


@pytest.mark.asyncio
async def test_attendance_handler_denies_anonymous() -> None:
    from src.handlers.attendance import handle_attendance

    from aiogram.filters import CommandObject

    update = make_message_update(text="/attendance evt-1")
    cmd = CommandObject(prefix="/", command="attendance", args="evt-1")

    with mock_answer(update.message) as answer:
        await handle_attendance(
            update.message,
            command=cmd,
            api_client=None,
            user_context=None,
        )
        answer.assert_awaited_once()


# ── /scan handler role gate ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_handler_denies_non_operator() -> None:
    from src.handlers.scan import handle_scan_command

    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey
    from aiogram.fsm.storage.memory import MemoryStorage

    update = make_message_update(text="/scan")
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=1, user_id=1)
    state = FSMContext(storage=storage, key=key)

    with mock_answer(update.message) as answer:
        await handle_scan_command(
            update.message,
            state=state,
            user_context=_member_context(),
        )
        answer.assert_awaited_once()
        (sent_text,), _ = answer.call_args

    assert "доступ" in sent_text.lower() or "access" in sent_text.lower()


# ── /approvals api_client.list_pending_approvals ──────────────────────────────


@pytest.mark.asyncio
async def test_list_pending_approvals_returns_empty_items() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": []})

    api_client = _client_for(handler)
    result = await api_client.list_pending_approvals(
        country="uz", directus_user_id="dir-op-1"
    )

    assert result.items == []
    await api_client.aclose()


# ── /announce api_client.push_announcement ────────────────────────────────────


@pytest.mark.asyncio
async def test_push_announcement_returns_recipient_count() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "recipientCount": 17})

    api_client = _client_for(handler)
    result = await api_client.push_announcement(
        event_id="evt-1",
        message="Hello everyone!",
        country="uz",
        directus_user_id="dir-op-1",
    )

    assert result.recipient_count == 17
    await api_client.aclose()


# ── operator stats ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_operator_stats_returns_counts() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"eventsManaged": 5, "registrationsThisPeriod": 120}
        )

    api_client = _client_for(handler)
    result = await api_client.get_operator_stats(directus_user_id="dir-op-1", country="uz")

    assert result.events_managed == 5
    assert result.registrations_this_period == 120
    await api_client.aclose()
