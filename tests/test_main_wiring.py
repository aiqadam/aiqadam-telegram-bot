"""Tests for main.py's dispatcher wiring (FR-BOT-002 PR 1/6, updated PR 2/6).

Only structural checks — build_dispatcher requires a live Bot/session to
fully exercise polling, out of scope for a unit test. This asserts the
BOT_COMMANDS content (in particular: /event, /register, /cancel are
deliberately excluded, per main.py's own comment) and that all expected
command routers are registered.
"""

from __future__ import annotations

from src.config import Settings
from src.main import BOT_COMMANDS, build_dispatcher
from src.services.api_client import ApiClient
from src.services.user_cache import UserCache


def test_bot_commands_excludes_argument_taking_commands() -> None:
    command_names = {c.command for c in BOT_COMMANDS}
    assert "event" not in command_names
    assert "register" not in command_names
    assert "cancel" not in command_names


def test_bot_commands_includes_the_three_argument_less_commands() -> None:
    command_names = {c.command for c in BOT_COMMANDS}
    assert command_names == {"start", "events", "help"}


def test_build_dispatcher_registers_all_expected_routers(tmp_path) -> None:
    settings = Settings(
        TELEGRAM_BOT_TOKEN="test-token",  # noqa: S106 - test fixture, not a real secret
        INTERNAL_API_URL="https://api.example.com",
        INTERNAL_API_TOKEN="test-internal-token",  # noqa: S106 - test fixture
        BOT_SQLITE_PATH=str(tmp_path / "cache.sqlite3"),
    )
    api_client = ApiClient(settings.internal_api_url, settings.internal_api_token)
    cache = UserCache(settings.sqlite_full_path)

    dispatcher = build_dispatcher(settings, api_client, cache)

    router_names = {r.name for r in dispatcher.sub_routers}
    assert {
        "start",
        "help",
        "events",
        "event_detail",
        "cancel",
        "fallback",
        "errors",
    }.issubset(router_names)
    assert dispatcher["api_client"] is api_client

    cache.close()
