"""`/help` handler (FR-BOT-002 PR 1/6, updated FR-BOT-003).

Lists all member commands (and, for operator-role users, the operator command
set as well). Operator commands are hidden from non-operator members — they
would receive "You don't have access to this command" if they ran them.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.locales import t
from src.middlewares.auth import UserContext

router = Router(name="help")

# Ordered to match FR-BOT-002's functional-scope table exactly.
_MEMBER_HELP_KEYS = (
    "help.start",
    "help.events",
    "help.event",
    "help.register",
    "help.cancel",
    "help.me",
    "help.leaderboard",
    "help.interests",
    "help.upgrade",
    "help.help",
)

# FR-BOT-003 operator command help lines.
_OPERATOR_HELP_KEYS = (
    "help.attendance",
    "help.scan",
    "help.approvals",
    "help.announce",
)


@router.message(Command("help"))
async def handle_help(message: Message, user_context: UserContext | None) -> None:
    lang = "ru"
    lines = [t("help.title", lang)] + [t(key, lang) for key in _MEMBER_HELP_KEYS]
    if user_context is not None and user_context.is_operator():
        lines.append("")
        lines.append(t("help.operator_section", lang))
        lines.extend(t(key, lang) for key in _OPERATOR_HELP_KEYS)
    await message.answer("\n".join(lines))
