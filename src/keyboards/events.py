"""Inline keyboards for /events and /event <N> (FEAT-BOT-2, FR-BOT-002 PR 1/6).

First real keyboards in the bot — keyboards/__init__.py's stub docstring
said these would land alongside FR-BOT-002; this is that PR.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.locales import t

# Callback data prefixes — kept short (Telegram caps callback_data at 64
# bytes). Format: "<prefix>:<offset>" for pagination, "<prefix>:<event_id>"
# for the per-event actions.
EVENTS_PAGE_PREFIX = "evpg"
EVENT_REGISTER_PREFIX = "evreg"


def events_page_keyboard(
    *, offset: int, limit: int, total: int, lang: str = "ru"
) -> InlineKeyboardMarkup | None:
    """Build the "Next page" / "Previous page" row for /events.

    Returns None when there's only one page (nothing to paginate) — the
    handler skips attaching a keyboard in that case, matching
    FR-BOT-002 Notes: "Paginated if > 5 events."
    """
    has_prev = offset > 0
    has_next = offset + limit < total
    if not has_prev and not has_next:
        return None

    row: list[InlineKeyboardButton] = []
    if has_prev:
        prev_offset = max(offset - limit, 0)
        row.append(
            InlineKeyboardButton(
                text=t("events.button_prev", lang),
                callback_data=f"{EVENTS_PAGE_PREFIX}:{prev_offset}",
            )
        )
    if has_next:
        next_offset = offset + limit
        row.append(
            InlineKeyboardButton(
                text=t("events.button_next", lang),
                callback_data=f"{EVENTS_PAGE_PREFIX}:{next_offset}",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[row])


def event_detail_keyboard(
    *, event_id: str, is_registered: bool, lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Build the Register / "I'm going" button for /event <N>.

    FEAT-BOT-2 PR 2/6: this button's callback now performs a real
    registration (see handlers/event_detail.py's handle_register_callback)
    — PR 1 shipped it as a placeholder toast. is_registered controls only
    the label; there is still no separate "cancel" affordance on this
    button (cancelling uses the standalone /cancel <N> command; a Cancel
    button here is deferred to PR 3's /me registration list).
    """
    label = t("event.button_going", lang) if is_registered else t("event.button_register", lang)
    button = InlineKeyboardButton(
        text=label,
        callback_data=f"{EVENT_REGISTER_PREFIX}:{event_id}",
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])
