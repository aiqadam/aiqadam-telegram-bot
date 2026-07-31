"""Tests for the global error handler router (FR-BOT-001 §6).

Gap identified by 06-test-strategy.md as lower priority (not directly
AC-mapped) but included here: this is new code with a security-relevant
property (04-security-review.md INV-2 — raw exception text must not leak
into a loggable field other than the stdlib-formatted traceback) that was
previously verified only by SecurityReviewer reading the code, not by an
automated test. Included per TestDesigner's own judgment call, since the
guard is cheap to write and directly regression-tests that property.
"""

from __future__ import annotations

import logging

import pytest
from aiogram.types import ErrorEvent

from src.error_handler import handle_error
from src.locales import t
from tests.conftest import make_message_update, mock_answer


@pytest.mark.asyncio
async def test_sends_generic_user_facing_message_when_handler_raises() -> None:
    update = make_message_update(text="/start")
    exc = ValueError("super secret internal detail: db password is hunter2")
    event = ErrorEvent(update=update, exception=exc)

    with mock_answer(update.message) as answer:
        result = await handle_error(event)
        answer.assert_awaited_once_with(t("error.generic"))

    assert result is True


@pytest.mark.asyncio
async def test_generic_message_never_contains_the_raw_exception_text() -> None:
    update = make_message_update(text="/start")
    secret_detail = "super-secret-internal-detail-xyz"
    exc = ValueError(secret_detail)
    event = ErrorEvent(update=update, exception=exc)

    with mock_answer(update.message) as answer:
        await handle_error(event)
        sent_message = answer.call_args.args[0]

    assert secret_detail not in sent_message


@pytest.mark.asyncio
async def test_logs_structured_error_with_update_id_and_full_traceback(caplog) -> None:
    update = make_message_update(text="/start", update_id=555)
    exc = ValueError("boom")
    event = ErrorEvent(update=update, exception=exc)

    with caplog.at_level(logging.ERROR, logger="bot.errors"), mock_answer(update.message):
        await handle_error(event)

    records = [r for r in caplog.records if r.name == "bot.errors"]
    assert len(records) == 1
    record = records[0]
    assert record.update_id == 555
    # exc_info was attached (the traceback is available for the formatter
    # to render), not swallowed or replaced with a bare message string.
    assert record.exc_info is not None
    assert record.exc_info[1] is exc


@pytest.mark.asyncio
async def test_does_not_raise_when_message_answer_itself_fails() -> None:
    """Best-effort user notification: if answer() itself raises, the error
    handler must swallow it (already logged) rather than propagate."""
    update = make_message_update(text="/start")
    exc = ValueError("boom")
    event = ErrorEvent(update=update, exception=exc)

    with mock_answer(update.message) as answer:
        answer.side_effect = RuntimeError("network down")
        result = await handle_error(event)

    assert result is True


@pytest.mark.asyncio
async def test_returns_true_when_update_has_no_message_or_callback_query() -> None:
    """An update kind with neither message nor callback_query (e.g. a raw
    poll answer) must not crash the error handler."""
    from aiogram.types import Update

    bare_update = Update(update_id=1)
    exc = ValueError("boom")
    event = ErrorEvent(update=bare_update, exception=exc)

    result = await handle_error(event)

    assert result is True
