"""Auth middleware: resolves telegram_id -> {directusUserId, isTemp, country}.

FR-BOT-001 §5 / FEAT-BOT-1 AC-7: calls POST /v1/internal/telegram/lookup
via ApiClient on every inbound update and attaches the resolved user
context to the handler's data dict under the "user_context" key.

Interpretation of the 404 case (documented per the task instruction to
state this explicitly rather than silently pick a behavior):

FR-BOT-001 AC-6 requires /start to work "within 3 seconds" even for
brand-new users who have never been seen before — at that point, no
Authentik user exists yet, so the lookup endpoint correctly returns 404
(`telegram_user_not_found`, AC-3 on the API side). Hard-blocking the
update on 404 would break /start for every first-time user, which
directly contradicts AC-6. Instead, this middleware treats 404 as a valid,
expected outcome ("unknown user") rather than an error: it attaches a
`UserContext` with `is_known=False` and lets the update reach the handler.
Handlers that require a known user (none exist yet in this FR's scope —
only /start and the unknown-command fallback, both of which work for
unknown users) are expected to check `user_context.is_known` themselves in
future FRs (FR-BOT-002/003) before doing anything that needs a resolved
identity.

A genuine API-down condition (`ApiUnavailableError` — network error,
timeout, 5xx, or an auth failure against our own shared secret) is
different: that is not "unknown user," it's "we can't tell right now," so
the update is still let through (so /start keeps responding within the
3-second AC even if the lookup call is slow/erroring) but with
`is_known=None` so a future handler can distinguish "confirmed unknown"
from "couldn't check" if it ever needs to. This scaffold does not
hard-block on this path either — over-blocking on an API hiccup would
make the bot appear completely dead, which is worse than degraded.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.middlewares._util import extract_telegram_id
from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    TelegramUserNotFoundError,
)
from src.services.user_cache import UserCache

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UserContext:
    """Resolved (or unresolved) identity for the current update.

    is_known:
        True  -> lookup succeeded, an Authentik user exists for this telegram_id.
        False -> lookup returned 404, confirmed no Authentik user yet.
        None  -> lookup could not be completed (API unavailable); unknown status.
    """

    telegram_id: str
    is_known: bool | None
    directus_user_id: str | None
    is_temp: bool
    country: str | None


class AuthMiddleware(BaseMiddleware):
    """Resolves the calling user via the internal API on every update."""

    def __init__(self, api_client: ApiClient, cache: UserCache | None = None) -> None:
        self._api_client = api_client
        self._cache = cache

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id = extract_telegram_id(event)
        if telegram_id is None:
            data["user_context"] = None
            return await handler(event, data)

        data["user_context"] = await self._resolve(telegram_id)
        return await handler(event, data)

    async def _resolve(self, telegram_id: str) -> UserContext:
        try:
            result = await self._api_client.lookup_telegram_user(telegram_id)
        except TelegramUserNotFoundError:
            if self._cache is not None:
                self._cache.set(telegram_id, None)
            return UserContext(
                telegram_id=telegram_id,
                is_known=False,
                directus_user_id=None,
                is_temp=False,
                country=None,
            )
        except ApiUnavailableError:
            logger.warning(
                "lookup_unavailable",
                extra={"telegram_id": telegram_id},
            )
            cached_id = self._cache.get(telegram_id) if self._cache is not None else None
            return UserContext(
                telegram_id=telegram_id,
                is_known=None,
                directus_user_id=cached_id,
                is_temp=False,
                country=None,
            )

        if self._cache is not None:
            self._cache.set(telegram_id, result.directus_user_id)

        return UserContext(
            telegram_id=telegram_id,
            is_known=True,
            directus_user_id=result.directus_user_id,
            is_temp=result.is_temp,
            country=result.country,
        )
