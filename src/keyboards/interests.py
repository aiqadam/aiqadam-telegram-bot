"""Inline keyboard for `/interests` (FEAT-BOT-2, FR-BOT-002 PR 5/6).

One button per topic, `[x]`/`[ ]` bracket-marker prefix per selected
state — a plain bracket marker, not emoji-as-state, per the task brief:
this bot's existing emoji usage elsewhere (events.button_next/button_prev's
➡️/⬅️) is a navigation affordance, not a state encoding, so a bracket
marker here is a deliberately different, unambiguous convention for a
toggle's on/off state.

Topic order and labels come from `INTERESTS_TOPIC_ORDER` below — the same
7 slugs the API's INTEREST_TOPICS constant returns (telegram-auth.service.ts),
kept in that same fixed order so the keyboard's button order matches the
API response's `available` list deterministically.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.locales import t

# Callback data prefix, same short-prefix convention as
# keyboards/events.py's EVENTS_PAGE_PREFIX / keyboards/me.py's
# ME_CANCEL_PREFIX (Telegram caps callback_data at 64 bytes). Format:
# "<prefix>:<slug>" — even the longest slug (computer-vision) stays well
# under the limit with this short prefix.
INTEREST_TOGGLE_PREFIX = "inttog"

# Fixed slug order — mirrors telegram-auth.service.ts's INTEREST_TOPICS
# constant exactly (same 7 slugs, same order). Duplicated here for the
# same reason that constant is itself a duplicate of
# TelegramEventTopicsService's KNOWN_EVENT_TOPICS: the bot has no server
# call that returns ordering guarantees beyond the API's own `available`
# list, and keeping a local, stable order means the keyboard's button
# order does not silently reshuffle if the API ever changes its own
# internal Set/array iteration order.
INTERESTS_TOPIC_ORDER: tuple[str, ...] = (
    "llm",
    "mlops",
    "computer-vision",
    "product",
    "career",
    "ethics",
    "infra",
)

SELECTED_MARKER = "[x]"
UNSELECTED_MARKER = "[ ]"


def _topic_label(slug: str, lang: str) -> str:
    return t(f"interests.topic.{slug}", lang)


def interests_keyboard(
    *, available: list[str], selected: list[str], lang: str = "ru"
) -> InlineKeyboardMarkup:
    """Build one button per topic in `available`, ordered per
    INTERESTS_TOPIC_ORDER, `[x] <label>` when the slug is in `selected`
    else `[ ] <label>`. One button per row (7 short rows reads more
    clearly on mobile than a cramped grid for label lengths like
    "Компьютерное зрение").
    """
    selected_set = set(selected)
    available_set = set(available)
    ordered_slugs = [slug for slug in INTERESTS_TOPIC_ORDER if slug in available_set]

    rows = [
        [
            InlineKeyboardButton(
                text=_button_text(slug, slug in selected_set, lang),
                callback_data=f"{INTEREST_TOGGLE_PREFIX}:{slug}",
            )
        ]
        for slug in ordered_slugs
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _button_text(slug: str, is_selected: bool, lang: str) -> str:
    marker = SELECTED_MARKER if is_selected else UNSELECTED_MARKER
    return f"{marker} {_topic_label(slug, lang)}"
