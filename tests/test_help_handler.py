"""Tests for the /help handler (FR-BOT-002 PR 1/6)."""

from __future__ import annotations

import pytest

from src.handlers.help import handle_help
from src.locales import t
from tests.conftest import make_message_update, mock_answer


@pytest.mark.asyncio
async def test_help_lists_all_ten_commands() -> None:
    update = make_message_update(text="/help")

    with mock_answer(update.message) as answer:
        await handle_help(update.message)
        answer.assert_awaited_once()
        (sent_text,), _ = answer.call_args

    for command in (
        "/start",
        "/events",
        "/event",
        "/register",
        "/cancel",
        "/me",
        "/leaderboard",
        "/interests",
        "/upgrade",
        "/help",
    ):
        assert command in sent_text


@pytest.mark.asyncio
async def test_help_marks_unimplemented_commands_as_coming_soon() -> None:
    update = make_message_update(text="/help")

    with mock_answer(update.message) as answer:
        await handle_help(update.message)
        (sent_text,), _ = answer.call_args

    # /register, /cancel, /me, /leaderboard, /interests, /upgrade are not
    # implemented in this PR — each locale string carries a "coming soon"
    # style marker so /help doesn't silently promise something unimplemented.
    assert t("help.register") in sent_text
    assert "скоро" in t("help.register") or "soon" in t("help.register").lower()
