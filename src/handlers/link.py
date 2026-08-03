"""`/link` handler (FR-AUTH-005).

Links an existing web-account member to their Telegram identity via a
bot-initiated email-code flow (ADR-0034 §"link flow"). The sequence:
  1. User sends /link — bot prompts for their web-account email.
  2. User sends email — bot calls link/start. API sends a 6-digit OTP
     to that email (if a member account exists; silent otherwise to
     prevent email enumeration).
  3. User sends the code — bot calls link/confirm. On success the
     member's directus_users row gains telegram_user_id + username.

Design decisions:

1. **Available regardless of is_temp.** Both temp and full members can
   run /link (a temp account has a Telegram ID already; the link flow
   is about connecting the *email-based* member record, not about
   temp→full upgrade). No is_temp short-circuit here.

2. **Same _EMAIL_RE as upgrade.py.** Client-side format check as a UX
   nicety before the API round trip; the API's Zod emailField is the
   authoritative boundary.

3. **FSM state is always cleared after each outcome** — on success and
   every error path. A user who wants to retry runs /link again.

4. **challenge_id stored in FSM data.** Between the email-collected step
   and the code-collected step the only cross-message state is
   challenge_id (returned by link/start). The FSM key "challenge_id" is
   named to match the API's own field name for readability in logs.

5. **409 "already linked to same account" handled as success.** The
   original FR-AUTH-005 AC intent is idempotency: if the member is
   re-linking the same TG account the API proceeds normally (the 409
   guard only fires when tg_user_id DIFFERS from the one already stored).
   The bot therefore never sees a 409 for the same-account case —
   link/confirm returns 200. If somehow a 409 still reaches the bot
   (race condition), it is treated as the "linked to different account"
   error and the user is told to contact support.
"""

from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    LinkAlreadyLinkedOtherError,
    LinkInvalidCodeError,
    LinkMemberNotFoundError,
    LinkRateLimitedError,
)
from src.states.link import LinkStates

router = Router(name="link")

# Same pattern as upgrade.py — UX-level guard before spending a round trip.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email_format(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


@router.message(Command("link"))
async def handle_link_command(
    message: Message,
    state: FSMContext,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    if user_context is None or not user_context.is_known:
        await message.answer(t("event.unavailable", lang))
        return

    await state.set_state(LinkStates.awaiting_email)
    await message.answer(t("link.prompt_email", lang))


@router.message(LinkStates.awaiting_email)
async def handle_link_email_reply(
    message: Message,
    state: FSMContext,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    email = (message.text or "").strip()

    if not _is_valid_email_format(email):
        await message.answer(t("link.invalid_email", lang))
        return

    if user_context is None or not user_context.is_known:
        await state.clear()
        await message.answer(t("event.unavailable", lang))
        return

    try:
        result = await api_client.request_link_start(
            telegram_id=user_context.telegram_id,
            email=email,
        )
    except LinkRateLimitedError:
        await state.clear()
        await message.answer(t("link.rate_limited", lang))
        return
    except ApiUnavailableError:
        await state.clear()
        await message.answer(t("link.unavailable", lang))
        return

    await state.update_data(challenge_id=result.challenge_id)
    await state.set_state(LinkStates.awaiting_code)
    await message.answer(t("link.code_sent", lang).format(email=result.sent_to_email_masked))


@router.message(LinkStates.awaiting_code)
async def handle_link_code_reply(
    message: Message,
    state: FSMContext,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    code = (message.text or "").strip()

    if user_context is None or not user_context.is_known:
        await state.clear()
        await message.answer(t("event.unavailable", lang))
        return

    data = await state.get_data()
    challenge_id: str | None = data.get("challenge_id")
    if not challenge_id:
        # FSM data lost (e.g. bot restart) — ask the user to restart.
        await state.clear()
        await message.answer(t("link.unavailable", lang))
        return

    username = getattr(message.from_user, "username", None)

    try:
        await api_client.request_link_confirm(
            challenge_id=challenge_id,
            code=code,
            telegram_id=user_context.telegram_id,
            telegram_username=username,
        )
    except LinkInvalidCodeError:
        await state.clear()
        await message.answer(t("link.wrong_code", lang))
        return
    except LinkMemberNotFoundError:
        await state.clear()
        await message.answer(t("link.no_account", lang))
        return
    except LinkAlreadyLinkedOtherError:
        await state.clear()
        await message.answer(t("link.already_linked_other", lang))
        return
    except ApiUnavailableError:
        await state.clear()
        await message.answer(t("link.unavailable", lang))
        return

    await state.clear()
    await message.answer(t("link.success", lang))
