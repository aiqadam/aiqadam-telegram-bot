"""Shared helpers for middleware implementations.

Private module (leading underscore) — not part of the public middleware
surface, just deduplicated logic used by rate_limit.py, auth.py,
logging_middleware.py.
"""

from __future__ import annotations

from aiogram.types import TelegramObject, Update


def extract_telegram_id(event: TelegramObject) -> str | None:
    """Best-effort extraction of the sending user's telegram_id from an update."""
    update = event if isinstance(event, Update) else None
    user = None
    if update is not None:
        if update.message is not None:
            user = update.message.from_user
        elif update.callback_query is not None:
            user = update.callback_query.from_user
    else:
        user = getattr(event, "from_user", None)

    return str(user.id) if user is not None else None


def extract_command(event: TelegramObject) -> str | None:
    """Extract the leading /command token (without @botname suffix), if any."""
    update = event if isinstance(event, Update) else None
    text = update.message.text if update is not None and update.message is not None else None
    if not text or not text.startswith("/"):
        return None
    return text.split()[0].split("@")[0]
