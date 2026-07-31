"""`/help` handler (FR-BOT-002 PR 1/6).

Lists all 10 commands from FR-BOT-002's functional-scope table, not just
the 3 implemented so far. Design choice (explicit, per task instruction to
document it rather than silently pick a behavior): showing the full
intended command set is better UX than growing the list PR-by-PR, because
a member reading /help should see where the bot is headed ("coming soon"
suffix on unimplemented ones) rather than being told a command doesn't
exist and then have it silently appear a week later with no announcement.
The "(coming soon)" suffix on each not-yet-shipped command's locale string
(help.register, help.cancel, help.me, help.leaderboard, help.interests,
help.upgrade) makes this explicit rather than misleading. If a user runs
one of those commands anyway, fallback.py's unknown-command handler
answers exactly as it does today — no crash, no special-casing needed
here.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.locales import t

router = Router(name="help")

# Ordered to match FR-BOT-002's functional-scope table exactly, so /help's
# output and the requirement doc read the same way.
_HELP_KEYS = (
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


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    lines = [t("help.title")] + [t(key) for key in _HELP_KEYS]
    await message.answer("\n".join(lines))
