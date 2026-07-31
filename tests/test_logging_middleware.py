"""Tests for LoggingMiddleware + JsonFormatter (FR-BOT-001 AC-11).

Gap identified by 06-test-strategy.md: no test previously asserted the
actual emitted stdout line is valid JSON with the required keys
(telegram_id, command, duration_ms, status). This attaches a real
JsonFormatter to a StringIO-backed StreamHandler on the same logger
LoggingMiddleware uses ("bot.update"), so the assertions exercise the
real formatting path end-to-end rather than just inspecting the
LogRecord's `extra` dict.
"""

from __future__ import annotations

import io
import json
import logging

import pytest

from src.logging_setup import JsonFormatter
from src.middlewares.logging_middleware import LoggingMiddleware
from tests.conftest import make_message_update


@pytest.fixture
def captured_json_logs():
    """Attach a JsonFormatter-backed handler to the "bot.update" logger for
    the duration of a test and yield the StringIO stream to read lines from.
    """
    stream = io.StringIO()
    handler = logging.StreamHandler(stream=stream)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger("bot.update")
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = True


def _last_json_line(stream: io.StringIO) -> dict:
    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert lines, "expected at least one log line to be emitted"
    return json.loads(lines[-1])


@pytest.mark.asyncio
async def test_emits_one_json_line_with_required_keys_on_success(captured_json_logs) -> None:
    middleware = LoggingMiddleware()

    async def downstream(_event, _data):
        return "handled"

    update = make_message_update(telegram_user_id=123, text="/start")
    result = await middleware(downstream, update, {})

    assert result == "handled"
    payload = _last_json_line(captured_json_logs)

    assert payload["telegram_id"] == "123"
    assert payload["command"] == "/start"
    assert isinstance(payload["duration_ms"], (int, float))
    assert payload["duration_ms"] >= 0
    assert payload["status"] == "ok"


@pytest.mark.asyncio
async def test_emitted_line_is_a_single_valid_json_object(captured_json_logs) -> None:
    middleware = LoggingMiddleware()

    async def downstream(_event, _data):
        return "handled"

    update = make_message_update(telegram_user_id=456, text="/help")
    await middleware(downstream, update, {})

    lines = [line for line in captured_json_logs.getvalue().splitlines() if line.strip()]
    assert len(lines) == 1
    # json.loads raises if the line isn't a single valid JSON document —
    # this is itself the assertion that the log line is well-formed JSON,
    # not e.g. a Python repr or a multi-line traceback dump.
    parsed = json.loads(lines[0])
    assert isinstance(parsed, dict)


@pytest.mark.asyncio
async def test_status_is_error_and_line_still_emitted_when_handler_raises(
    captured_json_logs,
) -> None:
    middleware = LoggingMiddleware()

    async def downstream(_event, _data):
        raise ValueError("boom")

    update = make_message_update(telegram_user_id=789, text="/start")

    with pytest.raises(ValueError, match="boom"):
        await middleware(downstream, update, {})

    payload = _last_json_line(captured_json_logs)
    assert payload["telegram_id"] == "789"
    assert payload["status"] == "error"


@pytest.mark.asyncio
async def test_command_is_null_for_non_command_text(captured_json_logs) -> None:
    middleware = LoggingMiddleware()

    async def downstream(_event, _data):
        return "handled"

    update = make_message_update(telegram_user_id=321, text="hello there")
    await middleware(downstream, update, {})

    payload = _last_json_line(captured_json_logs)
    assert payload["command"] is None
