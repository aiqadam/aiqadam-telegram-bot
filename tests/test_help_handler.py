"""Tests for the /help handler (FR-BOT-002 PR 1/6, updated PR 2/6, PR 3/6, PR 4/6)."""

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
async def test_help_no_longer_marks_register_and_cancel_as_coming_soon() -> None:
    update = make_message_update(text="/help")

    with mock_answer(update.message) as answer:
        await handle_help(update.message)
        (sent_text,), _ = answer.call_args

    # FR-BOT-002 PR 2/6 implements /register and /cancel — their /help
    # lines must no longer carry the "coming soon" marker PR 1 gave them.
    assert t("help.register") in sent_text
    assert "скоро" not in t("help.register") and "soon" not in t("help.register").lower()
    assert t("help.cancel") in sent_text
    assert "скоро" not in t("help.cancel") and "soon" not in t("help.cancel").lower()


@pytest.mark.asyncio
async def test_help_no_longer_marks_me_as_coming_soon() -> None:
    update = make_message_update(text="/help")

    with mock_answer(update.message) as answer:
        await handle_help(update.message)
        (sent_text,), _ = answer.call_args

    # FR-BOT-002 PR 3/6 implements /me — its /help line must no longer
    # carry the "coming soon" marker PR 1 gave it.
    assert t("help.me") in sent_text
    assert "скоро" not in t("help.me") and "soon" not in t("help.me").lower()


@pytest.mark.asyncio
async def test_help_no_longer_marks_leaderboard_as_coming_soon() -> None:
    update = make_message_update(text="/help")

    with mock_answer(update.message) as answer:
        await handle_help(update.message)
        (sent_text,), _ = answer.call_args

    # FR-BOT-002 PR 4/6 implements /leaderboard — its /help line must no
    # longer carry the "coming soon" marker PR 1 gave it.
    assert t("help.leaderboard") in sent_text
    assert "скоро" not in t("help.leaderboard") and "soon" not in t("help.leaderboard").lower()


@pytest.mark.asyncio
async def test_help_no_longer_marks_interests_as_coming_soon() -> None:
    update = make_message_update(text="/help")

    with mock_answer(update.message) as answer:
        await handle_help(update.message)
        (sent_text,), _ = answer.call_args

    # FR-BOT-002 PR 5/6 implements /interests — its /help line must no
    # longer carry the "coming soon" marker PR 1 gave it.
    assert t("help.interests") in sent_text
    assert "скоро" not in t("help.interests") and "soon" not in t("help.interests").lower()


@pytest.mark.asyncio
async def test_help_no_longer_marks_upgrade_as_coming_soon() -> None:
    update = make_message_update(text="/help")

    with mock_answer(update.message) as answer:
        await handle_help(update.message)
        (sent_text,), _ = answer.call_args

    # FR-BOT-002 PR 6/6 (final) implements /upgrade — its /help line must
    # no longer carry the "coming soon" marker PR 1 gave it. All 10
    # FR-BOT-002 commands are now implemented, so no command's /help line
    # should carry a "coming soon"/"скоро" marker anymore.
    assert t("help.upgrade") in sent_text
    assert "скоро" not in t("help.upgrade") and "soon" not in t("help.upgrade").lower()
    assert "скоро" not in sent_text and "coming soon" not in sent_text.lower()
