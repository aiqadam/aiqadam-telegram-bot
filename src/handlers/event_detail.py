"""`/event <N>` handler (FR-BOT-002 PR 1/6).

Shows full detail for one event. `<N>` is a free-text command argument
(NOT a bare BotFather-registered command — BotFather commands are
argument-less by convention, see main.py's set_my_commands call and its
comment for why /event is intentionally excluded from that list). Matches
this file's own `Command("event")` filter, which aiogram parses the same
way `Command("start")` does in handlers/start.py — the difference is this
handler additionally reads `command.args` for the identifier argument.

Note on "<N>": FR-BOT-002's functional-scope table uses `<N>` as informal
shorthand for "an event identifier." There is no separate short numeric
event-number field in the events schema — `events.id` is a UUID (see
telegram-auth.service.ts's eventDetailParamsSchema, and
TelegramEventsService's own slug-or-id fallback, which documents the same
UUID-shaped id). So `<N>` here is literally the event's UUID, which
/events's own list output prints under each event (see
handlers/events.py's "events.item" locale string) so a user can copy it.
A future PR could add a shorter per-tenant sequence number if this proves
too unwieldy in practice — not attempted here since it would need a new
schema column, out of scope for a read-only slice.

Includes an inline Register/"I'm going" button (event_detail_keyboard).
Its callback (handle_register_placeholder below) is a deliberate no-op
placeholder: actual registration is PR 2 of this FR's 6-PR sequence
(/register). Tapping the button today shows event.register_placeholder
rather than crashing or doing nothing silently — documented here per the
task's explicit instruction not to ship a dead button with no explanation.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from src.keyboards.events import EVENT_REGISTER_PREFIX, event_detail_keyboard
from src.locales import t
from src.services.api_client import ApiClient, ApiUnavailableError, EventDetail, EventNotFoundError

router = Router(name="event_detail")


def render_event_detail(event: EventDetail, lang: str) -> str:
    from src.handlers.events import format_event_date  # local import avoids a cycle at module load

    venue_line = t("event.venue_line", lang).format(venue=event.venue) if event.venue else ""
    capacity_line = (
        t("event.capacity_line", lang).format(capacity=event.capacity)
        if event.capacity is not None
        else ""
    )
    return t("event.detail", lang).format(
        title=event.title,
        date=format_event_date(event.starts_at),
        venue_line=venue_line,
        registered=event.registration_count,
        capacity_line=capacity_line,
        description=event.description,
    )


@router.message(Command("event"))
async def handle_event_detail(
    message: Message,
    command: CommandObject,
    api_client: ApiClient,
    user_context: object | None,
) -> None:
    lang = "ru"
    event_id = (command.args or "").strip()
    if not event_id:
        await message.answer(t("events.usage", lang))
        return

    directus_user_id = getattr(user_context, "directus_user_id", None)

    try:
        event = await api_client.get_event_detail(event_id, directus_user_id=directus_user_id)
    except EventNotFoundError:
        await message.answer(t("event.not_found", lang))
        return
    except ApiUnavailableError:
        await message.answer(t("event.unavailable", lang))
        return

    keyboard = event_detail_keyboard(
        event_id=event.id, is_registered=event.is_registered, lang=lang
    )
    await message.answer(render_event_detail(event, lang), reply_markup=keyboard)


@router.callback_query(
    lambda c: c.data is not None and c.data.startswith(f"{EVENT_REGISTER_PREFIX}:")
)
async def handle_register_placeholder(callback: CallbackQuery) -> None:
    """Placeholder for the Register/"I'm going" button — see module docstring.

    /register ships in PR 2 of this FR's sequence; until then this shows a
    friendly "coming soon" toast (callback.answer with show_alert) rather
    than silently doing nothing or crashing on an unhandled callback.
    """
    await callback.answer(t("event.register_placeholder"), show_alert=True)
