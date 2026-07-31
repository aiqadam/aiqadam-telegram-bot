"""Global error handling (FR-BOT-001 §6).

Unhandled exceptions raised by any handler are caught here: the user gets
a generic "something went wrong" message, and the full traceback is
logged as structured JSON to stdout (picked up by the LoggingMiddleware's
JSON formatter via `exc_info`).
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from src.locales import t

logger = logging.getLogger("bot.errors")

router = Router(name="errors")


@router.errors()
async def handle_error(event: ErrorEvent) -> bool:
    update = event.update
    message = update.message or (update.callback_query.message if update.callback_query else None)

    logger.error(
        "unhandled_exception",
        exc_info=event.exception,
        extra={"update_id": update.update_id},
    )

    if message is not None and hasattr(message, "answer"):
        try:
            await message.answer(t("error.generic"))
        except Exception:  # noqa: BLE001 - best-effort user notification only
            logger.error("failed_to_send_error_message", extra={"update_id": update.update_id})

    return True
