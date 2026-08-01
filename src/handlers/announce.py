"""`/announce <event_id>` handler (FR-BOT-003).

Operator-only FSM command. Prompts for a message body, confirms the audience
count, then sends the announcement to all confirmed registrants via the API's
push-announcement endpoint.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient, ApiUnavailableError, EventNotFoundError
from src.states.announce import AnnounceStates

router = Router(name="announce")

_ACCESS_DENIED_KEY = "operator.access_denied"
_MAX_MESSAGE_LENGTH = 4000


@router.message(Command("announce"))
async def handle_announce_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    user_context: UserContext | None,
) -> None:
    lang = "ru"

    if user_context is None or not user_context.is_known or not user_context.is_operator():
        await message.answer(t(_ACCESS_DENIED_KEY, lang))
        return

    event_id = (command.args or "").strip()
    if not event_id:
        await message.answer(t("announce.usage", lang))
        return

    if user_context.directus_user_id is None or user_context.country is None:
        await message.answer(t("events.unavailable", lang))
        return

    await state.update_data(
        event_id=event_id,
        country=user_context.country,
        directus_user_id=user_context.directus_user_id,
    )
    await state.set_state(AnnounceStates.awaiting_message)
    await message.answer(t("announce.prompt_message", lang))


@router.message(AnnounceStates.awaiting_message)
async def handle_announce_message(
    message: Message,
    state: FSMContext,
    api_client: ApiClient,
) -> None:
    lang = "ru"
    text = (message.text or "").strip()

    if not text:
        await message.answer(t("announce.empty_message", lang))
        return

    if len(text) > _MAX_MESSAGE_LENGTH:
        await message.answer(t("announce.message_too_long", lang))
        return

    data = await state.get_data()
    await state.clear()

    event_id: str = data.get("event_id", "")
    country: str = data.get("country", "")
    directus_user_id: str = data.get("directus_user_id", "")

    try:
        result = await api_client.push_announcement(
            event_id=event_id,
            message=text,
            country=country,
            directus_user_id=directus_user_id,
        )
    except EventNotFoundError:
        await message.answer(t("event.not_found", lang))
        return
    except ApiUnavailableError:
        await message.answer(t("event.unavailable", lang))
        return

    await message.answer(
        t("announce.sent", lang).format(count=result.recipient_count)
    )
