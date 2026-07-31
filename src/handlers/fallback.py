"""Unknown-command fallback handler (FR-BOT-001 AC-8).

Registered LAST (lowest router priority) so it only catches commands (and
non-command text) that no other handler matched. Any command not
recognized gets a friendly redirect to /help.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from src.locales import t

router = Router(name="fallback")


@router.message(F.text.startswith("/"))
async def handle_unknown_command(message: Message) -> None:
    await message.answer(t("unknown_command"))
