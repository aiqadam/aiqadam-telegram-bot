"""Tests for the /upgrade command handler and its FSM email-collection step
(FR-BOT-002 PR 6/6, final PR in this FR's sequence).

Covers: is_temp short-circuit (AC-2, no wasted API call for full accounts),
guard cases for unresolved identity, the FSM prompt -> state transition,
invalid-format re-prompt without leaving the state or calling the API
(AC-3), the 4 distinct outcome messages (success / telegram_user_not_found
/ not_a_temp_account / email_already_in_use) (AC-1/AC-4/AC-5), and the
API-unavailable retry path (AC-6) — plus that FSM state is always cleared
after the API call regardless of outcome.
"""

from __future__ import annotations

import httpx
import pytest

from src.handlers.upgrade import handle_upgrade_command, handle_upgrade_email_reply
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient
from src.states.upgrade import UpgradeStates
from tests.conftest import make_fsm_context, make_message_update, mock_answer


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


def _temp_user_context(*, telegram_id: str = "12345", is_known: bool | None = True) -> UserContext:
    return UserContext(
        telegram_id=telegram_id,
        is_known=is_known,
        directus_user_id=None,
        is_temp=True,
        country=None,
    )


def _full_user_context(*, telegram_id: str = "12345") -> UserContext:
    return UserContext(
        telegram_id=telegram_id,
        is_known=True,
        directus_user_id="dir-user-1",
        is_temp=False,
        country="uz",
    )


# ── /upgrade command entry ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upgrade_shows_unavailable_message_when_user_context_is_none() -> None:
    update = make_message_update(text="/upgrade")
    state = make_fsm_context()

    with mock_answer(update.message) as answer:
        await handle_upgrade_command(update.message, state, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_upgrade_shows_unavailable_message_when_user_is_unknown() -> None:
    update = make_message_update(text="/upgrade")
    state = make_fsm_context()
    context = _temp_user_context(is_known=False)

    with mock_answer(update.message) as answer:
        await handle_upgrade_command(update.message, state, context)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_upgrade_shows_already_full_account_message_and_does_not_enter_fsm() -> None:
    update = make_message_update(text="/upgrade")
    state = make_fsm_context()

    with mock_answer(update.message) as answer:
        await handle_upgrade_command(update.message, state, _full_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.already_full_account")
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_upgrade_prompts_for_email_and_enters_fsm_state_for_temp_account() -> None:
    update = make_message_update(text="/upgrade")
    state = make_fsm_context()

    with mock_answer(update.message) as answer:
        await handle_upgrade_command(update.message, state, _temp_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.prompt_email")
    assert await state.get_state() == UpgradeStates.awaiting_email.state


# ── AC-3: invalid-format email re-prompts without leaving the state ────────


@pytest.mark.asyncio
async def test_upgrade_email_reply_reprompts_on_invalid_format_without_calling_api() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API for an obviously malformed email")

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="not-an-email")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(update.message, state, api_client, _temp_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.invalid_email")
    assert await state.get_state() == UpgradeStates.awaiting_email.state
    await api_client.aclose()


@pytest.mark.asyncio
async def test_upgrade_email_reply_guards_on_unresolved_identity_and_clears_state() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved user context")

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="user@example.com")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(update.message, state, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()


# ── AC-1: success path ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upgrade_email_reply_sends_expected_payload_and_shows_success_message() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"ok": True})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="user@example.com")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(
            update.message, state, api_client, _temp_user_context(telegram_id="12345")
        )
        (sent_text,), _ = answer.call_args

    assert '"telegramId":"12345"' in captured["body"]
    assert '"email":"user@example.com"' in captured["body"]
    assert sent_text == t("upgrade.magic_link_sent")
    # Confirms the task brief's ~29-minute-TTL wording, not FR-AUTH-004's
    # stale "15 min" AC text.
    assert "30" in sent_text or "29" in sent_text
    assert "15" not in sent_text
    assert await state.get_state() is None
    await api_client.aclose()


# ── AC-4: telegram_user_not_found (404) ─────────────────────────────────


@pytest.mark.asyncio
async def test_upgrade_email_reply_shows_distinct_message_on_telegram_user_not_found() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "telegram_user_not_found"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="user@example.com")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(update.message, state, api_client, _temp_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.telegram_user_not_found")
    assert sent_text != t("upgrade.magic_link_sent")
    assert await state.get_state() is None
    await api_client.aclose()


# ── AC-4: not_a_temp_account (409, defensive race path) ─────────────────


@pytest.mark.asyncio
async def test_upgrade_email_reply_shows_already_full_account_message_on_not_a_temp_account() -> (
    None
):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "not_a_temp_account"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="user@example.com")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(update.message, state, api_client, _temp_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.already_full_account")
    assert await state.get_state() is None
    await api_client.aclose()


# ── AC-5: email_already_in_use (409) ────────────────────────────────────


@pytest.mark.asyncio
async def test_upgrade_email_reply_shows_email_in_use_message_without_overclaiming_linking() -> (
    None
):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "email_already_in_use"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="taken@example.com")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(update.message, state, api_client, _temp_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.email_already_in_use")
    # FR-AUTH-005 (Telegram-account-linking) does not exist as a built,
    # clickable feature yet — the message must not promise it.
    assert "telegram" not in sent_text.lower()
    assert await state.get_state() is None
    await api_client.aclose()


# ── AC-6: API unavailable ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upgrade_email_reply_shows_unavailable_message_on_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="user@example.com")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(update.message, state, api_client, _temp_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_upgrade_email_reply_shows_unavailable_message_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(UpgradeStates.awaiting_email)
    update = make_message_update(text="user@example.com")

    with mock_answer(update.message) as answer:
        await handle_upgrade_email_reply(update.message, state, api_client, _temp_user_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("upgrade.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()
