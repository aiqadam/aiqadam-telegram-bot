"""Tests for TenantMiddleware (FR-BOT-001 §5).

Gap identified by 06-test-strategy.md: tenant.py had zero dedicated test
file. TenantMiddleware must run AFTER AuthMiddleware and derive
data["country"] from the user_context AuthMiddleware attaches, including
the unknown/temp-user case where user_context.country is None and the
edge case where user_context itself is absent from data (no KeyError /
crash).
"""

from __future__ import annotations

import pytest

from src.middlewares.auth import UserContext
from src.middlewares.tenant import TenantMiddleware
from tests.conftest import make_message_update


@pytest.mark.asyncio
async def test_sets_country_from_user_context_when_present() -> None:
    middleware = TenantMiddleware()

    downstream_data: dict = {}

    async def downstream(_event, data):
        downstream_data.update(data)
        return "ok"

    user_context = UserContext(
        telegram_id="42",
        is_known=True,
        directus_user_id="dir-42",
        is_temp=False,
        country="kz",
    )
    update = make_message_update(telegram_user_id=42)
    result = await middleware(downstream, update, {"user_context": user_context})

    assert result == "ok"
    assert downstream_data["country"] == "kz"


@pytest.mark.asyncio
async def test_sets_country_to_none_when_user_context_country_is_none() -> None:
    """Unknown/temp user: user_context exists but country was never resolved."""
    middleware = TenantMiddleware()

    downstream_data: dict = {}

    async def downstream(_event, data):
        downstream_data.update(data)
        return "ok"

    user_context = UserContext(
        telegram_id="99",
        is_known=False,
        directus_user_id=None,
        is_temp=False,
        country=None,
    )
    update = make_message_update(telegram_user_id=99)
    result = await middleware(downstream, update, {"user_context": user_context})

    assert result == "ok"
    assert downstream_data["country"] is None


@pytest.mark.asyncio
async def test_sets_country_to_none_without_crashing_when_user_context_is_absent() -> None:
    """AuthMiddleware didn't run / didn't attach user_context at all — must
    not raise a KeyError, must degrade to country=None."""
    middleware = TenantMiddleware()

    downstream_data: dict = {}

    async def downstream(_event, data):
        downstream_data.update(data)
        return "ok"

    update = make_message_update(telegram_user_id=7)
    result = await middleware(downstream, update, {})

    assert result == "ok"
    assert downstream_data["country"] is None


@pytest.mark.asyncio
async def test_sets_country_to_none_when_user_context_key_present_but_none() -> None:
    """data["user_context"] explicitly None (e.g. extract_telegram_id failed
    upstream in AuthMiddleware) — same degrade-to-None behavior."""
    middleware = TenantMiddleware()

    downstream_data: dict = {}

    async def downstream(_event, data):
        downstream_data.update(data)
        return "ok"

    update = make_message_update(telegram_user_id=7)
    result = await middleware(downstream, update, {"user_context": None})

    assert result == "ok"
    assert downstream_data["country"] is None
