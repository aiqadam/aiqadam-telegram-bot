"""Tests for the /link command handler and its two FSM collection steps (FR-AUTH-005).

Covers:
  - handle_link_command: unresolved/unknown user guard (AC-1), entry prompt +
    state transition (AC-2).
  - handle_link_email_reply: invalid email format re-prompt without leaving
    awaiting_email (AC-3); rate-limited error (AC-4); API unavailable on the
    start step (AC-5); lost context mid-flow; successful email collection —
    challenge_id stored in FSM, state → awaiting_code (AC-6).
  - handle_link_code_reply: lost context (AC-7); lost challenge_id via bot
    restart (AC-8); wrong code / exhausted — both map to LinkInvalidCodeError
    and render link.wrong_code because the API returns 401 for both (AC-9);
    member not found (AC-10); already linked to a different account (AC-11);
    API unavailable on confirm step (AC-12); success (AC-13).

FSM state is always cleared after every terminal outcome — verified in each test.
"""

from __future__ import annotations

import httpx
import pytest

from src.handlers.link import (
    handle_link_code_reply,
    handle_link_command,
    handle_link_email_reply,
)
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient
from src.states.link import LinkStates
from tests.conftest import make_fsm_context, make_message_update, mock_answer


def _client_for(handler) -> ApiClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return ApiClient("https://api.example.com", "test-token", client=http_client)


def _known_context(*, telegram_id: str = "12345") -> UserContext:
    return UserContext(
        telegram_id=telegram_id,
        is_known=True,
        directus_user_id="dir-1",
        is_temp=False,
        country="uz",
    )


def _unknown_context() -> UserContext:
    return UserContext(
        telegram_id="12345",
        is_known=False,
        directus_user_id=None,
        is_temp=False,
        country=None,
    )


# ── /link command entry ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_link_command_shows_unavailable_when_user_context_is_none() -> None:
    update = make_message_update(text="/link")
    state = make_fsm_context()

    with mock_answer(update.message) as answer:
        await handle_link_command(update.message, state, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_link_command_shows_unavailable_when_user_is_unknown() -> None:
    update = make_message_update(text="/link")
    state = make_fsm_context()

    with mock_answer(update.message) as answer:
        await handle_link_command(update.message, state, _unknown_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_link_command_prompts_for_email_and_enters_awaiting_email_state() -> None:
    update = make_message_update(text="/link")
    state = make_fsm_context()

    with mock_answer(update.message) as answer:
        await handle_link_command(update.message, state, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.prompt_email")
    assert await state.get_state() == LinkStates.awaiting_email.state


# ── awaiting_email step ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_link_email_reply_reprompts_on_invalid_format_without_calling_api() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API for a malformed email")

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_email)
    update = make_message_update(text="not-an-email")

    with mock_answer(update.message) as answer:
        await handle_link_email_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.invalid_email")
    # State stays in awaiting_email so the user can type a corrected email.
    assert await state.get_state() == LinkStates.awaiting_email.state
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_email_reply_shows_unavailable_and_clears_state_when_context_lost() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved context")

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_email)
    update = make_message_update(text="alice@example.com")

    with mock_answer(update.message) as answer:
        await handle_link_email_reply(update.message, state, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_email_reply_shows_rate_limited_and_clears_state() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "rate_limited"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_email)
    update = make_message_update(text="alice@example.com")

    with mock_answer(update.message) as answer:
        await handle_link_email_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.rate_limited")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_email_reply_shows_unavailable_and_clears_state_on_api_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_email)
    update = make_message_update(text="alice@example.com")

    with mock_answer(update.message) as answer:
        await handle_link_email_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_email_reply_stores_challenge_id_and_transitions_to_awaiting_code() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={"challenge_id": "ch-abc", "sent_to_email_masked": "a***@example.com"},
        )

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_email)
    update = make_message_update(text="alice@example.com", telegram_user_id=12345)

    with mock_answer(update.message) as answer:
        await handle_link_email_reply(
            update.message, state, api_client, _known_context(telegram_id="12345")
        )
        (sent_text,), _ = answer.call_args

    assert '"12345"' in captured["body"]
    assert '"alice@example.com"' in captured["body"]
    # Masked email appears in the code-sent confirmation message.
    assert "a***@example.com" in sent_text
    # challenge_id persisted in FSM data for the confirm step.
    data = await state.get_data()
    assert data.get("challenge_id") == "ch-abc"
    assert await state.get_state() == LinkStates.awaiting_code.state
    await api_client.aclose()


# ── awaiting_code step ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_link_code_reply_shows_unavailable_and_clears_state_when_context_lost() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API without a resolved context")

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_code)
    await state.update_data(challenge_id="ch-abc")
    update = make_message_update(text="123456")

    with mock_answer(update.message) as answer:
        await handle_link_code_reply(update.message, state, api_client, None)
        (sent_text,), _ = answer.call_args

    assert sent_text == t("event.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_code_reply_shows_unavailable_when_challenge_id_absent_from_fsm() -> None:
    # Simulates a bot restart between steps that cleared FSM storage.
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call the API when challenge_id is missing")

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_code)
    # Intentionally no update_data(challenge_id=...) call.
    update = make_message_update(text="123456")

    with mock_answer(update.message) as answer:
        await handle_link_code_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_code_reply_shows_wrong_code_and_clears_state_on_401() -> None:
    # The API returns 401 for both wrong-code and exhausted-attempts — both
    # raise LinkInvalidCodeError and are rendered as link.wrong_code.
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_code"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_code)
    await state.update_data(challenge_id="ch-abc")
    update = make_message_update(text="000000")

    with mock_answer(update.message) as answer:
        await handle_link_code_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.wrong_code")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_code_reply_shows_no_account_and_clears_state_on_404() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "member_not_found"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_code)
    await state.update_data(challenge_id="ch-abc")
    update = make_message_update(text="123456")

    with mock_answer(update.message) as answer:
        await handle_link_code_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.no_account")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_code_reply_shows_already_linked_other_and_clears_state_on_409() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "already_linked_to_different_account"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_code)
    await state.update_data(challenge_id="ch-abc")
    update = make_message_update(text="123456")

    with mock_answer(update.message) as answer:
        await handle_link_code_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.already_linked_other")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_code_reply_shows_unavailable_and_clears_state_on_api_500() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_code)
    await state.update_data(challenge_id="ch-abc")
    update = make_message_update(text="123456")

    with mock_answer(update.message) as answer:
        await handle_link_code_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.unavailable")
    assert await state.get_state() is None
    await api_client.aclose()


@pytest.mark.asyncio
async def test_link_code_reply_shows_success_and_clears_state_on_200() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"member_id": "m-1", "tenant": "uz"})

    api_client = _client_for(handler)
    state = make_fsm_context()
    await state.set_state(LinkStates.awaiting_code)
    await state.update_data(challenge_id="ch-abc")
    update = make_message_update(text="123456")

    with mock_answer(update.message) as answer:
        await handle_link_code_reply(update.message, state, api_client, _known_context())
        (sent_text,), _ = answer.call_args

    assert sent_text == t("link.success")
    assert await state.get_state() is None
    await api_client.aclose()
