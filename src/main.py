"""Entry point: long-polling aiogram bot (FR-BOT-001).

No webhook server, no public FQDN — Telegram is reached via outbound
long-polling only (ADR-0034 §Q4).
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src import error_handler
from src.config import Settings, load_settings
from src.handlers import fallback, start
from src.logging_setup import configure_logging
from src.middlewares.auth import AuthMiddleware
from src.middlewares.logging_middleware import LoggingMiddleware
from src.middlewares.rate_limit import RateLimitMiddleware
from src.middlewares.tenant import TenantMiddleware
from src.services.api_client import ApiClient
from src.services.user_cache import UserCache

logger = logging.getLogger("bot.main")


def build_dispatcher(settings: Settings, api_client: ApiClient, cache: UserCache) -> Dispatcher:
    dispatcher = Dispatcher()

    # Middleware order matters (FR-BOT-001 §5): logging (outermost, times
    # everything) -> rate-limit (reject before any API call is made) ->
    # auth (resolve identity) -> tenant (derive country from identity).
    dispatcher.update.outer_middleware(LoggingMiddleware())
    dispatcher.update.outer_middleware(RateLimitMiddleware(settings.rate_limit_per_minute))
    dispatcher.update.outer_middleware(AuthMiddleware(api_client, cache))
    dispatcher.update.outer_middleware(TenantMiddleware())

    # /start must be registered before the unknown-command fallback, since
    # aiogram routers are matched in registration order and the fallback
    # matches any "/..." text.
    dispatcher.include_router(start.router)
    dispatcher.include_router(fallback.router)
    dispatcher.include_router(error_handler.router)

    return dispatcher


async def run() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    api_client = ApiClient(
        settings.internal_api_url,
        settings.internal_api_token,
        timeout_seconds=settings.http_timeout_seconds,
    )
    cache = UserCache(settings.sqlite_full_path)

    dispatcher = build_dispatcher(settings, api_client, cache)

    logger.info("bot_starting")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await api_client.aclose()
        cache.close()
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
