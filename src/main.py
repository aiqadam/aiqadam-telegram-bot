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
from aiogram.types import BotCommand

from src import error_handler
from src.config import Settings, load_settings
from src.handlers import cancel, event_detail, events, fallback, leaderboard, me, start
from src.handlers import help as help_handler
from src.logging_setup import configure_logging
from src.middlewares.auth import AuthMiddleware
from src.middlewares.logging_middleware import LoggingMiddleware
from src.middlewares.rate_limit import RateLimitMiddleware
from src.middlewares.tenant import TenantMiddleware
from src.services.api_client import ApiClient
from src.services.user_cache import UserCache

logger = logging.getLogger("bot.main")

# FR-BOT-002 Notes: "The bot registers commands with BotFather via
# set_my_commands on startup." Only argument-LESS commands belong here —
# BotFather's own command menu convention has no way to express a required
# argument. /event, /register, and /cancel all take a required id, so all
# three are intentionally excluded; users invoke e.g. "/register <id>" as
# free text, matched by the handler's own Command("register") filter +
# CommandObject.args, same mechanism BotFather-registered commands use
# under the hood — the only difference is whether it appears in Telegram's
# command-menu UI. /me (FR-BOT-002 PR 3/6) and /leaderboard (PR 4/6) take
# no argument, so both belong in this menu like /events and /help.
BOT_COMMANDS = (
    BotCommand(command="start", description="Начать / выбрать страну"),
    BotCommand(command="events", description="Ближайшие мероприятия"),
    BotCommand(command="me", description="Мои записи и статус аккаунта"),
    BotCommand(command="leaderboard", description="Таблица лидеров"),
    BotCommand(command="help", description="Список команд"),
)


def build_dispatcher(settings: Settings, api_client: ApiClient, cache: UserCache) -> Dispatcher:
    dispatcher = Dispatcher()
    # Workflow data: available to every handler as a named parameter
    # (aiogram's dependency injection matches by name), same as the
    # "message"/"callback" parameters aiogram injects natively. api_client
    # is a long-lived singleton constructed once in run() below.
    dispatcher["api_client"] = api_client

    # Middleware order matters (FR-BOT-001 §5): logging (outermost, times
    # everything) -> rate-limit (reject before any API call is made) ->
    # auth (resolve identity) -> tenant (derive country from identity).
    dispatcher.update.outer_middleware(LoggingMiddleware())
    dispatcher.update.outer_middleware(RateLimitMiddleware(settings.rate_limit_per_minute))
    dispatcher.update.outer_middleware(AuthMiddleware(api_client, cache))
    dispatcher.update.outer_middleware(TenantMiddleware())

    # /start must be registered before the unknown-command fallback, since
    # aiogram routers are matched in registration order and the fallback
    # matches any "/..." text. help/events/event_detail/cancel are all
    # specific Command() filters, so their relative order versus each
    # other doesn't matter — only "before fallback" does.
    dispatcher.include_router(start.router)
    dispatcher.include_router(help_handler.router)
    dispatcher.include_router(events.router)
    dispatcher.include_router(event_detail.router)
    dispatcher.include_router(cancel.router)
    dispatcher.include_router(me.router)
    dispatcher.include_router(leaderboard.router)
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
        await bot.set_my_commands(list(BOT_COMMANDS))
        await dispatcher.start_polling(bot)
    finally:
        await api_client.aclose()
        cache.close()
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
