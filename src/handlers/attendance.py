"""`/attendance <event_id>` handler (FR-BOT-003).

Operator-only command. Shows live confirmed / checked-in / waitlist counts
for a specific event. Operators re-run the command to refresh (no live push).
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient, ApiUnavailableError, EventNotFoundError

router = Router(name="attendance")

_ACCESS_DENIED_KEY = "operator.access_denied"


@router.message(Command("attendance"))
async def handle_attendance(
    message: Message,
    command: CommandObject,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"

    if user_context is None or not user_context.is_known or not user_context.is_operator():
        await message.answer(t(_ACCESS_DENIED_KEY, lang))
        return

    event_id = (command.args or "").strip()
    if not event_id:
        await message.answer(t("attendance.usage", lang))
        return

    if user_context.country is None:
        await message.answer(t("events.unavailable", lang))
        return

    try:
        counts = await api_client.get_attendance(
            event_id=event_id, country=user_context.country
        )
    except EventNotFoundError:
        await message.answer(t("event.not_found", lang))
        return
    except ApiUnavailableError:
        await message.answer(t("event.unavailable", lang))
        return

    await message.answer(
        t("attendance.result", lang).format(
            title=counts.event_title,
            registered=counts.registered,
            attended=counts.attended,
            waitlisted=counts.waitlisted,
        )
    )
