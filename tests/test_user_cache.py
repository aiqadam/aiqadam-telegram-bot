"""Tests for the local SQLite (telegram_id -> directusUserId) cache."""

from __future__ import annotations

from src.services.user_cache import UserCache


def test_get_returns_none_for_unknown_telegram_id(tmp_path) -> None:
    cache = UserCache(tmp_path / "cache.sqlite3")
    assert cache.get("nope") is None
    cache.close()


def test_set_then_get_roundtrips(tmp_path) -> None:
    cache = UserCache(tmp_path / "cache.sqlite3")
    cache.set("123", "directus-abc")
    assert cache.get("123") == "directus-abc"
    cache.close()


def test_set_upserts_existing_key(tmp_path) -> None:
    cache = UserCache(tmp_path / "cache.sqlite3")
    cache.set("123", "directus-abc")
    cache.set("123", "directus-xyz")
    assert cache.get("123") == "directus-xyz"
    cache.close()


def test_set_none_clears_cached_value(tmp_path) -> None:
    cache = UserCache(tmp_path / "cache.sqlite3")
    cache.set("123", "directus-abc")
    cache.set("123", None)
    assert cache.get("123") is None
    cache.close()
