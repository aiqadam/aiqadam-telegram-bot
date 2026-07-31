"""`/leaderboard` handler (FR-BOT-002 PR 4/6).

Shows the top 10 members for the caller's country, with the caller's own
row highlighted (bold, via the same `<b>...</b>` HTML emphasis convention
`event.detail`/`me.title` already established — parse_mode=HTML is set
once in main.py) if — and only if — they appear in that top 10.

Temp-user exclusion needs no code here: the API's getLeaderboard already
never returns a temp user's row (see telegram-auth.service.ts's doc
comment) — a temp (Authentik-only) user has never earned a point_awards
row to aggregate. There is nothing bot-side to filter.

Scope decision (see 01-requirement-validation.md's Analysis section):
FR-BOT-002's own wording — "Highlights the calling user's position IF
THEY APPEAR" — is read literally as conditional. A caller who ranks
outside the top 10 sees an unmarked list with no separate "your rank"
line. This command has no pagination (unlike /events) — the FR AC only
ever asks for "top 10," not a scrollable/queryable full ranking.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.locales import t
from src.middlewares.auth import UserContext
from src.services.api_client import (
    ApiClient,
    ApiUnavailableError,
    LeaderboardEntry,
    LeaderboardResult,
)

router = Router(name="leaderboard")


def render_leaderboard(result: LeaderboardResult, lang: str) -> str:
    if not result.entries:
        return "\n".join([t("leaderboard.title", lang), "", t("leaderboard.empty", lang)])

    lines = [t("leaderboard.title", lang), ""]
    for rank, entry in enumerate(result.entries, start=1):
        lines.append(_render_row(rank, entry, lang))
    return "\n".join(lines)


def _render_row(rank: int, entry: LeaderboardEntry, lang: str) -> str:
    key = "leaderboard.item_caller" if entry.is_caller else "leaderboard.item"
    return t(key, lang).format(rank=rank, name=entry.display_name, points=entry.points)


@router.message(Command("leaderboard"))
async def handle_leaderboard(
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
        result = await api_client.get_leaderboard(
            directus_user_id=user_context.directus_user_id,
            country=user_context.country,
        )
    except ApiUnavailableError:
        await message.answer(t("leaderboard.unavailable", lang))
        return

    await message.answer(render_leaderboard(result, lang))
