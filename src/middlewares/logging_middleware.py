"""Logging middleware: one structured JSON log line per update.

FR-BOT-001 §5 / AC-11: structured JSON logs to stdout, for Loki ingestion.
Includes telegram_id, command, duration_ms, status per line, at minimum.
Runs outermost (registered first) so it can time the full middleware
chain + handler, including rate-limit rejections and auth resolution.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.middlewares._util import extract_command, extract_telegram_id

logger = logging.getLogger("bot.update")


class LoggingMiddleware(BaseMiddleware):
    """Logs one structured line per processed update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id = extract_telegram_id(event)
        command = extract_command(event)
        started_at = time.monotonic()
        status = "ok"

        try:
            result = await handler(event, data)
            return result
        except Exception:
            status = "error"
            raise
        finally:
            duration_ms = round((time.monotonic() - started_at) * 1000, 2)
            logger.info(
                "update_processed",
                extra={
                    "telegram_id": telegram_id,
                    "command": command,
                    "duration_ms": duration_ms,
                    "status": status,
                },
            )
