"""`/upgrade` handler (FR-BOT-002 PR 6/6, final PR in this FR's sequence).

Lets a temp (Telegram-only) account upgrade to a full member account by
supplying an email address — the bot collects it via a short aiogram FSM
(FR-BOT-002 Notes: "State machine (aiogram FSM) is used only for
multi-step flows like /start ... and /upgrade (email collection)"), the
first real use of `states/upgrade.py`'s `UpgradeStates`.

The actual upgrade mechanism (Authentik email-collision check, magic-link
send, `is_temporary` flip on verification) is entirely owned by
FR-AUTH-006's already-shipped `POST /v1/internal/telegram/upgrade-temp` —
this handler only collects the email and renders each of that endpoint's
outcomes. See `api_client.py`'s `request_upgrade` for the exact contract.

Design decisions, documented per the task brief's instruction to make
scope calls explicit rather than silently pick one:

1. **`is_temp` short-circuit, no wasted API call.** `user_context.is_temp`
   is already resolved by AuthMiddleware on every update (same precedent
   `/me` already established for its own temp/full branching — see
   `handlers/me.py`). A full-account user running `/upgrade` gets an
   "already a member" message immediately, without ever calling the API
   or entering the FSM. The API's own `not_a_temp_account` 409 is kept as
   a defensive fallback for the (unlikely) race where the account was
   upgraded between this client-side check and the API call actually
   landing — see `_render_error` below.
2. **Client-side email-format check is a UX nicety, not a security
   boundary.** A small regex (`_EMAIL_RE`) rejects obviously-malformed
   input before spending a round trip; the API's own Zod `emailField`
   validation on `upgrade-temp` remains the authoritative check. An
   invalid-format reply re-prompts without leaving the FSM state and
   without calling the API.
3. **FSM state is always cleared after the API call**, on every outcome
   (success or any error) — there is nothing to resume mid-flow; a user
   who wants to retry after an error simply runs `/upgrade` again, same
   posture as every other command's "no persistent session" design.
4. **`email_already_in_use` messaging does not reference Telegram-account
   linking as an alternative.** FR-AUTH-005 (that feature) is
   `status: Planned`, not built — offering it as a working option would be
   inaccurate. The message instead tells the user to either use a
   different email or sign in with that email on the web (an option that
   genuinely exists today via FR-AUTH-004's magic-link sign-in).
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
    EmailAlreadyInUseError,
    NotATempAccountError,
    TelegramUserNotFoundError,
)
from src.states.upgrade import UpgradeStates

router = Router(name="upgrade")

# Deliberately simple format check — one "@", something on each side, a
# dot somewhere in the domain part. Not RFC 5322-complete (nothing short
# of sending an email is), and not meant to be: this only exists to catch
# obviously-malformed input before a wasted round trip. The API's Zod
# emailField schema is the real validation boundary.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email_format(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


@router.message(Command("upgrade"))
async def handle_upgrade_command(
    message: Message,
    state: FSMContext,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    if user_context is None or not user_context.is_known:
        await message.answer(t("event.unavailable", lang))
        return

    if not user_context.is_temp:
        await message.answer(t("upgrade.already_full_account", lang))
        return

    await state.set_state(UpgradeStates.awaiting_email)
    await message.answer(t("upgrade.prompt_email", lang))


@router.message(UpgradeStates.awaiting_email)
async def handle_upgrade_email_reply(
    message: Message,
    state: FSMContext,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    email = (message.text or "").strip()

    if not _is_valid_email_format(email):
        await message.answer(t("upgrade.invalid_email", lang))
        return

    # Guard again — the FSM state could technically outlive a change in
    # user_context between messages (e.g. AuthMiddleware's lookup failing
    # transiently), so this does not blindly trust the state alone.
    if user_context is None or not user_context.is_known:
        await state.clear()
        await message.answer(t("event.unavailable", lang))
        return

    try:
        await api_client.request_upgrade(telegram_id=user_context.telegram_id, email=email)
    except TelegramUserNotFoundError:
        await state.clear()
        await message.answer(t("upgrade.telegram_user_not_found", lang))
        return
    except NotATempAccountError:
        await state.clear()
        await message.answer(t("upgrade.already_full_account", lang))
        return
    except EmailAlreadyInUseError:
        await state.clear()
        await message.answer(t("upgrade.email_already_in_use", lang))
        return
    except ApiUnavailableError:
        await state.clear()
        await message.answer(t("upgrade.unavailable", lang))
        return

    await state.clear()
    await message.answer(t("upgrade.magic_link_sent", lang))
