"""Per-telegram_id rate limiting (FR-BOT-001 §5, AC-9).

10 requests/minute per telegram_id by default. Over the limit: reply with
a friendly "slow down" message and do NOT invoke the downstream handler.

In-memory sliding window, keyed by telegram_id. This is a single-process
bot (ADR-0034 §Q4: one bot container doing long-poll), so no shared/Redis
state is needed for this scaffold — matches the "bot owns no business
state" framing (this is transient rate-limit bookkeeping, not business
state) and keeps the dependency surface minimal.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from src.middlewares._util import extract_telegram_id

SLOW_DOWN_MESSAGE = "You're sending messages too fast. Please slow down and try again in a moment."

_WINDOW_SECONDS = 60.0


class RateLimitMiddleware(BaseMiddleware):
    """Blocks updates from a telegram_id once it exceeds N requests/minute."""

    def __init__(self, max_per_minute: int = 10) -> None:
        self._max_per_minute = max_per_minute
        self._history: dict[str, deque[float]] = defaultdict(deque)

    def _is_over_limit(self, telegram_id: str, *, now: float) -> bool:
        history = self._history[telegram_id]
        cutoff = now - _WINDOW_SECONDS
        while history and history[0] < cutoff:
            history.popleft()

        if len(history) >= self._max_per_minute:
            return True

        history.append(now)
        return False

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id = extract_telegram_id(event)
        if telegram_id is None:
            return await handler(event, data)

        if self._is_over_limit(telegram_id, now=time.monotonic()):
            message = event.message if isinstance(event, Update) else event
            reply = getattr(message, "answer", None)
            if callable(reply):
                await reply(SLOW_DOWN_MESSAGE)
            return None

        return await handler(event, data)
