"""Tests for RateLimitMiddleware (FR-BOT-001 AC-9)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.middlewares.rate_limit import SLOW_DOWN_MESSAGE, RateLimitMiddleware
from tests.conftest import make_message_update, mock_answer


@pytest.mark.asyncio
async def test_allows_requests_under_the_limit() -> None:
    middleware = RateLimitMiddleware(max_per_minute=10)
    handler = AsyncMock(return_value="handled")

    for i in range(10):
        update = make_message_update(update_id=i)
        result = await middleware(handler, update, {})
        assert result == "handled"

    assert handler.await_count == 10


@pytest.mark.asyncio
async def test_blocks_requests_over_the_limit_and_replies_slow_down() -> None:
    middleware = RateLimitMiddleware(max_per_minute=10)
    handler = AsyncMock(return_value="handled")

    telegram_user_id = 999
    for i in range(10):
        update = make_message_update(update_id=i, telegram_user_id=telegram_user_id)
        await middleware(handler, update, {})

    # 11th request in the same window should be rejected.
    over_limit_update = make_message_update(update_id=10, telegram_user_id=telegram_user_id)

    with mock_answer(over_limit_update.message) as answer:
        result = await middleware(handler, over_limit_update, {})
        answer.assert_awaited_once_with(SLOW_DOWN_MESSAGE)

    assert result is None
    assert handler.await_count == 10  # downstream handler NOT invoked again


@pytest.mark.asyncio
async def test_different_telegram_ids_have_independent_limits() -> None:
    middleware = RateLimitMiddleware(max_per_minute=1)
    handler = AsyncMock(return_value="handled")

    update_a = make_message_update(update_id=1, telegram_user_id=111)
    update_b = make_message_update(update_id=2, telegram_user_id=222)

    result_a = await middleware(handler, update_a, {})
    result_b = await middleware(handler, update_b, {})

    assert result_a == "handled"
    assert result_b == "handled"
    assert handler.await_count == 2


@pytest.mark.asyncio
async def test_window_resets_after_time_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    middleware = RateLimitMiddleware(max_per_minute=1)
    handler = AsyncMock(return_value="handled")

    fake_now = [1000.0]
    monkeypatch.setattr("src.middlewares.rate_limit.time.monotonic", lambda: fake_now[0])

    update_1 = make_message_update(update_id=1, telegram_user_id=555)
    update_2 = make_message_update(update_id=2, telegram_user_id=555)

    assert await middleware(handler, update_1, {}) == "handled"
    with mock_answer(update_2.message):
        assert await middleware(handler, update_2, {}) is None  # still within window

    fake_now[0] += 61.0  # advance past the 60s window
    update_3 = make_message_update(update_id=3, telegram_user_id=555)
    assert await middleware(handler, update_3, {}) == "handled"
