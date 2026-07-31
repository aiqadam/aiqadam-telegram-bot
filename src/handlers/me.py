"""`/me` handler (FR-BOT-002 PR 3/6).

Shows the caller's active registrations (with status badges + a Cancel
button per row), lifetime points total, and — for temp accounts — an
upgrade nudge, plus a generic "link your account on the web" CTA.

Two things this command deliberately does NOT show, both documented as
scope decisions in this PR (see
.copilot/tasks/active/wf-20260801-feat-176/01-requirement-validation.md
for the full reasoning, not repeated here in full):

1. **Streak.** No streak concept, column, or calculation exists anywhere
   in this codebase, and no FR-BOT-002 AC tests one. Rather than invent a
   scoring rule (a genuine product decision, not an implementation
   detail — AGENTS.md SS13/SS14), it is simply omitted. This is a named
   scope gap, not a silently dropped feature.
2. **A computed "is linked to web" boolean.** The only "linked" concept
   anywhere in this repo (directus_users.telegram_user_id, ADR-0033) is
   owned by a different, superseded auth surface
   (apps/api/src/modules/telegram/, pre-ADR-0034) that this bot's
   identity model (Authentik attributes, resolved via
   TelegramAuthService.lookupUser) has no relationship to. Rather than
   conflate the two systems, /me always shows the same generic
   "link on web" CTA line — harmless whether or not the user has done so,
   same posture as /help's "(coming soon)" labels for not-yet-built
   commands.

Account type (temp vs. full) needs no new API call — it's already on
user_context.is_temp, attached by AuthMiddleware on every update (see
middlewares/auth.py). Registrations + points total come from the one new
GET /v1/internal/telegram/me call this PR adds.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.handlers.events import format_event_date
from src.keyboards.me import ME_CANCEL_PREFIX, me_registrations_keyboard
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    EventNotFoundError,
    MeRegistration,
    MeSummary,
)

router = Router(name="me")

# Maps the API's registration status union to the locale key for its
# badge. 'cancelled' is intentionally absent — listMine's own server-side
# filter (filter[status][_neq]=cancelled) means the bot never receives a
# cancelled row here, so there is no badge to render for it.
_STATUS_BADGE_KEYS = {
    "registered": "me.status_registered",
    "waitlisted": "me.status_waitlisted",
    "attended": "me.status_attended",
}


def _status_badge(status: str, lang: str) -> str:
    """Falls back to the raw status string for any value outside the
    three known ones — defensive against a future status the bot doesn't
    know about yet, rather than crashing render.
    """
    key = _STATUS_BADGE_KEYS.get(status)
    return t(key, lang) if key else status.upper()


def _render_registrations(registrations: list[MeRegistration], lang: str) -> list[str]:
    if not registrations:
        return [t("me.registrations_title", lang), t("me.registrations_empty", lang)]

    lines = [t("me.registrations_title", lang)]
    for reg in registrations:
        lines.append(
            t("me.registration_item", lang).format(
                status_badge=_status_badge(reg.status, lang),
                title=reg.event.title,
                date=format_event_date(reg.event.starts_at),
            )
        )
    return lines


def render_me(summary: MeSummary, *, is_temp: bool, lang: str) -> str:
    lines = [t("me.title", lang), ""]
    lines.extend(_render_registrations(summary.registrations, lang))
    lines.append("")
    lines.append(t("me.points_total", lang).format(points=summary.points_total))
    if is_temp:
        lines.append("")
        lines.append(t("me.temp_account_nudge", lang))
    lines.append("")
    lines.append(t("me.link_web_cta", lang))
    return "\n".join(lines)


@router.message(Command("me"))
async def handle_me(
    message: Message,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    if user_context is None or not user_context.is_known or user_context.directus_user_id is None:
        await message.answer(t("event.unavailable", lang))
        return
    if user_context.country is None:
        await message.answer(t("events.unavailable", lang))
        return

    try:
        summary = await api_client.get_me_summary(
            directus_user_id=user_context.directus_user_id,
            country=user_context.country,
        )
    except ApiUnavailableError:
        await message.answer(t("me.unavailable", lang))
        return

    text = render_me(summary, is_temp=user_context.is_temp, lang=lang)
    keyboard = me_registrations_keyboard(summary.registrations, lang)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data is not None and c.data.startswith(f"{ME_CANCEL_PREFIX}:"))
async def handle_me_cancel_callback(
    callback: CallbackQuery, api_client: ApiClient, user_context: UserContext | None
) -> None:
    """Cancel button on a /me registration row.

    Reuses the same cancel_registration API call /cancel <N> already
    makes — no new cancellation logic, only a new trigger surface. Shown
    via callback.answer(show_alert=True), same delivery mechanism
    event_detail.py's Register button callback already established, so
    tapping always gives visible feedback even though the underlying
    message isn't re-rendered (re-fetching /me to redraw the list is a
    nice-to-have left for a future polish pass, same deferral
    event_detail.py's own callback already documented for itself).
    """
    lang = "ru"
    if callback.data is None:
        await callback.answer()
        return
    event_id = callback.data.split(":", 1)[1]

    if user_context is None or not user_context.is_known or user_context.directus_user_id is None:
        await callback.answer(t("event.unavailable", lang), show_alert=True)
        return
    if user_context.country is None:
        await callback.answer(t("events.unavailable", lang), show_alert=True)
        return

    try:
        result = await api_client.cancel_registration(
            directus_user_id=user_context.directus_user_id,
            event_id=event_id,
            country=user_context.country,
        )
    except EventNotFoundError:
        await callback.answer(t("event.not_found", lang), show_alert=True)
        return
    except ApiUnavailableError:
        await callback.answer(t("event.unavailable", lang), show_alert=True)
        return

    if result.status == "not_registered":
        await callback.answer(t("cancel.not_registered", lang), show_alert=True)
        return
    await callback.answer(t("cancel.confirmed", lang), show_alert=True)
