"""`/interests` handler (FR-BOT-002 PR 5/6).

Shows the member's current topic interests as toggle buttons; tapping a
topic adds or removes it, re-rendering the message in place (matching
events.py's handle_events_page_callback in-place-edit precedent —
callback.message.edit_text(...), NOT me.py's toast-only pattern, since a
toggle button's whole point is showing its own new state immediately).

Guard pattern mirrors leaderboard.py's exact guard (user_context None /
not is_known / no directus_user_id -> event.unavailable message) but
deliberately does NOT copy leaderboard's country check — interests are
not tenant-scoped (no country_code column on member_interests; see
telegram-auth.service.ts's interestsQuerySchema comment), so there is no
country guard to add here.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.keyboards.interests import INTEREST_TOGGLE_PREFIX, interests_keyboard
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient, ApiUnavailableError, InterestsResult

router = Router(name="interests")


def _render_interests_text(lang: str) -> str:
    return t("interests.title", lang)


async def _answer_interests(
    *, api_client: ApiClient, directus_user_id: str, lang: str
) -> tuple[str, object]:
    """Shared fetch+render for both the command and the toggle callback.

    Returns (text, keyboard) so both call sites format the reply
    identically — mirrors events.py's _answer_events_page helper.
    """
    try:
        result = await api_client.get_interests(directus_user_id=directus_user_id)
    except ApiUnavailableError:
        return t("interests.unavailable", lang), None

    return _render_interests_text(lang), _keyboard_for(result, lang)


def _keyboard_for(result: InterestsResult, lang: str):
    return interests_keyboard(available=result.available, selected=result.selected, lang=lang)


@router.message(Command("interests"))
async def handle_interests(
    message: Message,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    if user_context is None or not user_context.is_known or user_context.directus_user_id is None:
        await message.answer(t("event.unavailable", lang))
        return

    text, keyboard = await _answer_interests(
        api_client=api_client, directus_user_id=user_context.directus_user_id, lang=lang
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(
    lambda c: c.data is not None and c.data.startswith(f"{INTEREST_TOGGLE_PREFIX}:")
)
async def handle_interest_toggle_callback(
    callback: CallbackQuery,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    if callback.data is None or callback.message is None:
        await callback.answer()
        return

    if user_context is None or not user_context.is_known or user_context.directus_user_id is None:
        await callback.message.edit_text(t("event.unavailable", lang))
        await callback.answer()
        return

    topic = callback.data.split(":", 1)[1]

    try:
        result = await api_client.toggle_interest(
            directus_user_id=user_context.directus_user_id, topic=topic
        )
    except ApiUnavailableError:
        await callback.message.edit_text(t("interests.unavailable", lang))
        await callback.answer()
        return

    await callback.message.edit_text(
        _render_interests_text(lang), reply_markup=_keyboard_for(result, lang)
    )
    await callback.answer()
