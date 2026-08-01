"""Inline keyboard for `/approvals` (FR-BOT-003).

One Approve + one Decline button per pending approval row, stacked vertically.
Callback data format: "<prefix>:<registration_id>".
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.locales import t
from src.services.api_client import PendingApprovalItem

APPROVE_PREFIX = "approv"
DECLINE_PREFIX = "declin"


def approvals_keyboard(
    items: list[PendingApprovalItem], lang: str = "ru"
) -> InlineKeyboardMarkup | None:
    """One approve/decline row per pending approval item.

    Returns None when there are no items — callers skip the reply_markup.
    """
    if not items:
        return None

    buttons: list[list[InlineKeyboardButton]] = []
    for item in items:
        reg_id = item.registration_id
        buttons.append([
            InlineKeyboardButton(
                text=t("approvals.button_approve", lang),
                callback_data=f"{APPROVE_PREFIX}:{reg_id}",
            ),
            InlineKeyboardButton(
                text=t("approvals.button_decline", lang),
                callback_data=f"{DECLINE_PREFIX}:{reg_id}",
            ),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
