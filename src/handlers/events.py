"""`/events` handler (FR-BOT-002 PR 1/6).

Lists upcoming events for the caller's country (from TenantMiddleware's
`data["country"]`), 5 per page, with "Next page ->" / "<- Previous page"
inline buttons (offset-based, per FR-BOT-002 Notes).

Country resolution: if `data["country"]` is None (unknown/unresolved
user — see AuthMiddleware's module docstring for the is_known=False/None
cases), this handler cannot know which tenant's events to show, so it
answers with a friendly message rather than guessing a default country or
crashing. This is a new error case beyond FR-BOT-002's documented four
(API unavailable / user not found / event not found / already registered)
— documented here since it wasn't explicitly a listed AC for a read-only
listing command and there is no "user not found" redirect-to-/start
behavior needed for browsing (browsing is intentionally anonymous-safe,
matching TelegramEventsService's own posture on the web side).
"""

from __future__ import annotations

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.keyboards.events import EVENTS_PAGE_PREFIX, events_page_keyboard
from src.locales import t
from src.services.api_client import ApiClient, ApiUnavailableError, EventListResult

router = Router(name="events")

PAGE_SIZE = 5  # FR-BOT-002 Notes: "Paginated if > 5 events."


def format_event_date(iso_starts_at: str) -> str:
    """Render an ISO-8601 starts_at as a short human-readable date/time.

    Falls back to the raw string on any parse failure — a malformed date
    shouldn't crash event rendering, just look a little rough.
    """
    try:
        dt = datetime.fromisoformat(iso_starts_at.replace("Z", "+00:00"))
    except ValueError:
        return iso_starts_at
    return dt.strftime("%d.%m.%Y %H:%M")


def render_events_page(result: EventListResult, lang: str) -> str:
    if not result.items:
        return t("events.empty", lang)

    lines = [t("events.title", lang)]
    for item in result.items:
        lines.append(
            t("events.item", lang).format(
                title=item.title,
                date=format_event_date(item.starts_at),
                count=item.registration_count,
                id=item.id,
            )
        )
    total_pages = max((result.total + result.limit - 1) // result.limit, 1) if result.limit else 1
    current_page = (result.offset // result.limit) + 1 if result.limit else 1
    if result.total > result.limit:
        lines.append("")
        lines.append(t("events.page_info", lang).format(page=current_page, total_pages=total_pages))
    return "\n".join(lines)


async def _answer_events_page(
    *, api_client: ApiClient, country: str | None, offset: int, lang: str
) -> tuple[str, object]:
    """Shared fetch+render for both the command and the pagination callback.

    Returns (text, keyboard-or-None) so both call sites format the reply
    identically.
    """
    if country is None:
        return t("events.unavailable", lang), None

    try:
        result = await api_client.list_events(country, offset=offset, limit=PAGE_SIZE)
    except ApiUnavailableError:
        return t("events.unavailable", lang), None

    text = render_events_page(result, lang)
    keyboard = events_page_keyboard(
        offset=result.offset, limit=result.limit, total=result.total, lang=lang
    )
    return text, keyboard


@router.message(Command("events"))
async def handle_events(message: Message, api_client: ApiClient, country: str | None) -> None:
    text, keyboard = await _answer_events_page(
        api_client=api_client, country=country, offset=0, lang="ru"
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data is not None and c.data.startswith(f"{EVENTS_PAGE_PREFIX}:"))
async def handle_events_page_callback(
    callback: CallbackQuery, api_client: ApiClient, country: str | None
) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return

    offset_str = callback.data.split(":", 1)[1]
    try:
        offset = int(offset_str)
    except ValueError:
        await callback.answer()
        return

    text, keyboard = await _answer_events_page(
        api_client=api_client, country=country, offset=offset, lang="ru"
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
