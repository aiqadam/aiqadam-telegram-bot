"""Inline keyboard for `/me` (FEAT-BOT-2, FR-BOT-002 PR 3/6).

One Cancel button per active registration row — event_detail.py's own
module docstring flagged this as deferred to PR 3: "a Cancel button here
is deferred to PR 3's /me registration list." Reuses the existing
/cancel <N> API call (ApiClient.cancel_registration) — no new cancel
logic, only a new trigger surface (button vs. command), same reuse
posture as every other PR in this sequence.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.locales import t
from src.services.api_client import MeRegistration

# Callback data prefix, same short-prefix convention as
# keyboards/events.py's EVENTS_PAGE_PREFIX/EVENT_REGISTER_PREFIX (Telegram
# caps callback_data at 64 bytes). Format: "<prefix>:<event_id>".
ME_CANCEL_PREFIX = "mecxl"


def me_registrations_keyboard(
    registrations: list[MeRegistration], lang: str = "ru"
) -> InlineKeyboardMarkup | None:
    """One Cancel button per row, stacked vertically.

    Returns None when there are no registrations to show a button for —
    matches events_page_keyboard's own "nothing to render, skip the
    keyboard" convention.
    """
    if not registrations:
        return None

    rows = [
        [
            InlineKeyboardButton(
                text=f"{t('me.button_cancel', lang)} — {reg.event.title}",
                callback_data=f"{ME_CANCEL_PREFIX}:{reg.event.id}",
            )
        ]
        for reg in registrations
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
