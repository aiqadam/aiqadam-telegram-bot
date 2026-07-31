"""`/cancel <N>` handler (FR-BOT-002 PR 2/6).

Cancels the caller's registration for event N. No inline-button
counterpart in this PR — a Cancel button on the user's registration list
is PR 3's concern (/me), per FR-BOT-002.md's Implementation progress
table. Kept in its own file rather than folded into event_detail.py
(which already holds /event + /register) since cancel has no shared
render/keyboard logic with event detail — a plain command-in, text-out
handler, same shape as help.py.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient, ApiUnavailableError, EventNotFoundError

router = Router(name="cancel")


@router.message(Command("cancel"))
async def handle_cancel_command(
    message: Message,
    command: CommandObject,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    event_id = (command.args or "").strip()
    if not event_id:
        await message.answer(t("cancel.usage", lang))
        return

    if user_context is None or not user_context.is_known or user_context.directus_user_id is None:
        await message.answer(t("event.unavailable", lang))
        return
    if user_context.country is None:
        await message.answer(t("events.unavailable", lang))
        return

    try:
        result = await api_client.cancel_registration(
            directus_user_id=user_context.directus_user_id,
            event_id=event_id,
            country=user_context.country,
        )
    except EventNotFoundError:
        await message.answer(t("event.not_found", lang))
        return
    except ApiUnavailableError:
        await message.answer(t("event.unavailable", lang))
        return

    if result.status == "not_registered":
        await message.answer(t("cancel.not_registered", lang))
        return
    await message.answer(t("cancel.confirmed", lang))
