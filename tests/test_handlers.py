"""Tests for the /start smoke-test handler and the unknown-command fallback."""

from __future__ import annotations

import pytest

from src.handlers.fallback import handle_unknown_command
from src.handlers.start import handle_start
from src.locales import t
from tests.conftest import make_message_update, mock_answer


@pytest.mark.asyncio
async def test_start_handler_replies_with_welcome_message() -> None:
    update = make_message_update(text="/start")

    with mock_answer(update.message) as answer:
        await handle_start(update.message)
        answer.assert_awaited_once_with(t("start.welcome"))


@pytest.mark.asyncio
async def test_unknown_command_handler_replies_with_help_hint() -> None:
    update = make_message_update(text="/does_not_exist")

    with mock_answer(update.message) as answer:
        await handle_unknown_command(update.message)
        answer.assert_awaited_once_with(t("unknown_command"))

    assert "/help" in t("unknown_command")
