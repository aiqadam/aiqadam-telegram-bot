"""`/start` smoke-test handler (FR-BOT-001 §7, AC-6).

Responds with a static welcome message — must work even for brand-new
users (i.e. even when AuthMiddleware's lookup resolves `is_known=False` or
`None`), before any full signup flow exists. This handler intentionally
does NOT branch on `user_context` — the welcome message is identical for
everyone at this scaffold stage, which is itself what guarantees the
"works even for new users" requirement without extra logic.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.locales import t

router = Router(name="start")


@router.message(Command("start"))
async def handle_start(message: Message) -> None:
    await message.answer(t("start.welcome"))
