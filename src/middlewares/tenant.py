"""Tenant middleware: sets country from the resolved user context.

FR-BOT-001 §5: "tenant middleware (sets country from user's
country_preference)". Must run AFTER AuthMiddleware, since it reads the
`user_context` key AuthMiddleware attaches to `data`. Attaches `country`
directly to `data` so handlers can depend on it without reaching into
`user_context` themselves.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.middlewares.auth import UserContext


class TenantMiddleware(BaseMiddleware):
    """Derives the current update's tenant (country) from user_context."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_context: UserContext | None = data.get("user_context")
        data["country"] = user_context.country if user_context is not None else None
        return await handler(event, data)
