"""`/approvals` handler (FR-BOT-003).

Operator-only command. Lists pending registration approvals for invite_only
events. The underlying invite_only event type is not yet in the schema
(documented scope gap — see 01-requirement-validation.md), so this handler
always renders the empty state for now. The Approve/Decline inline-button
infrastructure is fully implemented for when data is available.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.keyboards.approvals import APPROVE_PREFIX, DECLINE_PREFIX, approvals_keyboard
from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import ApiClient, ApiUnavailableError

router = Router(name="approvals")

_ACCESS_DENIED_KEY = "operator.access_denied"


@router.message(Command("approvals"))
async def handle_approvals(
    message: Message,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"

    if user_context is None or not user_context.is_known or not user_context.is_operator():
        await message.answer(t(_ACCESS_DENIED_KEY, lang))
        return

    if user_context.directus_user_id is None or user_context.country is None:
        await message.answer(t("events.unavailable", lang))
        return

    try:
        result = await api_client.list_pending_approvals(
            country=user_context.country,
            directus_user_id=user_context.directus_user_id,
        )
    except ApiUnavailableError:
        await message.answer(t("event.unavailable", lang))
        return

    if not result.items:
        await message.answer(t("approvals.empty", lang))
        return

    lines = [t("approvals.title", lang)]
    for item in result.items:
        lines.append(
            t("approvals.item", lang).format(
                member=item.member_name,
                event=item.event_title,
            )
        )
    keyboard = approvals_keyboard(result.items, lang)
    await message.answer("\n".join(lines), reply_markup=keyboard)


@router.callback_query(F.data.startswith(f"{APPROVE_PREFIX}:"))
async def handle_approve_callback(
    callback: CallbackQuery,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    await callback.answer()

    if user_context is None or not user_context.is_known or not user_context.is_operator():
        return
    if user_context.directus_user_id is None or user_context.country is None:
        return

    reg_id = (callback.data or "").split(":", 1)[-1]
    try:
        await api_client.approve_registration(
            registration_id=reg_id,
            country=user_context.country,
            directus_user_id=user_context.directus_user_id,
        )
        if callback.message:
            await callback.message.answer(t("approvals.approved", lang))  # type: ignore[union-attr]
    except ApiUnavailableError:
        if callback.message:
            await callback.message.answer(t("event.unavailable", lang))  # type: ignore[union-attr]


@router.callback_query(F.data.startswith(f"{DECLINE_PREFIX}:"))
async def handle_decline_callback(
    callback: CallbackQuery,
    api_client: ApiClient,
    user_context: UserContext | None,
) -> None:
    lang = "ru"
    await callback.answer()

    if user_context is None or not user_context.is_known or not user_context.is_operator():
        return
    if user_context.directus_user_id is None or user_context.country is None:
        return

    reg_id = (callback.data or "").split(":", 1)[-1]
    try:
        await api_client.decline_registration(
            registration_id=reg_id,
            country=user_context.country,
            directus_user_id=user_context.directus_user_id,
        )
        if callback.message:
            await callback.message.answer(t("approvals.declined", lang))  # type: ignore[union-attr]
    except ApiUnavailableError:
        if callback.message:
            await callback.message.answer(t("event.unavailable", lang))  # type: ignore[union-attr]
