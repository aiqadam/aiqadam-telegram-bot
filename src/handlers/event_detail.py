"""`/event <N>` handler (FR-BOT-002 PR 1/6) + `/register <N>` / `/cancel <N>`
(FR-BOT-002 PR 2/6).

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
Its callback (handle_register_callback below) now performs a real
registration (FR-BOT-002 PR 2/6) — PR 1 shipped it as a deliberate
no-op placeholder; this PR wires it to the same registration logic as
the /register <N> command, per the task brief's explicit instruction.

/register and /cancel, like /event, are excluded from BotFather's
argument-less command menu (main.py's BOT_COMMANDS) for the same reason.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from src.keyboards.events import EVENT_REGISTER_PREFIX, event_detail_keyboard
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    EventDetail,
    EventNotFoundError,
    RegisterResult,
    RegistrationConsentRequiredError,
    RegistrationIneligibleError,
)

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


def _confirmation_text(result: RegisterResult, lang: str) -> str:
    """Renders one of the two distinct confirmation messages (FR-BOT-002
    AC-1/AC-2), keyed off the service's own status field — no separate
    waitlist-detection logic here, per the task brief's explicit
    instruction. Falls back to the 'registered' copy for the
    'cancelled'/'attended' values RegistrationsDirectusService's Status
    union technically allows but register() never actually returns.
    """
    if result.status == "waitlisted":
        return t("register.waitlisted", lang).format(title=result.event_title)
    return t("register.confirmed", lang).format(title=result.event_title)


async def _do_register(
    *, api_client: ApiClient, user_context: UserContext | None, event_id: str, lang: str
) -> str:
    """Shared register logic for the /register command and the Register
    button callback — both need identical API-call + error-mapping
    behavior, so this is the single place that owns it (mirrors
    events.py's own _answer_events_page sharing pattern).

    Returns the message text to show; callers decide how to deliver it
    (message.answer vs. callback.answer/show_alert).
    """
    if user_context is None or not user_context.is_known or user_context.directus_user_id is None:
        return t("event.unavailable", lang)
    if user_context.country is None:
        return t("events.unavailable", lang)

    try:
        result = await api_client.register_for_event(
            directus_user_id=user_context.directus_user_id,
            event_id=event_id,
            country=user_context.country,
        )
    except EventNotFoundError:
        return t("event.not_found", lang)
    except RegistrationConsentRequiredError:
        return t("register.consent_required", lang)
    except RegistrationIneligibleError:
        return t("register.ineligible", lang)
    except ApiUnavailableError:
        return t("event.unavailable", lang)

    return _confirmation_text(result, lang)


@router.message(Command("register"))
async def handle_register_command(
    message: Message,
    command: CommandObject,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    event_id = (command.args or "").strip()
    if not event_id:
        await message.answer(t("register.usage", lang))
        return

    text = await _do_register(
        api_client=api_client, user_context=user_context, event_id=event_id, lang=lang
    )
    await message.answer(text)


@router.callback_query(
    lambda c: c.data is not None and c.data.startswith(f"{EVENT_REGISTER_PREFIX}:")
)
async def handle_register_callback(
    callback: CallbackQuery, api_client: ApiClient, user_context: UserContext | None
) -> None:
    """Register/"I'm going" button callback (FR-BOT-002 PR 2/6).

    PR 1 shipped this as a placeholder toast; this is the PR that makes it
    real, per the task brief's explicit instruction. Reuses `_do_register`
    so the button and the /register command behave identically. Shown via
    `callback.answer(show_alert=True)` — same delivery mechanism PR 1's
    placeholder already used, so tapping the button always gives visible
    feedback even though the underlying message isn't re-rendered (that
    would need re-fetching event detail to redraw the keyboard, which is
    a nice-to-have left for a future polish pass, not required by any
    FR-BOT-002 AC).
    """
    if callback.data is None:
        await callback.answer()
        return
    event_id = callback.data.split(":", 1)[1]

    text = await _do_register(
        api_client=api_client, user_context=user_context, event_id=event_id, lang="ru"
    )
    await callback.answer(text, show_alert=True)
